import datetime
import yfinance as yf
from sqlalchemy.orm import Session
from app.models.base import InsiderTrade, InsiderScore
from app.core.database import SessionLocal
import logging

logger = logging.getLogger(__name__)

# Constants
SPY_TICKER = "SPY"
LOOKBACK_YEARS = 3
WIN_ALPHA_THRESHOLD = 0.03 # 3%

class ScoringService:
    def __init__(self, db: Session):
        self.db = db
        self.spy_history = {} # Cache SPY history

    def _get_price(self, ticker: str, date: datetime.date) -> float:
        """
        Fetches closing price for a ticker on a specific date.
        If date is non-trading, finds next trading day.
        """
        # We can fetch a small window around the date
        start = date
        end = date + datetime.timedelta(days=5) # 5 day window to find a trading day
        
        try:
            # yfinance download
            data = yf.download(ticker, start=start, end=end, progress=False)
            if data.empty:
                return None
            
            # Get the first available close
            # Dataframe structure might be MultiIndex if multiple tickers, but here single.
            # 'Close' column.
            # yfinance 0.2.x returns pandas dataframe
            
            # yfinance recent versions might return MultiIndex if we didn't specify properly or just index is Date
            # For single ticker, it usually has columns: Open, High, Low, Close, Adj Close, Volume
            
            # Check if 'Close' is available
            # Note: yf.download might return different structure depending on version. 
            # Safe way: access 'Close' then first item.
            
            if "Close" in data.columns:
                 # Check if Close is a dataframe (multi-level) or series
                 close_data = data["Close"]
                 if hasattr(close_data, "iloc"):
                     val = close_data.iloc[0]
                     # If val is a Series (multi-ticker artifacts), get value
                     if hasattr(val, "item"):
                         return val.item()
                     return float(val)
            
            return None

        except Exception as e:
            logger.error(f"Error fetching price for {ticker} on {date}: {e}")
            return None

    def _get_spy_return(self, start_date: datetime.date, end_date: datetime.date) -> float:
        # Optimization: Cache SPY data for the last 3+ years once if possible, 
        # but for now per-trade fetch is okay or cache individually.
        
        p_start = self._get_price(SPY_TICKER, start_date)
        p_end = self._get_price(SPY_TICKER, end_date)
        
        if p_start and p_end:
            return (p_end - p_start) / p_start
        return None

    def calculate_alpha(self, ticker: str, t_start: datetime.date, days: int, trade_type: str):
        t_end = t_start + datetime.timedelta(days=days)
        if t_end > datetime.date.today():
             return None, None, None # Can't calculate yet

        p_start = self._get_price(ticker, t_start)
        p_end = self._get_price(ticker, t_end)
        
        if not p_start or not p_end:
            return None, None, None
            
        stock_return = (p_end - p_start) / p_start
        spy_return = self._get_spy_return(t_start, t_end)
        
        if spy_return is None:
             return stock_return, None, None
             
        if trade_type == "P":
            alpha = stock_return - spy_return
        else: # "S"
            # For sells, we win if stock underperforms SPY (stock return < SPY return).
            # Alpha = SPY Return - Stock Return.
            # Example: SPY +5%, Stock -2%. Alpha = 5 - (-2) = 7%. Good sell.
            # Example: SPY +5%, Stock +10%. Alpha = 5 - 10 = -5%. Bad sell.
            alpha = spy_return - stock_return
            
        return stock_return, spy_return, alpha

    def process_trades(self):
        """
        Iterates over InsiderTrades that haven't been fully scored yet.
        Calculates Alpha for 30d, 90d, 180d, 1y.
        """
        # We process any trade that has NULL in any of the return columns AND is old enough
        # Actually, simpler: process any trade where alpha is None but date allows it.
        # Just iterate all trades for simplicity in MVP re-run, or filter.
        
        trades = self.db.query(InsiderTrade).filter(
            InsiderTrade.alpha == None
        ).all()
        
        logger.info(f"Found {len(trades)} trades to process.")
        
        for trade in trades:
            t_start = trade.transaction_date
            trade_type = trade.transaction_code
            
            # 30d
            r30, s30, a30 = self.calculate_alpha(trade.ticker, t_start, 30, trade_type)
            if r30 is not None:
                trade.return_30d = r30
                trade.spy_return_30d = s30
            
            # 90d
            r90, s90, a90 = self.calculate_alpha(trade.ticker, t_start, 90, trade_type)
            if r90 is not None:
                trade.return_90d = r90
                trade.spy_return_90d = s90

            # 180d - Primary for Score
            r180, s180, a180 = self.calculate_alpha(trade.ticker, t_start, 180, trade_type)
            if r180 is not None:
                trade.return_180d = r180
                trade.spy_return_180d = s180
                trade.alpha = a180 # Store 180d alpha as main alpha
                trade.is_win = a180 > WIN_ALPHA_THRESHOLD

            # 1y
            r1y, s1y, a1y = self.calculate_alpha(trade.ticker, t_start, 365, trade_type)
            if r1y is not None:
                trade.return_1y = r1y
                trade.spy_return_1y = s1y
            
            self.db.add(trade)
        
        self.db.commit()

    def update_scores(self):
        """
        Aggregates trades per insider and updates InsiderScore.
        """
        lookback_date = datetime.date.today() - datetime.timedelta(days=LOOKBACK_YEARS * 365)
        
        trades = self.db.query(InsiderTrade).filter(
            InsiderTrade.transaction_date >= lookback_date,
            InsiderTrade.is_win != None 
        ).all()
        
        insider_stats = {}
        
        for trade in trades:
            cik = trade.cik
            if cik not in insider_stats:
                insider_stats[cik] = {
                    "wins": 0, "total": 0,
                    "buy_wins": 0, "total_buys": 0,
                    "sell_wins": 0, "total_sells": 0,
                    "alphas_30d": [], "alphas_90d": [], 
                    "alphas_180d": [], "buy_alphas_180d": [], "sell_alphas_180d": [],
                    "alphas_1y": [],
                    "name": trade.insider_name,
                    "company": trade.ticker
                }
            
            stats = insider_stats[cik]
            stats["total"] += 1
            if trade.is_win:
                stats["wins"] += 1
            
            # Collect Alphas for averaging
            def compute_alpha(r, s, type):
                if r is None or s is None: return None
                return (r - s) if type == "P" else (s - r)

            a30 = compute_alpha(trade.return_30d, trade.spy_return_30d, trade.transaction_code)
            a90 = compute_alpha(trade.return_90d, trade.spy_return_90d, trade.transaction_code)
            a180 = trade.alpha
            a1y = compute_alpha(trade.return_1y, trade.spy_return_1y, trade.transaction_code)
            
            if a30 is not None: stats["alphas_30d"].append(a30)
            if a90 is not None: stats["alphas_90d"].append(a90)
            if a1y is not None: stats["alphas_1y"].append(a1y)
            
            if a180 is not None: 
                stats["alphas_180d"].append(a180)
                if trade.transaction_code == "P":
                    stats["buy_alphas_180d"].append(a180)
                elif trade.transaction_code == "S":
                    stats["sell_alphas_180d"].append(a180)

            if trade.transaction_code == "P":
                stats["total_buys"] += 1
                if trade.is_win: stats["buy_wins"] += 1
            elif trade.transaction_code == "S":
                stats["total_sells"] += 1
                if trade.is_win: stats["sell_wins"] += 1
                
        # Update InsiderScore table
        for cik, stats in insider_stats.items():
            total = stats["total"]
            
            # Upsert
            insider_score = self.db.query(InsiderScore).filter(InsiderScore.cik == cik).first()
            if not insider_score:
                insider_score = InsiderScore(cik=cik)
                self.db.add(insider_score)
            
            insider_score.name = stats["name"]
            insider_score.company = stats["company"]
            insider_score.total_trades = total
            insider_score.total_buys = stats["total_buys"]
            insider_score.total_sells = stats["total_sells"]
            insider_score.wins = stats["wins"]
            insider_score.buy_wins = stats["buy_wins"]
            insider_score.sell_wins = stats["sell_wins"]
            
            # Score formula (overall win rate)
            if total < 3:
                insider_score.score = 0.0
            else:
                insider_score.score = (stats["wins"] / total) * 100.0
            
            # Avg Alphas
            def avg(l): return sum(l)/len(l) if l else 0.0
            
            insider_score.alpha_30d = avg(stats["alphas_30d"])
            insider_score.alpha_90d = avg(stats["alphas_90d"])
            insider_score.alpha_180d = avg(stats["alphas_180d"])
            insider_score.buy_alpha_180d = avg(stats["buy_alphas_180d"])
            insider_score.sell_alpha_180d = avg(stats["sell_alphas_180d"])
            insider_score.alpha_1y = avg(stats["alphas_1y"])

            insider_score.last_updated = datetime.datetime.now()
        
        self.db.commit()

def main():
    db = SessionLocal()
    service = ScoringService(db)
    
    logger.info("Calculating Alphas...")
    service.process_trades()
    
    logger.info("Updating Insider Scores...")
    service.update_scores()
    
    logger.info("Done.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
