# Local Language Translation — Autonomyx LLM Gateway

## Licence-safe models only

> ⚠️ NLLB-200 and SeamlessM4T are CC-BY-NC 4.0 — NOT commercially usable.
> Do not use either in the gateway stack. All models below are Apache 2.0 or MIT.

## Architecture

```
Incoming request
  │
  ├─ Language detection (fastText LID model — Apache 2.0, 917KB)
  │
  ├─ Language is natively supported by target model?
  │   │
  │   ├─ YES → route directly (Qwen3-30B-A3B, Gemma 4B)
  │   │         No translation overhead. Best quality.
  │   │
  │   └─ NO → pivot translation
  │             IndicTrans2: Indian languages ↔ English
  │             Opus-MT:     Arabic + Southeast Asian ↔ English
  │
  └─ Response → translate back to original language if input was non-English
```

---

## Model selection — commercial safe

### Tier 1: Native multilingual (already in Ollama stack)

These models handle Indian languages, Arabic, and major Southeast Asian languages
natively — no translation layer needed for them.

| Model | Languages | Quality | RAM | Notes |
|---|---|---|---|---|
| Qwen3-30B-A3B | 100+ incl. Hindi, Tamil, Telugu, Bengali, Gujarati, Marathi, Kannada, Malayalam, Urdu, Arabic, Thai, Vietnamese, Indonesian, Malay | ⭐⭐⭐⭐⭐ | 19GB | Already always-on. Use first. |
| Gemma 3 9B | Hindi, Tamil, Telugu, Malayalam, Kannada, Bengali, Gujarati, Marathi, Arabic | ⭐⭐⭐⭐ | 6GB | Already in stack (long_context slot) |
| Llama 3.1 8B | Hindi, Arabic, partial Indian languages | ⭐⭐⭐ | 6GB | Already in stack |

**For most requests — use native Qwen3-30B-A3B directly.** No translation sidecar needed.
Qwen3 was trained on massive multilingual data including all major Indian languages.

### Tier 2: Specialised translation sidecar (for low-resource accuracy)

Use when Qwen3 native quality is insufficient for a specific language pair.
Measured by human feedback score < 0.7 on a language pair after 30 days.

#### IndicTrans2 — 22 Indian languages ↔ English
**Licence: MIT (AI4Bharat) — commercial safe ✅**

- Covers: Assamese, Bengali, Bodo, Dogri, Gujarati, Hindi, Kannada, Kashmiri,
  Konkani, Maithili, Malayalam, Manipuri, Marathi, Nepali, Odia, Punjabi,
  Sanskrit, Santali, Sindhi, Tamil, Telugu, Urdu
- Architecture: Encoder-Decoder, 200M-1.1B parameters
- RAM: ~2-4GB (200M distilled) or ~4-6GB (1.1B full)
- Speed: ~100-300 tokens/sec on CPU
- Quality: SOTA on Indian languages, beats GPT-4 on several Dravidian language pairs
- Self-hostable: HuggingFace model, standard transformers

```bash
# Pull IndicTrans2 (distilled, commercial safe)
pip install indic-trans  # AI4Bharat's library
# or use HuggingFace directly:
# ai4bharat/indictrans2-indic-en-dist-200M (Indic → English)
# ai4bharat/indictrans2-en-indic-dist-200M (English → Indic)
```

#### Helsinki-NLP Opus-MT — Arabic + Southeast Asian
**Licence: Apache 2.0 — commercial safe ✅**

- Covers: Arabic (ar), Thai (th), Vietnamese (vi), Indonesian (id),
  Malay (ms), Tagalog (tl), Burmese (my), Khmer (km), Sinhala (si)
- Architecture: MarianMT (small encoder-decoder)
- RAM: ~300MB per language pair
- Speed: Very fast — ~500-1000 tokens/sec on CPU
- Quality: Good for common language pairs, acceptable for Southeast Asian
- Self-hostable: HuggingFace, standard transformers

```python
# Example: Arabic → English
from transformers import MarianMTModel, MarianTokenizer
model_name = "Helsinki-NLP/opus-mt-ar-en"
tokenizer = MarianTokenizer.from_pretrained(model_name)
model = MarianMTModel.from_pretrained(model_name)
```

---

## docker-compose — translation sidecar

```yaml
  translator:
    image: python:3.12-slim
    container_name: autonomyx-translator
    restart: always
    networks:
      - coolify
    environment:
      - INDICTRANS2_DEVICE=cpu
      - OPUS_MT_CACHE=/models/opus
    volumes:
      - translator-models:/models
      - ./translator_server.py:/app/translator_server.py:ro
    command: ["python", "/app/translator_server.py"]
    mem_limit: 8g      # IndicTrans2 1.1B + Opus-MT models
```

