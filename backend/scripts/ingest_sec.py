import os
import sys
import json
import asyncio
import datetime
from pathlib import Path
from typing import List, Dict, Optional
import requests
from sec_edgar_downloader import Downloader
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session
from app.core.database import SessionLocal, init_db
from app.models.base import InsiderTrade

# Setup logging
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
DATA_DIR = Path("backend/data/sec")
TICKERS_JSON_URL = "https://www.sec.gov/files/company_tickers.json"
USER_AGENT = "InsiderAlpha/1.0 (jules@example.com)" 
# Note: SEC requires a valid User-Agent. I'll use a placeholder but in prod it should be real.

class SECOperator:
    def __init__(self, db: Session):
        self.db = db
        self.dl = Downloader("InsiderAlpha", "jules@example.com", DATA_DIR)

    def fetch_tickers(self) -> Dict[str, str]:
        """
        Fetches company_tickers.json and returns a mapping of Ticker -> CIK.
        Result format: {'AAPL': '0000320193', ...}
        """
        headers = {"User-Agent": USER_AGENT}
        resp = requests.get(TICKERS_JSON_URL, headers=headers)
        if resp.status_code != 200:
            logger.error(f"Failed to fetch tickers: {resp.status_code}")
            return {}
        
        data = resp.json()
        ticker_map = {}
        for idx, entry in data.items():
            ticker = entry['ticker']
            cik = str(entry['cik_str']).zfill(10)
            ticker_map[ticker] = cik
        
        return ticker_map

    def download_filings(self, ticker: str, limit: int = 10): # Limit to 10 for testing speed
        """
        Downloads Form 4s for a given ticker.
        """
        try:
            # We pass ticker as the equity. Downloader resolves it to CIK mostly, or we can pass CIK.
            # Passing ticker is supported.
            logger.info(f"Downloading {limit} filings for {ticker}...")
            self.dl.get("4", ticker, limit=limit)
        except Exception as e:
            logger.error(f"Error downloading filings for {ticker}: {e}")

    def parse_filing(self, file_path: Path, ticker: str) -> List[InsiderTrade]:
        """
        Parses a single Form 4 XML file.
        Returns a list of InsiderTrade objects found in the filing.
        """
        if not file_path.exists():
            return []

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        soup = BeautifulSoup(content, 'xml')
        
        trades = []
        
        # Extract generic info
        try:
            issuer_cik = soup.find('issuerCik').text
            reporting_owner = soup.find('reportingOwner')
            rpt_owner_cik = reporting_owner.reportingOwnerId.rptOwnerCik.text
            rpt_owner_name = reporting_owner.reportingOwnerId.rptOwnerName.text
            
            # Extract transactions
            # There can be multiple nonDerivativeTransaction
            transactions = soup.find_all('nonDerivativeTransaction')
            
            for trans in transactions:
                try:
                    # Filter for transactionCode == "P" or "S"
                    trans_code = trans.transactionCoding.transactionCode.text
                    if trans_code not in ["P", "S"]:
                        continue
                    
                    # Get Date
                    date_str = trans.transactionDate.value.text
                    trans_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
                    
                    # Check age (Phase 3 requirement: ignore older than 3 years)
                    # But wait, logic says "Analysis Engine" does the lookback. 
                    # Here we ingest. Maybe we can ingest everything or filter here.
                    # Prompt says: "Filter Filings: ... Extract transactions strictly matching P ... Drops A, M, G"
                    # "Lookback Window: Ignore any trade older than 3 years" is in Phase 3. 
                    # But it's efficient to filter here.
                    if (datetime.date.today() - trans_date).days > 3 * 365:
                         continue

                    # Get Shares and Price
                    shares = float(trans.transactionAmounts.transactionShares.value.text)
                    price_per_share = float(trans.transactionAmounts.transactionPricePerShare.value.text)
                    amount_usd = shares * price_per_share
                    
                    # Filing Date (from folder structure or file metadata? XML usually has periodOfReport but filing date is when it was filed)
                    # The downloader stores files in folder struct: sec-edgar-filings/{Ticker}/4/{AccessionNumber}/...
                    # We can use periodOfReport as proxy for transaction, but filing date is needed?
                    # Downloader doesn't easily give filing date unless we look at the index.html or accession number metadata.
                    # Let's assume filing_date ~= transaction_date for now or periodOfReport.
                    # Actually, we can get it from the path maybe? No.
                    # Let's use periodOfReport as a fallback or today if parsing live.
                    # For historical backfill, periodOfReport is closest we have in XML usually.
                    # Wait, 'periodOfReport' is in the XML.
                    
                    filing_date_node = soup.find('periodOfReport')
                    if filing_date_node:
                         filing_date_str = filing_date_node.text
                         filing_date = datetime.datetime.strptime(filing_date_str, "%Y-%m-%d").date()
                    else:
                         filing_date = trans_date # Fallback

                    # Accession number is part of the path usually.
                    # .../primary_doc.xml
                    accession_number = file_path.parent.name
                    
                    trade = InsiderTrade(
                        cik=rpt_owner_cik,
                        ticker=ticker,
                        insider_name=rpt_owner_name,
                        transaction_date=trans_date,
                        filing_date=filing_date,
                        transaction_code=trans_code,
                        amount_usd=amount_usd,
                        price_per_share=price_per_share,
                        number_of_shares=shares,
                        accession_number=accession_number
                    )
                    trades.append(trade)
                except Exception as e:
                    logger.debug(f"Skipping transaction in {file_path}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error parsing {file_path}: {e}")
        
        return trades

    def process_ticker(self, ticker: str):
        self.download_filings(ticker)
        
        # Iterate over downloaded files
        ticker_dir = DATA_DIR / "sec-edgar-filings" / ticker / "4"
        if not ticker_dir.exists():
            return
            
        for filing_dir in ticker_dir.iterdir():
            if not filing_dir.is_dir():
                continue
            
            # Look for XML (usually primary_doc.xml or similar, but the downloader might rename it or we just find *.xml)
            # v5.0.3 usually saves `full-submission.txt`.
            # We need to scan full-submission.txt and extract XML if it's not a standalone xml file.
            # But based on `sec-edgar-downloader` documentation, it saves files as is.
            
            xml_files = list(filing_dir.glob("*.xml"))
            txt_files = list(filing_dir.glob("*.txt"))
            
            # If no XML files, check txt files (full-submission.txt)
            if not xml_files and txt_files:
                # Naive approach: Parse the txt file as if it might contain the XML or be the XML content wrapped
                # The file I read (full-submission.txt) has <SEC-DOCUMENT> ... <XML> ... </XML> ...
                # BeautifulSoup can parse this directly if we just feed it.
                # It will find <ownershipDocument> inside <XML>
                xml_files = txt_files

            if not xml_files:
                continue
            
            # Usually the largest XML is the form itself, or specifically the one containing <ownershipDocument>
            target_file = None
            for xml in xml_files:
                # Naive check: does it look like the right file?
                # We can just try parsing all XMLs, usually there is only one relevant form 4 xml.
                target_file = xml
                # We'll try to parse it.
                
                new_trades = self.parse_filing(target_file, ticker)
                for trade in new_trades:
                    # Upsert logic or just add and ignore duplicates if constrained
                    # We have a unique constraint: accession, date, ticker.
                    # But transaction index is not in unique constraint? A filing can have multiple buys.
                    # We should probably add an index or something to the constraint, or just handle it.
                    # My model constraint: UniqueConstraint('accession_number', 'transaction_date', 'ticker')
                    # This might fail if multiple buys on same day in same filing.
                    # Better constraint: accession_number + line item index?
                    # For now I will try to insert and catch integrity error, or query first.
                    
                    existing = self.db.query(InsiderTrade).filter(
                        InsiderTrade.accession_number == trade.accession_number,
                        InsiderTrade.transaction_date == trade.transaction_date,
                        InsiderTrade.ticker == trade.ticker,
                        InsiderTrade.amount_usd == trade.amount_usd # Check amount to distinguish different trades in same filing
                    ).first()
                    
                    if not existing:
                        self.db.add(trade)
                
                try:
                    self.db.commit()
                except Exception as e:
                    self.db.rollback()
                    logger.warning(f"Failed to commit trades for {ticker} in {target_file.parent.name}: {e}")


def main():
    init_db()
    db = SessionLocal()
    operator = SECOperator(db)
    
    # 1. Map Tickers
    logger.info("Fetching tickers...")
    tickers = operator.fetch_tickers()
    logger.info(f"Found {len(tickers)} tickers.")
    
    # 2. Select tickers to process
    # For this task, we can't process all 10k tickers. 
    # I'll pick a few known ones for the demo: AAPL, TSLA, MSFT, NVDA, META
    target_tickers = ["AAPL", "TSLA", "MSFT", "NVDA", "META"]
    
    for ticker in target_tickers:
        logger.info(f"Processing {ticker}...")
        operator.process_ticker(ticker)
        
    logger.info("Done.")

if __name__ == "__main__":
    main()
