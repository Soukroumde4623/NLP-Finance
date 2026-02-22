# 📊 FinSent — Financial Sentiment Analysis

A Django web application for sentiment analysis on financial news, powered by a **FinBERT** model fine-tuned on financial data.

## 🏗️ Project Structure

```
finance_sentiment/
├── manage.py                        # Django entry point
├── requirements.txt                 # Python dependencies
├── .env                             # Environment variables (not versioned)
├── .gitignore
│
├── finance_sentiment/               # Django configuration
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
│
├── dashboard/                       # Main application
│   ├── models.py                    # Django models (PredictionHistory)
│   ├── views.py                     # Views: dashboard, news, statistics
│   ├── urls.py                      # App routing
│   ├── admin.py                     # Django admin
│   ├── model_inference.py           # FinBERT inference (sentiment prediction)
│   ├── models_ml/                   # Fine-tuned ML model
│   │   └── finbert_finetuned/
│   └── templates/dashboard/         # HTML templates
│       ├── base.html                # Shared base template
│       ├── sentiment_dashboard.html # Interactive analysis page
│       ├── latest_news.html         # Latest news
│       └── statistics.html          # Statistics & KPIs
│
├── scripts/                         # Data pipeline scripts
│   ├── pipeline_finbert.py          # Full pipeline (S&P500 → News → Analysis)
│   └── legacy_pipeline_lstm.py      # Legacy LSTM pipeline (archived)
│
├── database/                        # SQL scripts
│   └── schema.sql                   # PostgreSQL database schema
│
└── notebooks/                       # Jupyter notebooks
    └── NLP_FINBERT.ipynb            # FinBERT training / exploration
```

## 🚀 Installation

### 1. Clone the repository
```bash
git clone https://github.com/Soukroumde4623/NLP-Finance.git
cd finance_sentiment
```

### 2. Create a virtual environment
```bash
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux / Mac
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure environment variables
Create a `.env` file at the project root:
```ini
SECRET_KEY=your-django-secret-key
DEBUG=True
DB_NAME=AnalyseSentiments
DB_USER=postgres
DB_PASSWORD=your-password
DB_HOST=127.0.0.1
DB_PORT=5432
```

### 5. Create the PostgreSQL database
```bash
psql -U postgres -f database/schema.sql
```

### 6. Apply Django migrations
```bash
python manage.py migrate
```

### 7. Run the server
```bash
python manage.py runserver
```

## 📡 Data Pipeline

The script `scripts/pipeline_finbert.py` runs three steps:

1. **Asset collection** — Fetches S&P 500 companies from Wikipedia
2. **News collection** — Retrieves news articles via Yahoo Finance
3. **Sentiment analysis** — Runs each article through the fine-tuned FinBERT model

```bash
python scripts/pipeline_finbert.py
```

## 🌐 Available Pages

| URL | Description |
|-----|-------------|
| `/` | Main dashboard — Interactive text analysis |
| `/news/latest/` | Latest news with sentiment labels |
| `/news/feed/` | JSON API for real-time news feed |
| `/stats/` | Global and per-asset statistics |

## 🧠 ML Model

- **Architecture**: FinBERT (BERT pre-trained on financial text)
- **Fine-tuning**: Trained on a custom financial corpus
- **Labels**: `positive`, `neutral`, `negative`
- **Location**: `dashboard/models_ml/finbert_finetuned/`

## 🗄️ Database

PostgreSQL database with the following tables:
- `SOURCE` — Data sources (Yahoo Finance, etc.)
- `DOCUMENT` — Collected news articles
- `ACTIF` — Financial assets (S&P 500)
- `CONCERNE` — Document ↔ asset mapping
- `ANALYSE_SENTIMENT` — Sentiment analysis results
- `UTILISATEUR` / `ALERTE` — User alerts management

## 🛠️ Tech Stack

- **Backend**: Django 6.0, Python 3.12+
- **ML**: PyTorch, Transformers (HuggingFace), FinBERT
- **Database**: PostgreSQL
- **Frontend**: HTML/CSS/JS (inline, dark theme)
- **Data**: yfinance, pandas, requests