Add to `volumes:`:
```yaml
  translator-models:
```

---

## `translator_server.py` — FastAPI translation service

```python
"""
Autonomyx Translation Sidecar
Serves POST /translate on port 8200 (internal network only)
Models: IndicTrans2 (Indian languages) + Opus-MT (Arabic + SEA)
Language detection: fastText LID
"""

import os, logging
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("translator")
app = FastAPI()

# ── Language codes supported natively by Qwen3 (no translation needed) ────
QWEN3_NATIVE = {
    "en", "zh", "hi", "ar", "fr", "de", "es", "pt", "ru", "ja", "ko",
    "th", "vi", "id", "ms", "bn", "gu", "mr", "ta", "te", "kn", "ml",
    "pa", "ur", "ne", "si", "my", "km", "tl", "tr", "it", "nl", "pl",
}

# ── IndicTrans2 language codes ─────────────────────────────────────────────
INDICTRANS2_CODES = {
    "as": "asm_Beng", "bn": "ben_Beng", "brx": "brx_Deva",
    "doi": "doi_Deva", "gu": "guj_Gujr", "hi": "hin_Deva",
    "kn": "kan_Knda", "ks": "kas_Arab", "kok": "kok_Deva",
    "mai": "mai_Deva", "ml": "mal_Mlym", "mni": "mni_Mtei",
    "mr": "mar_Deva", "ne": "npi_Deva", "or": "ory_Orya",
    "pa": "pan_Guru", "sa": "san_Deva", "sat": "sat_Olck",
    "sd": "snd_Arab", "ta": "tam_Taml", "te": "tel_Telu",
    "ur": "urd_Arab",
}

# ── Opus-MT language pairs (source_code: model_name) ──────────────────────
OPUS_MT_MODELS = {
    "ar": "Helsinki-NLP/opus-mt-ar-en",
    "th": "Helsinki-NLP/opus-mt-th-en",
    "vi": "Helsinki-NLP/opus-mt-vi-en",
    "id": "Helsinki-NLP/opus-mt-id-en",
    "ms": "Helsinki-NLP/opus-mt-ms-en",
    "tl": "Helsinki-NLP/opus-mt-tl-en",
    "si": "Helsinki-NLP/opus-mt-si-en",
}
# Reverse (en → target)
OPUS_MT_EN_MODELS = {
    "ar": "Helsinki-NLP/opus-mt-en-ar",
    "th": "Helsinki-NLP/opus-mt-en-th",
    "vi": "Helsinki-NLP/opus-mt-en-vi",
    "id": "Helsinki-NLP/opus-mt-en-id",
    "ms": "Helsinki-NLP/opus-mt-en-ms",
}

# ── State ──────────────────────────────────────────────────────────────────
indictrans2_en = None    # Indic → English
indictrans2_indic = None # English → Indic
opus_models = {}         # lang_code → (tokenizer, model)
lid_model = None         # fastText language detection


@app.on_event("startup")
async def startup():
    global indictrans2_en, indictrans2_indic, lid_model
    import fasttext, urllib.request

    log.info("Loading fastText LID model (917KB)...")
    lid_path = "/models/lid.176.ftz"
    if not os.path.exists(lid_path):
        urllib.request.urlretrieve(
            "https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.ftz",
            lid_path
        )
    lid_model = fasttext.load_model(lid_path)

    log.info("Loading IndicTrans2 (Indic→EN)...")
    indictrans2_en = {
        "tokenizer": AutoTokenizer.from_pretrained(
            "ai4bharat/indictrans2-indic-en-dist-200M", trust_remote_code=True),
        "model": AutoModelForSeq2SeqLM.from_pretrained(
            "ai4bharat/indictrans2-indic-en-dist-200M", trust_remote_code=True),
    }

    log.info("Loading IndicTrans2 (EN→Indic)...")
    indictrans2_indic = {
        "tokenizer": AutoTokenizer.from_pretrained(
            "ai4bharat/indictrans2-en-indic-dist-200M", trust_remote_code=True),
        "model": AutoModelForSeq2SeqLM.from_pretrained(
            "ai4bharat/indictrans2-en-indic-dist-200M", trust_remote_code=True),
    }

    log.info("Translator ready.")


def detect_language(text: str) -> str:
    """Returns ISO 639-1 language code."""
    labels, _ = lid_model.predict(text[:200].replace("\n", " "))
    return labels[0].replace("__label__", "")


def translate_to_english(text: str, src_lang: str) -> str:
    """Translate from any supported language to English."""
    if src_lang in INDICTRANS2_CODES:
        tok = indictrans2_en["tokenizer"]
        mod = indictrans2_en["model"]
        src_code = INDICTRANS2_CODES[src_lang]
        inputs = tok(text, return_tensors="pt", src_lang=src_code)
        with torch.no_grad():
            output = mod.generate(**inputs, forced_bos_token_id=tok.lang_code_to_id["eng_Latn"])
        return tok.decode(output[0], skip_special_tokens=True)

    elif src_lang in OPUS_MT_MODELS:
        if src_lang not in opus_models:
            model_name = OPUS_MT_MODELS[src_lang]
            opus_models[src_lang] = {
                "tokenizer": AutoTokenizer.from_pretrained(model_name),
                "model": AutoModelForSeq2SeqLM.from_pretrained(model_name),
            }
        tok = opus_models[src_lang]["tokenizer"]
        mod = opus_models[src_lang]["model"]
        inputs = tok([text], return_tensors="pt", padding=True)
        with torch.no_grad():
            output = mod.generate(**inputs)
        return tok.decode(output[0], skip_special_tokens=True)

    return text  # passthrough if unsupported


def translate_from_english(text: str, tgt_lang: str) -> str:
    """Translate from English to target language."""
    if tgt_lang in INDICTRANS2_CODES:
        tok = indictrans2_indic["tokenizer"]
        mod = indictrans2_indic["model"]
        tgt_code = INDICTRANS2_CODES[tgt_lang]
        inputs = tok(text, return_tensors="pt", src_lang="eng_Latn")
        with torch.no_grad():
            output = mod.generate(**inputs, forced_bos_token_id=tok.lang_code_to_id[tgt_code])
        return tok.decode(output[0], skip_special_tokens=True)

    elif tgt_lang in OPUS_MT_EN_MODELS:
        key = f"en-{tgt_lang}"
        if key not in opus_models:
            model_name = OPUS_MT_EN_MODELS[tgt_lang]
            opus_models[key] = {
                "tokenizer": AutoTokenizer.from_pretrained(model_name),
                "model": AutoModelForSeq2SeqLM.from_pretrained(model_name),
            }
        tok = opus_models[key]["tokenizer"]
        mod = opus_models[key]["model"]
        inputs = tok([text], return_tensors="pt", padding=True)
        with torch.no_grad():
            output = mod.generate(**inputs)
        return tok.decode(output[0], skip_special_tokens=True)

    return text  # passthrough


# ── API ────────────────────────────────────────────────────────────────────

class TranslateRequest(BaseModel):
    text: str
    src_lang: Optional[str] = None      # auto-detect if not provided
    tgt_lang: str = "en"
    detect_only: bool = False

class TranslateResponse(BaseModel):
    translated: str
    src_lang: str
    tgt_lang: str
    needs_translation: bool
    native_model_sufficient: bool        # True = Qwen3 can handle this directly

@app.post("/translate", response_model=TranslateResponse)
def translate(body: TranslateRequest):
    src_lang = body.src_lang or detect_language(body.text)
    native   = src_lang in QWEN3_NATIVE

    if body.detect_only:
        return TranslateResponse(
            translated=body.text,
            src_lang=src_lang,
            tgt_lang=body.tgt_lang,
            needs_translation=(src_lang != body.tgt_lang),
            native_model_sufficient=native,
        )

    if src_lang == body.tgt_lang:
        return TranslateResponse(
            translated=body.text, src_lang=src_lang,
            tgt_lang=body.tgt_lang, needs_translation=False,
            native_model_sufficient=native,
        )

    # Translate to English first (pivot), then to target if needed
    if src_lang != "en":
        english = translate_to_english(body.text, src_lang)
    else:
        english = body.text

    if body.tgt_lang == "en":
        return TranslateResponse(
            translated=english, src_lang=src_lang,
            tgt_lang="en", needs_translation=True,
            native_model_sufficient=native,
        )

    final = translate_from_english(english, body.tgt_lang)
    return TranslateResponse(
        translated=final, src_lang=src_lang,
        tgt_lang=body.tgt_lang, needs_translation=True,
        native_model_sufficient=native,
    )

@app.get("/languages")
def supported_languages():
    return {
        "native_in_qwen3": sorted(QWEN3_NATIVE),
        "indictrans2": sorted(INDICTRANS2_CODES.keys()),
        "opus_mt": sorted(OPUS_MT_MODELS.keys()),
    }

@app.get("/health")
def health():
    return {"status": "ok", "lid_loaded": lid_model is not None}

import uvicorn
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8200)
```

