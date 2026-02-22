"""
Pipeline FinBERT — Collecte des actifs S&P 500, récupération des news Yahoo Finance,
et analyse de sentiment via le modèle FinBERT fine-tuné.

Usage :
    python scripts/pipeline_finbert.py
"""

import os
import sys

# Ajouter la racine du projet au PYTHONPATH pour importer dashboard.model_inference
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

import requests
import pandas as pd
from io import StringIO
from datetime import datetime
import yfinance as yf

import psycopg
from psycopg.rows import dict_row

from decouple import config

from dashboard.model_inference import predict_sentiment


# =============================================================================
# CONFIG DB (depuis .env)
# =============================================================================
DB_NAME = config("DB_NAME", default="AnalyseSentiments")
DB_USER = config("DB_USER", default="postgres")
DB_PASS = config("DB_PASSWORD")
DB_HOST = config("DB_HOST", default="127.0.0.1")
DB_PORT = config("DB_PORT", default=5432, cast=int)

CONNINFO = f"dbname={DB_NAME} user={DB_USER} password={DB_PASS} host={DB_HOST} port={DB_PORT}"


# =============================================================================
# ÉTAPE 1 — Remplir la table ACTIF depuis le S&P 500
# =============================================================================
def load_sp500_assets():
    """Récupère la liste S&P 500 depuis Wikipedia et insère dans ACTIF."""
    print("=" * 60)
    print("ÉTAPE 1 : Chargement des actifs S&P 500")
    print("=" * 60)

    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    headers = {"User-Agent": "Mozilla/5.0"}

    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()

    sp500 = pd.read_html(StringIO(response.text))[0]

    df_actifs = pd.DataFrame({
        "nom_actif": sp500["Security"],
        "ticker": sp500["Symbol"],
        "secteur": sp500["GICS Sector"],
    })

    print(f"  → {len(df_actifs)} actifs récupérés depuis Wikipedia")

    values = list(df_actifs[["nom_actif", "ticker", "secteur"]].itertuples(index=False, name=None))

    with psycopg.connect(CONNINFO) as conn:
        with conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO actif (nom_actif, ticker, secteur)
                VALUES (%s, %s, %s)
                ON CONFLICT (ticker) DO NOTHING
                """,
                values,
            )
        conn.commit()

    print("  ✓ Insertion des tickers S&P 500 terminée !")


# =============================================================================
# ÉTAPE 2 — Récupérer les news Yahoo Finance → DOCUMENT + CONCERNE
# =============================================================================
def fetch_yahoo_news():
    """Récupère les news via yfinance et les stocke dans DOCUMENT / CONCERNE."""
    print("\n" + "=" * 60)
    print("ÉTAPE 2 : Récupération des news Yahoo Finance")
    print("=" * 60)

    with psycopg.connect(CONNINFO, row_factory=dict_row) as conn:
        with conn.cursor() as cur:

            # Source Yahoo Finance
            cur.execute("""
                INSERT INTO source (nom_source, type_source, fiabilite)
                VALUES ('Yahoo Finance', 'API', 0.95)
                ON CONFLICT (nom_source) DO UPDATE SET fiabilite = EXCLUDED.fiabilite
                RETURNING id_source
            """)
            id_source = cur.fetchone()["id_source"]

            cur.execute("SELECT id_actif, ticker FROM actif WHERE ticker IS NOT NULL")
            actifs = cur.fetchall()

            print(f"  → {len(actifs)} tickers dans la table ACTIF")

            for a in actifs:
                id_actif = a["id_actif"]
                ticker = a["ticker"]

                try:
                    t = yf.Ticker(ticker)
                    news_list = t.news or []
                    if not news_list:
                        continue

                    print(f"  {ticker} : {len(news_list)} articles trouvés")

                    for article in news_list:
                        content = article.get("content") or {}
                        titre = content.get("title")
                        contenu = content.get("summary") or ""
                        pub_date = content.get("pubDate")

                        if not titre or not pub_date:
                            continue

                        date_pub = datetime.fromisoformat(pub_date.replace("Z", "+00:00")).date()

                        cur.execute("""
                            INSERT INTO document (titre, contenu, date_publication, id_source)
                            VALUES (%s, %s, %s, %s)
                            ON CONFLICT (titre, date_publication, id_source)
                            DO UPDATE SET contenu = EXCLUDED.contenu
                            RETURNING id_document
                        """, (titre, contenu, date_pub, id_source))

                        id_doc = cur.fetchone()["id_document"]

                        cur.execute("""
                            INSERT INTO concerne (id_document, id_actif)
                            VALUES (%s, %s)
                            ON CONFLICT (id_document, id_actif) DO NOTHING
                        """, (id_doc, id_actif))

                    conn.commit()

                except Exception as e:
                    print(f"  ⚠ Erreur pour {ticker} : {e}")

    print("  ✓ Stockage des news terminé !")


# =============================================================================
# ÉTAPE 3 — Analyse de sentiment FinBERT → ANALYSE_SENTIMENT
# =============================================================================
def run_sentiment_analysis():
    """Analyse les documents non encore traités avec FinBERT."""
    print("\n" + "=" * 60)
    print("ÉTAPE 3 : Analyse de sentiment FinBERT")
    print("=" * 60)

    with psycopg.connect(CONNINFO, row_factory=dict_row) as conn:
        with conn.cursor() as cur:

            cur.execute("""
                SELECT d.id_document, d.titre, d.contenu, c.id_actif
                FROM document d
                JOIN concerne c ON d.id_document = c.id_document
                LEFT JOIN analyse_sentiment s
                  ON s.id_document = d.id_document
                 AND s.id_actif = c.id_actif
                WHERE s.id_analyse IS NULL
            """)
            documents = cur.fetchall()
            print(f"  → {len(documents)} documents à analyser")

            for idx, r in enumerate(documents, 1):
                texte = f"{r['titre']}. {r['contenu']}"
                score, label = predict_sentiment(texte)

                cur.execute("""
                    INSERT INTO analyse_sentiment (polarite, score, date_analyse, id_document, id_actif)
                    VALUES (%s, %s, %s, %s, %s)
                """, (label, float(score), datetime.now(), r["id_document"], r["id_actif"]))

                if idx % 100 == 0 or idx == len(documents):
                    print(f"  {idx}/{len(documents)} documents analysés")

            conn.commit()

    print("  ✓ Toutes les news ont été analysées avec FinBERT !")


# =============================================================================
# MAIN
# =============================================================================
if __name__ == "__main__":
    print("\n🚀 Pipeline FinSent — Démarrage\n")
    load_sp500_assets()
    fetch_yahoo_news()
    run_sentiment_analysis()
    print("\n✅ Pipeline terminé avec succès !\n")
