FROM python:3.12-slim

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install CPU-only torch first (smaller wheel, no CUDA baggage)
RUN pip install --no-cache-dir \
    torch==2.3.0+cpu \
    --index-url https://download.pytorch.org/whl/cpu

# Install remaining deps
RUN pip install --no-cache-dir \
    fastapi==0.111.0 \
    uvicorn==0.30.0 \
    transformers==4.41.0 \
    sentencepiece==0.2.0 \
    sacremoses==0.1.1 \
    fasttext-wheel==0.9.2 \
    httpx==0.27.0

# IndicTrans2 toolkit
RUN pip install --no-cache-dir \
    git+https://github.com/VarunGumma/IndicTransToolkit.git

COPY translator_server.py .

# Pre-download fastText LID model (917KB) — tiny, safe to bake in
RUN python3 -c "import urllib.request, os; os.makedirs('/models', exist_ok=True); urllib.request.urlretrieve('https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.ftz', '/models/lid.176.ftz'); print('fastText LID model downloaded')"

RUN useradd -m translator && chown -R translator /app /models
USER translator

EXPOSE 8200
CMD ["uvicorn", "translator_server:app", "--host", "0.0.0.0", "--port", "8200"]