---

## Translation middleware in LiteLLM

Wire the translator into the LiteLLM request pipeline via custom pre/post hooks:

```python
# translation_middleware.py — mounted on LiteLLM

import httpx
from fastapi import APIRouter
router = APIRouter()

TRANSLATOR_URL = os.environ.get("TRANSLATOR_URL", "http://translator:8200")

async def detect_and_translate_input(messages: list) -> tuple[list, str | None]:
    """
    Detect language of last user message.
    Translate to English if non-English and not natively supported.
    Returns (translated_messages, original_lang_if_translated).
    """
    last_user = next((m for m in reversed(messages) if m["role"] == "user"), None)
    if not last_user:
        return messages, None

    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(
            f"{TRANSLATOR_URL}/translate",
            json={"text": last_user["content"][:500], "detect_only": True},
        )
        detection = r.json()

    src_lang = detection["src_lang"]
    native   = detection["native_model_sufficient"]

    # If language is natively handled by Qwen3 or is already English → no translation
    if src_lang == "en" or native:
        return messages, None

    # Translate to English for non-native languages
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            f"{TRANSLATOR_URL}/translate",
            json={"text": last_user["content"], "src_lang": src_lang, "tgt_lang": "en"},
        )
        result = r.json()

    translated_messages = [
        {**m, "content": result["translated"]}
        if m["role"] == "user" and m["content"] == last_user["content"]
        else m
        for m in messages
    ]
    return translated_messages, src_lang


async def translate_output(text: str, tgt_lang: str) -> str:
    """Translate English response back to original language."""
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            f"{TRANSLATOR_URL}/translate",
            json={"text": text, "src_lang": "en", "tgt_lang": tgt_lang},
        )
        return r.json()["translated"]
```

