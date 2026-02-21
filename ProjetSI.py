import requests
import pandas as pd
from io import StringIO
import psycopg2
from psycopg2.extras import execute_values





#Remplissage de la table Actif a partir des entreprises du S&P500.

url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
headers = {"User-Agent": "Mozilla/5.0"}

response = requests.get(url, headers=headers)
response.raise_for_status()  

html_io = StringIO(response.text)
sp500 = pd.read_html(html_io)[0]


df_actifs = pd.DataFrame({
    'nom_actif': sp500['Security'],
    'ticker': sp500['Symbol'],
    'secteur': sp500['GICS Sector']
})

print(df_actifs.head())  

#Connection a la base postgreSQL
conn = psycopg2.connect(
    dbname="AnalyseSentiments",
    user="postgres",
    password="23112003",
    host="localhost",
    port=5432
)
cur = conn.cursor()


values = list(df_actifs[['nom_actif', 'ticker', 'secteur']].itertuples(index=False, name=None))



execute_values(cur,
    """
    INSERT INTO ACTIF (nom_actif, ticker, secteur)
    VALUES %s
    ON CONFLICT (ticker) DO NOTHING
    """,
    values
)

conn.commit()
cur.close()
conn.close()

print("Insertion des tickers S&P500 terminée !")





#Recuperer les news de YahooFinance 

import psycopg2
from datetime import datetime
import yfinance as yf


conn = psycopg2.connect(
    dbname="AnalyseSentiments",
    user="postgres",
    password="soukroumde",
    host="localhost",
    port=5432
)
cur = conn.cursor()


cur.execute("""
    INSERT INTO SOURCE (nom_source, type_source, fiabilite)
    VALUES ('Yahoo Finance', 'API', 0.95)
    ON CONFLICT (nom_source) DO NOTHING
    RETURNING id_source
""")
res = cur.fetchone()
if res:
    id_source = res[0]
else:
    cur.execute("SELECT id_source FROM SOURCE WHERE nom_source='Yahoo Finance'")
    id_source = cur.fetchone()[0]


cur.execute("SELECT ticker FROM ACTIF")
tickers = [row[0] for row in cur.fetchall()]
print(f"{len(tickers)} tickers récupérés dans la table ACTIF.")


for ticker in tickers:
    try:
        t = yf.Ticker(ticker)
        news_list = t.news
        if not news_list:
            print(f"Aucune news pour {ticker}")
            continue

        print(f"{ticker} : {len(news_list)} articles trouvés")

        for article in news_list:
            try:
                
                content = article.get('content', {})
                titre = content.get('title')
                contenu = content.get('summary') or ""
                pubDate = content.get('pubDate')

                if not titre or not pubDate:
                    continue  

                
                date_pub = datetime.fromisoformat(pubDate.replace('Z', '+00:00')).date()

                # Insérer le document
                cur.execute("""
                    INSERT INTO DOCUMENT (titre, contenu, date_publication, id_source)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id_document
                """, (titre, contenu, date_pub, id_source))
                id_doc = cur.fetchone()[0]

                # Lier le document à l'actif si ticker existe
                cur.execute("SELECT id_actif FROM ACTIF WHERE ticker=%s", (ticker,))
                res_actif = cur.fetchone()
                if res_actif:
                    id_actif = res_actif[0]
                    cur.execute("INSERT INTO CONCERNE (id_document, id_actif) VALUES (%s, %s)", (id_doc, id_actif))

                
                conn.commit()
                print(f"Document inséré pour {ticker} : id {id_doc}")

            except Exception as e:
                print(f"Erreur insertion article pour {ticker} :", e)

    except Exception as e:
        print(f"Erreur récupération news pour {ticker} :", e)

cur.close()
conn.close()
print("Stockage de toutes les news Yahoo Finance terminé !")







#Faire passer les news par le modele deja entraine

import psycopg2
from datetime import datetime
import pickle
import re
import numpy as np
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.sequence import pad_sequences
from sklearn.preprocessing import LabelEncoder



DB_NAME = "AnalyseSentiments"
DB_USER = "postgres"
DB_PASS = "23112003"
DB_HOST = "localhost"
DB_PORT = 5432

MAX_LEN = 30
LABELS = ["negative", "neutral", "positive"]

MODEL_PATH = "sentiment_lstm.h5"
TOKENIZER_PATH = "tokenizer.pkl"



def clean_text(text):
    text = text.lower()
    text = re.sub(r"http\S+", " <URL> ", text)
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def prepare_text(text, tokenizer):
    text = clean_text(text)
    seq = tokenizer.texts_to_sequences([text])
    padded = pad_sequences(seq, maxlen=MAX_LEN, padding='post')
    return padded



print("Chargement du modèle et du tokenizer...")
model = load_model(MODEL_PATH)
with open(TOKENIZER_PATH, "rb") as f:
    tokenizer = pickle.load(f)

label_encoder = LabelEncoder()
label_encoder.fit(LABELS)



conn = psycopg2.connect(
    dbname=DB_NAME,
    user=DB_USER,
    password=DB_PASS,
    host=DB_HOST,
    port=DB_PORT
)
cur = conn.cursor()



cur.execute("""
    SELECT d.id_document, d.titre, d.contenu, c.id_actif
    FROM DOCUMENT d
    JOIN CONCERNE c ON d.id_document = c.id_document
    LEFT JOIN ANALYSE_SENTIMENT s ON s.id_document = d.id_document
    WHERE s.id_document IS NULL
""")
documents = cur.fetchall()
print(f"{len(documents)} documents à analyser.")



for idx, (id_doc, titre, contenu, id_actif) in enumerate(documents, 1):
    texte = f"{titre}. {contenu}"
    padded = prepare_text(texte, tokenizer)
    
    pred = model.predict(padded, verbose=0)
    label_int = np.argmax(pred, axis=1)[0]
    label_str = label_encoder.inverse_transform([label_int])[0]
    score = float(pred[0][label_int])
    
    # STOCKER DANS LA BASE
    cur.execute("""
        INSERT INTO ANALYSE_SENTIMENT (polarite, score, date_analyse, id_document, id_actif)
        VALUES (%s, %s, %s, %s, %s)
    """, (label_str, score, datetime.now(), id_doc, id_actif))
    
    # Affichage pour suivre l’avancement
    if idx % 100 == 0 or idx == len(documents):
        print(f"{idx}/{len(documents)} documents analysés.")




conn.commit()
cur.close()
conn.close()
print("Toutes les news ont été analysées et stockées avec succès !")
