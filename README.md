# Insider-Alpha

A portfolio management dashboard that tracks high-performing insider trades by analyzing SEC Form 4 filings and calculating "Conviction Scores" based on historical Alpha vs S&P 500.

## Tech Stack

*   **Backend:** Python 3.11+, FastAPI, SQLAlchemy, SQLite (Dev), Pydantic.
*   **Frontend:** React 18 (Next.js App Router), TypeScript, Tailwind CSS, Recharts.
*   **Data:** SEC EDGAR API (via `sec-edgar-downloader`), `yfinance`.
*   **Auth:** Google OAuth 2.0 (restricted to whitelist).

## Prerequisites

*   Python 3.11 or higher
*   Node.js 18+ and npm
*   Git

## Local Setup Instructions

### 1. Clone the Repository

```bash
git clone <repository-url>
cd insider-alpha
```

### 2. Backend Setup

1.  **Navigate to the backend directory:**
    ```bash
    cd backend
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment Variables:**
    Create a `.env` file in the `backend` directory:
    ```bash
    touch .env
    ```
    Add the following content (replace with your real credentials if needed, or use mock for dev):
    ```env
    SECRET_KEY=supersecret-dev-key
    GOOGLE_CLIENT_ID=your-google-client-id
    GOOGLE_CLIENT_SECRET=your-google-client-secret
    ALLOWED_USERS=["your.email@gmail.com"]
    DATABASE_URL=sqlite:///./insider_alpha.db
    ```

5.  **Seed Data (Optional for Dev):**
    To populate the database with mock data for visualization:
    ```bash
    export PYTHONPATH=$PYTHONPATH:$(pwd)
    python3 scripts/seed_data.py
    ```

    **Or Run Real Ingestion (Takes time):**
    ```bash
    python3 scripts/ingest_sec.py
    # Then run scoring
    python3 app/services/scoring.py
    ```

6.  **Run the Server:**
    ```bash
    uvicorn app.main:app --reload
    ```
    The API will be available at `http://localhost:8000`.

### 3. Frontend Setup

1.  **Open a new terminal and navigate to the frontend directory:**
    ```bash
    cd frontend
    ```

2.  **Install dependencies:**
    ```bash
    npm install
    ```

3.  **Run the Development Server:**
    ```bash
    npm run dev
    ```
    The dashboard will be available at `http://localhost:3000`.

## Features

*   **Leaderboard:** View top insiders ranked by Win Rate and Alpha.
*   **Metrics:** 30D, 180D, and 1Y Returns; Buy vs Sell Efficacy.
*   **Portfolio:** Track your own positions.
*   **Comparison:** Visualize performance vs Insiders and SPY.

## Troubleshooting

*   **Auth Error:** If you see "Not authenticated" or 401/403 errors, ensure you have set up Google OAuth credentials correctly in `.env` and your email is in `ALLOWED_USERS`. For local testing without OAuth, you may need to modify `backend/app/api/insider.py` to remove the `verify_authorized_user` dependency temporarily.
*   **No Data:** Ensure you ran the `seed_data.py` script or the ingestion pipeline.
