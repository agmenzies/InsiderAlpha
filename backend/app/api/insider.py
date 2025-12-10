from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.core.database import SessionLocal
from app.models.base import InsiderScore, InsiderTrade
from app.schemas.insider import InsiderScoreBase, InsiderTradeBase
from app.core.auth import verify_authorized_user

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/leaderboard", response_model=List[InsiderScoreBase])
def get_leaderboard(db: Session = Depends(get_db), user=Depends(verify_authorized_user)):
    """
    Returns the leaderboard of insiders sorted by Score.
    """
    scores = db.query(InsiderScore).order_by(InsiderScore.score.desc()).limit(100).all()
    return scores

@router.get("/trades/{cik}", response_model=List[InsiderTradeBase])
def get_insider_trades(cik: str, db: Session = Depends(get_db), user=Depends(verify_authorized_user)):
    """
    Returns trades for a specific insider.
    """
    trades = db.query(InsiderTrade).filter(InsiderTrade.cik == cik).order_by(InsiderTrade.transaction_date.desc()).all()
    return trades
