import os
import torch
from transformers import BertTokenizer, BertForSequenceClassification
import torch.nn.functional as F

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(BASE_DIR, "models_ml", "finbert_finetuned")

tokenizer = BertTokenizer.from_pretrained("ProsusAI/finbert")

model = BertForSequenceClassification.from_pretrained(MODEL_DIR)
model.eval()
model.to("cpu")


import re
def clean_text(text):
    text = text.lower()
    text = re.sub(r"http\S+", " <URL> ", text)
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


label_map = ["negative", "neutral", "positive"]


def predict_sentiment(text):
    text_clean = clean_text(text)

    inputs = tokenizer(
        text_clean,
        return_tensors="pt",
        truncation=True,
        padding=True,
        max_length=128
    )

    with torch.no_grad():
        outputs = model(**inputs)
        logits = outputs.logits
        probs = F.softmax(logits, dim=1)[0]

    pred = probs.argmax().item()
    return probs[pred].item(), label_map[pred]
