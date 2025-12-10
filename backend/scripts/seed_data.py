from sqlalchemy.orm import Session
from app.core.database import SessionLocal, init_db
from app.models.base import InsiderScore, InsiderTrade
import datetime
import random

def seed():
    init_db()
    db = SessionLocal()
    
    # clear existing
    db.query(InsiderScore).delete()
    db.query(InsiderTrade).delete()
    
    # Create Insiders
    insiders = [
        {"cik": "0001", "name": "Lando Norris", "company": "MCLAREN", "wins": 8, "total": 10},
        {"cik": "0002", "name": "Oscar Piastri", "company": "MCLAREN", "wins": 6, "total": 10},
        {"cik": "0003", "name": "Max Verstappen", "company": "RED BULL", "wins": 5, "total": 10},
        {"cik": "0004", "name": "Lewis Hamilton", "company": "FERRARI", "wins": 4, "total": 10},
    ]
    
    for i in insiders:
        # Create Score
        score = InsiderScore(
            cik=i["cik"],
            name=i["name"],
            company=i["company"],
            score=(i["wins"]/i["total"])*100,
            total_trades=i["total"],
            wins=i["wins"],
            total_buys=5,
            total_sells=5,
            buy_wins=int(i["wins"]/2),
            sell_wins=int(i["wins"]/2),
            alpha_30d=random.uniform(-0.05, 0.10),
            alpha_90d=random.uniform(-0.05, 0.15),
            alpha_180d=random.uniform(0.0, 0.20),
            buy_alpha_180d=random.uniform(0.0, 0.20),
            sell_alpha_180d=random.uniform(0.0, 0.20),
            alpha_1y=random.uniform(0.05, 0.25),
            last_updated=datetime.datetime.now()
        )
        db.add(score)
        
        # Create Trades
        for j in range(i["total"]):
            is_buy = j % 2 == 0
            code = "P" if is_buy else "S"
            t_date = datetime.date(2023, 1, 1) + datetime.timedelta(days=j*30)
            
            trade = InsiderTrade(
                cik=i["cik"],
                ticker=i["company"],
                insider_name=i["name"],
                transaction_date=t_date,
                filing_date=t_date,
                transaction_code=code,
                amount_usd=random.randint(10000, 1000000),
                price_per_share=random.uniform(10, 200),
                number_of_shares=1000,
                accession_number=f"acc-{i['cik']}-{j}",
                is_win=random.choice([True, False]),
                alpha=random.uniform(-0.1, 0.3),
                return_30d=random.uniform(-0.05, 0.1),
                return_90d=random.uniform(-0.05, 0.15),
                return_180d=random.uniform(-0.1, 0.2),
                return_1y=random.uniform(-0.1, 0.3),
                spy_return_30d=0.01,
                spy_return_90d=0.03,
                spy_return_180d=0.05,
                spy_return_1y=0.10
            )
            db.add(trade)
            
    db.commit()
    print("Seed data inserted.")

if __name__ == "__main__":
    seed()
