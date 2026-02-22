"""
Module d'inférence FinBERT.

Charge le modèle FinBERT fine-tuné et expose la fonction `predict_sentiment(text)`
qui retourne un tuple (score, label) pour un texte donné.
"""

import os
import re

import torch
import torch.nn.functional as F
from transformers import BertTokenizer, BertForSequenceClassification


# =============================================================================
# Chargement du modèle (une seule fois au démarrage)
# =============================================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(BASE_DIR, "models_ml", "finbert_finetuned")

tokenizer = BertTokenizer.from_pretrained("ProsusAI/finbert")
model = BertForSequenceClassification.from_pretrained(MODEL_DIR)
model.eval()
model.to("cpu")

LABEL_MAP = ["negative", "neutral", "positive"]


# =============================================================================
# Prétraitement
# =============================================================================

def clean_text(text: str) -> str:
    """Nettoie un texte brut pour l'inférence."""
    text = text.lower()
    text = re.sub(r"http\S+", " <URL> ", text)
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


# =============================================================================
# Prédiction
# =============================================================================

def predict_sentiment(text: str) -> tuple[float, str]:
    """
    Prédit le sentiment d'un texte financier.

    Args:
        text: Texte brut à analyser.

    Returns:
        Tuple (score, label) où score ∈ [0, 1] et label ∈ {negative, neutral, positive}.
    """
    text_clean = clean_text(text)

    inputs = tokenizer(
        text_clean,
        return_tensors="pt",
        truncation=True,
        padding=True,
        max_length=128,
    )

    with torch.no_grad():
        outputs = model(**inputs)
        logits = outputs.logits
        probs = F.softmax(logits, dim=1)[0]

    pred = probs.argmax().item()
    return probs[pred].item(), LABEL_MAP[pred]
