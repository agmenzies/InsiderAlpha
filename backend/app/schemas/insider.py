from typing import List, Optional
from pydantic import BaseModel
from datetime import date, datetime

class InsiderScoreBase(BaseModel):
    cik: str
    name: Optional[str] = None
    company: Optional[str] = None
    score: float
    total_trades: int
    wins: int
    
    total_buys: int
    total_sells: int
    buy_wins: int
    sell_wins: int
    
    alpha_30d: float
    alpha_90d: float
    alpha_180d: float
    buy_alpha_180d: float
    sell_alpha_180d: float
    alpha_1y: float
    
    last_updated: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class InsiderTradeBase(BaseModel):
    cik: str
    ticker: str
    transaction_date: date
    transaction_code: str
    amount_usd: float
    price_per_share: float
    number_of_shares: float
    is_win: Optional[bool] = None
    alpha: Optional[float] = None
    
    return_30d: Optional[float] = None
    return_90d: Optional[float] = None
    return_180d: Optional[float] = None
    return_1y: Optional[float] = None
    
    class Config:
        from_attributes = True
