"""
Autonomyx Local Task Classifier
Sentence-transformers embeddings + LogisticRegression
Serves POST /classify on port 8100 (internal network only)
"""
import os, json, joblib, logging
import numpy as np
from pathlib import Path
from fastapi import FastAPI
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import cross_val_score

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("classifier")

MODEL_NAME   = os.environ.get("MODEL_NAME", "all-MiniLM-L6-v2")
MODEL_DIR    = Path("/app/model")
TRAIN_PATH   = Path("/app/training_data.json")
THRESHOLD    = float(os.environ.get("CONFIDENCE_THRESHOLD", "0.80"))
RETRAIN      = os.environ.get("AUTO_RETRAIN_ON_STARTUP", "true").lower() == "true"

app = FastAPI()

# ── State ─────────────────────────────────────────────────────────────────
embedder: SentenceTransformer = None
clf: LogisticRegression = None
le: LabelEncoder = None

# ── Training ──────────────────────────────────────────────────────────────
def load_training_data():
    data = json.loads(TRAIN_PATH.read_text())
    texts  = [e["text"]  for e in data["examples"]]
    labels = [e["label"] for e in data["examples"]]
    return texts, labels


def train():
    global clf, le
    log.info("Training classifier...")
    texts, labels = load_training_data()

    le = LabelEncoder()
    y = le.fit_transform(labels)
    X = embedder.encode(texts, show_progress_bar=False)

    clf = LogisticRegression(max_iter=1000, C=4.0, solver="lbfgs", multi_class="multinomial")
    scores = cross_val_score(clf, X, y, cv=5, scoring="accuracy")
    clf.fit(X, y)

    log.info(f"Trained. CV accuracy: {scores.mean():.3f} ± {scores.std():.3f} ({len(texts)} examples)")

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(clf, MODEL_DIR / "clf.joblib")
    joblib.dump(le,  MODEL_DIR / "le.joblib")
    log.info(f"Model saved to {MODEL_DIR}")


def load_or_train():
    clf_path = MODEL_DIR / "clf.joblib"
    le_path  = MODEL_DIR / "le.joblib"
    if clf_path.exists() and le_path.exists() and not RETRAIN:
        global clf, le
        clf = joblib.load(clf_path)
        le  = joblib.load(le_path)
        log.info("Loaded existing model from disk")
    else:
        train()


# ── Startup ───────────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    global embedder
    log.info(f"Loading embedding model: {MODEL_NAME}")
    embedder = SentenceTransformer(MODEL_NAME)
    load_or_train()
    log.info("Classifier ready")


# ── API ───────────────────────────────────────────────────────────────────
class ClassifyRequest(BaseModel):
    text: str
    top_n: int = 3

class ClassifyResponse(BaseModel):
    task: str
    confidence: float
    below_threshold: bool
    top_n: list[dict]     # [{task, confidence}]
    threshold: float

@app.post("/classify", response_model=ClassifyResponse)
def classify(body: ClassifyRequest):
    emb   = embedder.encode([body.text[:2000]])
    probs = clf.predict_proba(emb)[0]
    idx   = np.argsort(probs)[::-1]

    top_n = [
        {"task": le.classes_[i], "confidence": round(float(probs[i]), 4)}
        for i in idx[:body.top_n]
    ]
    best_task = le.classes_[idx[0]]
    best_conf = float(probs[idx[0]])

    return ClassifyResponse(
        task=best_task,
        confidence=round(best_conf, 4),
        below_threshold=best_conf < THRESHOLD,
        top_n=top_n,
        threshold=THRESHOLD,
    )

@app.post("/retrain")
def retrain():
    train()
    return {"status": "retrained", "examples": len(load_training_data()[0])}

@app.get("/health")
def health():
    return {"status": "ok", "model": MODEL_NAME, "threshold": THRESHOLD}