---

## Language support matrix

| Language | Code | Native in Qwen3 | IndicTrans2 | Opus-MT |
|---|---|---|---|---|
| Hindi | hi | ✅ | ✅ | — |
| Tamil | ta | ✅ | ✅ | — |
| Telugu | te | ✅ | ✅ | — |
| Bengali | bn | ✅ | ✅ | — |
| Marathi | mr | ✅ | ✅ | — |
| Gujarati | gu | ✅ | ✅ | — |
| Kannada | kn | ✅ | ✅ | — |
| Malayalam | ml | ✅ | ✅ | — |
| Punjabi | pa | ✅ | ✅ | — |
| Urdu | ur | ✅ | ✅ | — |
| Odia | or | — | ✅ | — |
| Assamese | as | — | ✅ | — |
| Sanskrit | sa | — | ✅ | — |
| Manipuri | mni | — | ✅ | — |
| Santali | sat | — | ✅ | — |
| Arabic | ar | ✅ | — | ✅ |
| Thai | th | ✅ | — | ✅ |
| Vietnamese | vi | ✅ | — | ✅ |
| Indonesian | id | ✅ | — | ✅ |
| Malay | ms | ✅ | — | ✅ |
| Tagalog/Filipino | tl | — | — | ✅ |
| Sinhala | si | — | — | ✅ |
| Nepali | ne | ✅ | ✅ | — |
| Burmese | my | ✅ | — | — |

**Strategy per language:**
- ✅ Native in Qwen3 → route directly, no translation, best quality
- IndicTrans2 only → translate to English, process, translate back
- Opus-MT → same pivot approach
- Both available → IndicTrans2 preferred for Indian languages (better quality)

---

## RAM allocation for translation stack

| Component | RAM |
|---|---|
| fastText LID model | ~50MB |
| IndicTrans2 distilled 200M (×2, both directions) | ~1.5GB |
| Opus-MT loaded pairs (lazy, 300MB each, up to 8) | ~2.4GB max |
| **Translation sidecar total** | **~4GB** |

Update 96GB RAM allocation:
```
Infrastructure + translation:  ~26GB  (was 22GB)
Always-on 32B models:          ~41GB
Warm 8B slots:                 ~15GB
Headroom:                      ~14GB  (was 18GB)
```
Still comfortable. Translation adds 4GB.

---

## Env vars (add to .env.example)

```
# Translation Sidecar
TRANSLATOR_URL=http://translator:8200
INDICTRANS2_DEVICE=cpu                  # cpu or cuda
OPUS_MT_CACHE=/models/opus
```
