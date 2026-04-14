import logging
from dataclasses import dataclass

import torch
import numpy as np
from transformers import pipeline, AutoTokenizer, AutoModel
from scipy.spatial.distance import cosine

logger = logging.getLogger(__name__)


@dataclass
class SentimentResult:
    label: str        # positive / negative / neutral
    score: float      # 0.0 to 1.0
    model_name: str   # "finbert" or "muril"


# ---------------------------------------------------------------------------
# Singleton model holders — loaded once on first call
# ---------------------------------------------------------------------------

_finbert_pipeline = None
_muril_tokenizer = None
_muril_model = None
_muril_seed_embeddings: dict[str, np.ndarray] | None = None

MURIL_SEEDS = {
    "positive": [
        "शेयर बाजार में तेजी और बढ़त",
        "कंपनी को भारी मुनाफा हुआ",
        "शेयरों में उछाल आया",
    ],
    "negative": [
        "शेयर बाजार में भारी गिरावट",
        "कंपनी को नुकसान हुआ",
        "बाजार में मंदी का माहौल",
    ],
    "neutral": [
        "बाजार स्थिर रहा कोई बदलाव नहीं",
        "सामान्य कारोबार जारी रहा",
        "कोई खास हलचल नहीं दिखी",
    ],
}


def _load_finbert():
    global _finbert_pipeline
    if _finbert_pipeline is not None:
        return
    logger.info("Loading FinBERT model (ProsusAI/finbert) ...")
    _finbert_pipeline = pipeline(
        "text-classification",
        model="ProsusAI/finbert",
        tokenizer="ProsusAI/finbert",
        top_k=None,
    )
    logger.info("FinBERT model loaded successfully.")


def _mean_pooling(model_output, attention_mask):
    """Mean pooling over token embeddings, masked by attention."""
    token_embeddings = model_output.last_hidden_state
    input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
    return (
        torch.sum(token_embeddings * input_mask_expanded, dim=1)
        / torch.clamp(input_mask_expanded.sum(dim=1), min=1e-9)
    )


def _embed_texts(texts: list[str]) -> np.ndarray:
    """Encode texts with MuRIL and return mean-pooled numpy vectors."""
    encoded = _muril_tokenizer(texts, padding=True, truncation=True, max_length=128, return_tensors="pt")
    with torch.no_grad():
        output = _muril_model(**encoded)
    pooled = _mean_pooling(output, encoded["attention_mask"])
    return pooled.numpy()


def _load_muril():
    global _muril_tokenizer, _muril_model, _muril_seed_embeddings
    if _muril_model is not None:
        return
    logger.info("Loading MuRIL model (google/muril-base-cased) ...")
    _muril_tokenizer = AutoTokenizer.from_pretrained("google/muril-base-cased")
    _muril_model = AutoModel.from_pretrained("google/muril-base-cased")
    _muril_model.eval()
    logger.info("MuRIL model loaded successfully.")

    # Pre-compute seed embeddings
    _muril_seed_embeddings = {}
    for label, phrases in MURIL_SEEDS.items():
        vecs = _embed_texts(phrases)
        _muril_seed_embeddings[label] = vecs.mean(axis=0)


# ---------------------------------------------------------------------------
# Language detection
# ---------------------------------------------------------------------------

def _is_hindi(text: str) -> bool:
    """Return True if more than 30% of characters are non-ASCII (likely Hindi/Hinglish)."""
    if not text:
        return False
    non_ascii = sum(1 for ch in text if ord(ch) > 127)
    return (non_ascii / len(text)) > 0.30


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def analyse_sentiment(text: str) -> SentimentResult:
    """Run sentiment analysis on a piece of text. Auto-selects FinBERT or MuRIL."""
    if _is_hindi(text):
        return _analyse_muril(text)
    return _analyse_finbert(text)


def _analyse_finbert(text: str) -> SentimentResult:
    try:
        _load_finbert()
        results = _finbert_pipeline(text[:512])
        # results is a list of lists; take the top prediction
        top = max(results[0], key=lambda x: x["score"])
        label = top["label"].lower()
        if label not in ("positive", "negative", "neutral"):
            label = "neutral"
        return SentimentResult(label=label, score=round(top["score"], 4), model_name="finbert")
    except Exception as e:
        logger.error("FinBERT inference failed: %s", e)
        return SentimentResult(label="neutral", score=0.0, model_name="finbert")


def _analyse_muril(text: str) -> SentimentResult:
    try:
        _load_muril()
        text_vec = _embed_texts([text])[0]

        labels = []
        sims = []
        for label, seed_vec in _muril_seed_embeddings.items():
            sim = 1.0 - cosine(text_vec, seed_vec)
            labels.append(label)
            sims.append(sim)

        # Softmax with temperature scaling to amplify small differences
        sims_arr = np.array(sims)
        temperature = 0.01
        exp_scores = np.exp((sims_arr - sims_arr.max()) / temperature)
        probs = exp_scores / exp_scores.sum()

        best_idx = int(np.argmax(probs))
        return SentimentResult(
            label=labels[best_idx],
            score=round(float(probs[best_idx]), 4),
            model_name="muril",
        )
    except Exception as e:
        logger.error("MuRIL inference failed: %s", e)
        return SentimentResult(label="neutral", score=0.0, model_name="muril")
