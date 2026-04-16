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
