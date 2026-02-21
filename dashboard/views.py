from django.shortcuts import render
from .model_inference import predict_sentiment
from .models import PredictionHistory
from django.db import connection

def sentiment_view(request):
    analysis = None
    query = ""

    if request.method == "POST":
        query = request.POST.get("query", "")
        score, label = predict_sentiment(query)

        label_fr = {
            "positive": "Positif",
            "neutral": "Neutre",
            "negative": "Négatif"
        }[label]

        PredictionHistory.objects.create(
            query=query,
            sentiment=label_fr,
            score=score
        )

        analysis = {
            "summary": f"Le sentiment détecté est {label_fr.lower()}",
            "label": label_fr,
            "score": score,
            "details": [
                {"source": "Actualités", "sentiment": label_fr, "score": score},
                {"source": "Réseaux sociaux", "sentiment": label_fr, "score": score * 0.9},
                {"source": "Crypto", "sentiment": label_fr, "score": score * 1.1},
            ],
        }

    history = PredictionHistory.objects.all()[:10]

    return render(request, "dashboard/sentiment_dashboard.html", {
        "analysis": analysis,
        "query": query,
        "history": history
    })

#--------------------------------------------------------------------------------------------------------------------------------------

from django.shortcuts import render
from django.db import connection

def latest_news(request):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT
                d.id_document,
                d.titre,
                d.contenu,
                d.date_publication,
                ans.polarite,
                ans.score
            FROM document d
            LEFT JOIN analyse_sentiment ans
              ON ans.id_document = d.id_document
            ORDER BY d.date_publication DESC, d.id_document DESC
            LIMIT 50;
        """)
        rows = cursor.fetchall()

    documents = []
    for (id_doc, titre, contenu, date_pub, polarite, score) in rows:
        # mapping label vers FR (optionnel)
        polarite_fr = None
        if polarite == "positive":
            polarite_fr = "Positif"
        elif polarite == "negative":
            polarite_fr = "Négatif"
        elif polarite == "neutral":
            polarite_fr = "Neutre"

        documents.append({
            "titre": titre,
            "contenu": contenu,
            "date_publication": date_pub,
            "polarite": polarite_fr,   # "Positif"/"Neutre"/"Négatif" ou None
            "score": score,
        })

    return render(request, "dashboard/latest_news.html", {"documents": documents})

from django.http import JsonResponse

def news_feed(request):
    """
    Retourne les derniers docs (analysés ou non) en JSON.
    Paramètre optionnel: after_id=123 (retourne uniquement les docs plus récents que cet id)
    """
    after_id = request.GET.get("after_id")
    after_id = int(after_id) if after_id and after_id.isdigit() else 0

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT
                d.id_document,
                d.titre,
                d.contenu,
                d.date_publication,
                ans.polarite,
                ans.score
            FROM document d
            LEFT JOIN LATERAL (
                SELECT polarite, score
                FROM analyse_sentiment s
                WHERE s.id_document = d.id_document
                ORDER BY s.date_analyse DESC, s.id_analyse DESC
                LIMIT 1
            ) ans ON TRUE
            WHERE d.id_document > %s
            ORDER BY d.id_document ASC
            LIMIT 50
        """, (after_id,))
        rows = cursor.fetchall()

    def fr(p):
        return {"positive": "Positif", "negative": "Négatif", "neutral": "Neutre"}.get(p)

    data = []
    for (id_doc, titre, contenu, date_pub, polarite, score) in rows:
        data.append({
            "id_document": id_doc,
            "titre": titre,
            "contenu": contenu or "",
            "date_publication": date_pub.isoformat() if date_pub else "",
            "polarite": fr(polarite),
            "score": float(score) if score is not None else None,
        })

    return JsonResponse({"items": data})
#................................................................................................................

def statistics_view(request):
    # 1) Totaux par polarité
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT COALESCE(polarite,'unknown') AS polarite, COUNT(*) as n
            FROM analyse_sentiment
            GROUP BY COALESCE(polarite,'unknown')
        """)
        rows = cursor.fetchall()

    counts = {"positive": 0, "neutral": 0, "negative": 0}
    total = 0
    for pol, n in rows:
        if pol in counts:
            counts[pol] = int(n)
        total += int(n)

    def pct(x):
        return round((x * 100.0 / total), 1) if total else 0.0

    # 2) Score moyen global
    with connection.cursor() as cursor:
        cursor.execute("SELECT AVG(score) FROM analyse_sentiment")
        avg_score = cursor.fetchone()[0] or 0.0

    # 3) Série par jour (7 derniers jours)
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT DATE(date_analyse) as d,
                   SUM(CASE WHEN polarite='positive' THEN 1 ELSE 0 END) as pos,
                   SUM(CASE WHEN polarite='neutral' THEN 1 ELSE 0 END) as neu,
                   SUM(CASE WHEN polarite='negative' THEN 1 ELSE 0 END) as neg
            FROM analyse_sentiment
            WHERE date_analyse >= NOW() - INTERVAL '7 days'
            GROUP BY DATE(date_analyse)
            ORDER BY d ASC
        """)
        daily_rows = cursor.fetchall()

    daily = []
    for d, pos, neu, neg in daily_rows:
        daily.append({
            "date": d.isoformat(),
            "positive": int(pos or 0),
            "neutral": int(neu or 0),
            "negative": int(neg or 0),
        })

    # 4) Top tickers analysés
    top_tickers = []
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT a.ticker, COUNT(*) as n
            FROM analyse_sentiment s
            JOIN actif a ON a.id_actif = s.id_actif
            WHERE a.ticker IS NOT NULL
            GROUP BY a.ticker
            ORDER BY n DESC
            LIMIT 10
        """)
        for ticker, n in cursor.fetchall():
            top_tickers.append({"ticker": ticker, "count": int(n)})

    # 5) Sentiment moyen par actif
    avg_by_actif = []
    with connection.cursor() as cur:
        cur.execute("""
            SELECT
                a.ticker,
                a.nom_actif,
                AVG(s.score) AS avg_score,
                AVG(
                    CASE s.polarite
                        WHEN 'positive' THEN 1
                        WHEN 'neutral'  THEN 0
                        WHEN 'negative' THEN -1
                        ELSE 0
                    END
                ) AS mean_polarity
            FROM analyse_sentiment s
            JOIN actif a ON a.id_actif = s.id_actif
            WHERE a.ticker IS NOT NULL
            GROUP BY a.ticker, a.nom_actif
            ORDER BY mean_polarity DESC, avg_score DESC
            LIMIT 30
        """)
        rows = cur.fetchall()

    def label_from_mean(x):
        if x is None:
            return "Neutre"
        if x > 0.15:
            return "Positif"
        if x < -0.15:
            return "Négatif"
        return "Neutre"

    for ticker, nom_actif, a_score, mean_pol in rows:
        avg_by_actif.append({
            "ticker": ticker,
            "nom_actif": nom_actif,
            "avg_score": float(a_score or 0.0),
            "label": label_from_mean(mean_pol),
        })

    # 6) Construire stats (utilisé par ton template)
    stats = {
        "total": total,
        "avg_score": float(avg_score or 0.0),
        "count_positive": counts["positive"],
        "count_neutral": counts["neutral"],
        "count_negative": counts["negative"],
        "pct_positive": pct(counts["positive"]),
        "pct_neutral": pct(counts["neutral"]),
        "pct_negative": pct(counts["negative"]),
    }

    context = {
        "stats": stats,
        "daily": daily,
        "top_tickers": top_tickers,
        "avg_by_actif": avg_by_actif,
    }
    return render(request, "dashboard/statistics.html", context)
