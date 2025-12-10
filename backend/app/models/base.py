from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func

Base = declarative_base()

class InsiderTrade(Base):
    __tablename__ = "insider_trades"

    id = Column(Integer, primary_key=True, index=True)
    cik = Column(String, index=True, nullable=False)
    ticker = Column(String, index=True, nullable=False)
    insider_name = Column(String, nullable=True)
    transaction_date = Column(Date, nullable=False)
    filing_date = Column(Date, nullable=False)
    transaction_code = Column(String, nullable=False) # Should be "P"
    amount_usd = Column(Float, nullable=False)
    price_per_share = Column(Float, nullable=False)
    number_of_shares = Column(Float, nullable=False)
    
    # We might want to store the accession number to avoid duplicates
    accession_number = Column(String, nullable=False)
    
    # Analysis fields (calculated later)
    is_win = Column(Boolean, nullable=True)
    alpha = Column(Float, nullable=True) # Primary metric (usually 180d or best fit)
    
    # Returns for multiple timeframes
    return_30d = Column(Float, nullable=True)
    spy_return_30d = Column(Float, nullable=True)
    
    return_90d = Column(Float, nullable=True)
    spy_return_90d = Column(Float, nullable=True)
    
    return_180d = Column(Float, nullable=True)
    spy_return_180d = Column(Float, nullable=True)
    
    return_1y = Column(Float, nullable=True)
    spy_return_1y = Column(Float, nullable=True)

    __table_args__ = (
        # Removed UniqueConstraint to allow multiple trades on same day/accession.
        # UniqueConstraint('accession_number', 'transaction_date', 'ticker', name='_unique_trade'),
    )

class InsiderScore(Base):
    __tablename__ = "insider_scores"
    
    cik = Column(String, primary_key=True)
    name = Column(String)
    company = Column(String) # Most recent company or list
    score = Column(Float, default=0.0) # Aggregate Score
    
    total_trades = Column(Integer, default=0)
    total_buys = Column(Integer, default=0)
    total_sells = Column(Integer, default=0)
    
    wins = Column(Integer, default=0)
    buy_wins = Column(Integer, default=0)
    sell_wins = Column(Integer, default=0)
    
    # Efficacy / Alpha metrics (avg alpha across trades)
    alpha_30d = Column(Float, default=0.0)
    alpha_90d = Column(Float, default=0.0)
    
    alpha_180d = Column(Float, default=0.0) # Overall 180d alpha
    buy_alpha_180d = Column(Float, default=0.0)
    sell_alpha_180d = Column(Float, default=0.0)
    
    alpha_1y = Column(Float, default=0.0)
    
    last_updated = Column(DateTime(timezone=True), server_default=func.now())
