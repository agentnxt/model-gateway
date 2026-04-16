FROM python:3.12-slim

WORKDIR /app

# System deps for tokenizers (Rust-based)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    fastapi==0.111.0 \
    uvicorn==0.30.0 \
    transformers==4.41.0 \
    torch==2.3.0 --index-url https://download.pytorch.org/whl/cpu \
    sentencepiece==0.2.0 \
    sacremoses==0.1.1 \
    fasttext-wheel==0.9.2 \
    httpx==0.27.0

# IndicTrans2 toolkit
RUN pip install --no-cache-dir \
    git+https://github.com/VarunGumma/IndicTransToolkit.git

COPY translator_server.py .

# Pre-download fastText LID model (917KB) at build time
RUN python3 -c "
import urllib.request, os
os.makedirs('/models', exist_ok=True)
urllib.request.urlretrieve(
    'https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.ftz',
    '/models/lid.176.ftz'
)
print('fastText LID downloaded')
"

RUN useradd -m translator && chown -R translator /models
USER translator

EXPOSE 8200
CMD ["uvicorn", "translator_server:app", "--host", "0.0.0.0", "--port", "8200"]
