import requests
import pandas as pd
from io import StringIO
from datetime import datetime
import yfinance as yf

import psycopg
from psycopg.rows import dict_row

from dashboard.model_inference import predict_sentiment


# =========================
# CONFIG DB
# =========================
DB_NAME = "AnalyseSentiments"
DB_USER = "postgres"
DB_PASS = "soukroumde"        
DB_HOST = "127.0.0.1"
DB_PORT = 5432

CONNINFO = f"dbname={DB_NAME} user={DB_USER} password={DB_PASS} host={DB_HOST} port={DB_PORT}"


# =========================
# 1) Remplir ACTIF depuis S&P500
# =========================
url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
headers = {"User-Agent": "Mozilla/5.0"}

response = requests.get(url, headers=headers, timeout=30)
response.raise_for_status()

sp500 = pd.read_html(StringIO(response.text))[0]

df_actifs = pd.DataFrame({
    "nom_actif": sp500["Security"],
    "ticker": sp500["Symbol"],
    "secteur": sp500["GICS Sector"]
})

print(df_actifs.head())

values = list(df_actifs[["nom_actif", "ticker", "secteur"]].itertuples(index=False, name=None))

with psycopg.connect(CONNINFO) as conn:
    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO actif (nom_actif, ticker, secteur)
            VALUES (%s, %s, %s)
            ON CONFLICT (ticker) DO NOTHING
            """,
            values
        )
    conn.commit()

print("Insertion des tickers S&P500 terminée !")


# =========================
# 2) Récupérer les news Yahoo Finance -> DOCUMENT + CONCERNE
# =========================
with psycopg.connect(CONNINFO, row_factory=dict_row) as conn:
    with conn.cursor() as cur:

        # source Yahoo Finance
        cur.execute("""
            INSERT INTO source (nom_source, type_source, fiabilite)
            VALUES ('Yahoo Finance', 'API', 0.95)
            ON CONFLICT (nom_source) DO UPDATE SET fiabilite = EXCLUDED.fiabilite
            RETURNING id_source
        """)
        id_source = cur.fetchone()["id_source"]

        cur.execute("SELECT id_actif, ticker FROM actif WHERE ticker IS NOT NULL")
        actifs = cur.fetchall()

        print(f"{len(actifs)} tickers récupérés dans la table ACTIF.")

        for a in actifs:
            id_actif = a["id_actif"]
            ticker = a["ticker"]

            try:
                t = yf.Ticker(ticker)
                news_list = t.news or []
                if not news_list:
                    print(f"Aucune news pour {ticker}")
                    continue

                print(f"{ticker} : {len(news_list)} articles trouvés")

                for article in news_list:
                    content = article.get("content") or {}
                    titre = content.get("title")
                    contenu = content.get("summary") or ""
                    pubDate = content.get("pubDate")

                    if not titre or not pubDate:
                        continue

                    date_pub = datetime.fromisoformat(pubDate.replace("Z", "+00:00")).date()

                    # Insert doc 
                    cur.execute("""
                        INSERT INTO document (titre, contenu, date_publication, id_source)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (titre, date_publication, id_source)
                        DO UPDATE SET contenu = EXCLUDED.contenu
                        RETURNING id_document
                    """, (titre, contenu, date_pub, id_source))

                    id_doc = cur.fetchone()["id_document"]

                    # lien concerne
                    cur.execute("""
                        INSERT INTO concerne (id_document, id_actif)
                        VALUES (%s, %s)
                        ON CONFLICT (id_document, id_actif) DO NOTHING
                    """, (id_doc, id_actif))

                conn.commit()

            except Exception as e:
                print(f"Erreur récupération/insertion news pour {ticker} :", e)

print("Stockage de toutes les news Yahoo Finance terminé !")


# =========================
# 3) Analyse sentiments avec TON FinBERT fine-tuné -> ANALYSE_SENTIMENT
# =========================
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
        print(f"{len(documents)} documents à analyser.")

        for idx, r in enumerate(documents, 1):
            texte = f"{r['titre']}. {r['contenu']}"
            score, label = predict_sentiment(texte)   #  modèle

            cur.execute("""
                INSERT INTO analyse_sentiment (polarite, score, date_analyse, id_document, id_actif)
                VALUES (%s, %s, %s, %s, %s)
            """, (label, float(score), datetime.now(), r["id_document"], r["id_actif"]))

            if idx % 100 == 0 or idx == len(documents):
                print(f"{idx}/{len(documents)} documents analysés.")

        conn.commit()

print(" Toutes les news ont été analysées et stockées avec FinBERT !")
