# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Trade Validation System - A prototype application that validates trade confirmations from external counterparties against internal system records using LLM-powered document extraction.

### Key Features
- Document upload portal (PDFs, images, text/email content)
- LLM-powered trade data extraction (FX and Swap trades)
- Configurable matching rules with tolerance settings
- Side-by-side comparison and validation results dashboard
- Demo-friendly with editable system records

## Tech Stack

### Frontend
- React + TypeScript + Vite
- shadcn/ui components
- Tailwind CSS
- React Router

### Backend
- Python FastAPI
- OpenAI-compatible LLM API (Claude Sonnet 4 / GPT-4)
- JSON file-based storage (for prototype)

## Getting Started

### Prerequisites
- Node.js 20+
- Python 3.10+
- OpenAI API key (or OpenAI-compatible endpoint)

### Quick Start

1. Start the backend:
```bash
./start_backend.sh
```

2. In a separate terminal, start the frontend:
```bash
./start_frontend.sh
```

3. Open http://localhost:5173 in your browser

### Manual Setup

**Backend:**
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python init_data.py  # Initialize sample data
uvicorn main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

## Commands

### Backend
- `uvicorn main:app --reload` - Start dev server with hot reload
- `python init_data.py` - Initialize/reset sample data

### Frontend
- `npm run dev` - Start dev server
- `npm run build` - Production build
- `npm run preview` - Preview production build

## Architecture

```
tradevalidation/
├── frontend/                 # React frontend
│   ├── src/
│   │   ├── components/ui/    # shadcn/ui components
│   │   ├── pages/            # Route pages
│   │   ├── types/            # TypeScript types
│   │   └── lib/              # Utilities
│   └── package.json
├── backend/                  # FastAPI backend
│   ├── app/
│   │   ├── api/              # API routes
│   │   ├── services/         # LLM extraction, comparison engine
│   │   ├── models/           # Pydantic schemas
│   │   └── db/               # JSON database
│   ├── main.py
│   └── requirements.txt
└── data/                     # Data storage
    ├── database.json         # Trades, documents, rules
    ├── uploads/              # Uploaded files
    └── sample_trades.json    # Sample data
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/trades/fx | List all FX trades |
| POST | /api/trades/fx | Create FX trade |
| GET | /api/trades/swap | List all Swap trades |
| POST | /api/trades/swap | Create Swap trade |
| POST | /api/documents/upload | Upload document |
| POST | /api/documents/text | Submit text content |
| POST | /api/documents/{id}/extract | Extract trade data |
| POST | /api/documents/{id}/validate | Validate against system |
| GET | /api/rules | Get matching rules |
| PUT | /api/rules | Save matching rules |
| GET | /api/validations | Get validation results |

## Configuration

Create `backend/.env` with:
```
OPENAI_API_KEY=your_key_here
# For Claude via compatible endpoint:
# OPENAI_BASE_URL=https://api.anthropic.com/v1
LLM_MODEL=gpt-4o
```

## Trade Types Supported

### FX/Forex Trades
- Trade ID, Counterparty, Currency Pair, Direction
- Notional, Rate, Trade Date, Value Date

### Interest Rate/Currency Swaps
- Trade ID, Counterparty, Trade Type (IRS/CCS/BASIS)
- Notional, Currency, Fixed Rate, Floating Index
- Spread, Effective Date, Maturity Date, Payment Frequency

## Matching Rules

- **Exact**: Values must match exactly
- **Tolerance**: Numeric values within threshold (absolute or %)
- **Fuzzy**: String similarity matching for names
- **Date Tolerance**: Dates within N days
