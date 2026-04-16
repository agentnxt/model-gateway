"""
autonomyx-playwright-scraper
FastAPI sidecar service. Exposes POST /scrape.

Pipeline per URL:
  1. Playwright crawls URL (configurable depth)
  2. Extracts clean text + metadata per page
  3. LiteLLM extracts structured data (via local Qwen3-30B)
  4. nomic-embed-text generates embeddings (via Ollama)
  5. Stores chunks + vectors in SurrealDB
  6. Returns summary + collection name for RAG

Endpoints:
  POST /scrape          - crawl + extract + embed + store
  GET  /status/{job_id} - job status
  POST /query           - query stored collection (RAG search)
  GET  /collections     - list stored collections
  DELETE /collection/{name} - delete a collection
"""

import asyncio
import hashlib
import json
import logging
import os
import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("playwright-scraper")

app = FastAPI(title="Autonomyx Playwright Scraper", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ── Config ─────────────────────────────────────────────────────────────────
GATEWAY_URL    = os.environ.get("GATEWAY_URL",    "http://litellm:4000")
OLLAMA_URL     = os.environ.get("OLLAMA_URL",     "http://ollama:11434")
SURREAL_URL    = os.environ.get("SURREAL_URL",    "http://localhost:8000")
SURREAL_NS     = os.environ.get("SURREAL_NS",     "autonomyx")
SURREAL_DB     = os.environ.get("SURREAL_DB",     "scraper")
SURREAL_USER   = os.environ.get("SURREAL_USER",   "root")
SURREAL_PASS   = os.environ.get("SURREAL_PASS",   "root")
MASTER_KEY     = os.environ.get("LITELLM_MASTER_KEY", "")
EXTRACT_MODEL  = os.environ.get("EXTRACT_MODEL",  "ollama/qwen3:30b-a3b")
EMBED_MODEL    = os.environ.get("EMBED_MODEL",    "nomic-embed-text")
CHUNK_SIZE     = int(os.environ.get("CHUNK_SIZE", "512"))
CHUNK_OVERLAP  = int(os.environ.get("CHUNK_OVERLAP", "64"))
MAX_PAGES      = int(os.environ.get("MAX_PAGES",  "200"))
EMBED_DIM      = 768   # nomic-embed-text output dimension

# ── In-memory job store ────────────────────────────────────────────────────
jobs: dict[str, dict] = {}


# ── Request / Response models ──────────────────────────────────────────────

class ScrapeRequest(BaseModel):
    url: str
    depth: int = 1              # 0=single page, 1=+1 level, -1=full site
    collection: str = ""        # SurrealDB collection name (auto-generated if empty)
    extract_schema: dict = {}   # optional JSON schema for structured extraction
    max_pages: int = 50         # safety limit
    respect_robots: bool = True
    headless: bool = True
    wait_for: str = "domcontentloaded"   # domcontentloaded | networkidle | load
    exclude_patterns: list[str] = []     # URL patterns to skip

class QueryRequest(BaseModel):
    collection: str
    query: str
    top_k: int = 5
    include_metadata: bool = True


# ── Utility ────────────────────────────────────────────────────────────────

def url_to_collection(url: str) -> str:
    """Generate a safe SurrealDB collection name from URL."""
    domain = urlparse(url).netloc.replace(".", "_").replace("-", "_")
    short_hash = hashlib.md5(url.encode()).hexdigest()[:6]
    return f"site_{domain}_{short_hash}"


def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping chunks."""
    words = text.split()
    chunks, i = [], 0
    while i < len(words):
        chunk = " ".join(words[i:i + size])
        if chunk.strip():
            chunks.append(chunk.strip())
        i += size - overlap
    return chunks


def clean_text(html_content: str) -> str:
    """Strip HTML tags and normalise whitespace."""
    text = re.sub(r"<script[^>]*>.*?</script>", " ", html_content, flags=re.DOTALL)
    text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&[a-z]+;", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


# ── Step 1: Playwright crawl ───────────────────────────────────────────────

async def crawl_site(
    url: str,
    depth: int,
    max_pages: int,
    headless: bool,
    wait_for: str,
    exclude_patterns: list[str],
    job_id: str,
) -> list[dict]:
    """
    Crawl URL to specified depth using Playwright.
    Returns list of {url, title, text, html, meta} per page.
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        raise RuntimeError("playwright not installed: pip install playwright && playwright install chromium")

    base_domain = urlparse(url).netloc
    visited, queue, pages = set(), [(url, 0)], []

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=headless,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-extensions",
            ]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (compatible; AutonomyxBot/1.0)",
            viewport={"width": 1280, "height": 720},
            java_script_enabled=True,
        )
        # Block images, fonts, media to speed up crawl
        await context.route(
            "**/*.{png,jpg,jpeg,gif,svg,ico,woff,woff2,ttf,mp4,mp3,pdf}",
            lambda route: route.abort()
        )

        while queue and len(pages) < max_pages:
            current_url, current_depth = queue.pop(0)

            if current_url in visited:
                continue
            if any(pat in current_url for pat in exclude_patterns):
                continue

            visited.add(current_url)
            jobs[job_id]["pages_crawled"] = len(visited)

            try:
                page = await context.new_page()
                await page.goto(current_url, wait_until=wait_for, timeout=15000)

                title     = await page.title()
                html      = await page.content()
                text      = clean_text(html)
                meta_desc = await page.evaluate(
                    "document.querySelector('meta[name=\"description\"]')?.content || ''"
                )

                pages.append({
                    "url":   current_url,
                    "title": title,
                    "text":  text,
                    "html":  html[:5000],   # keep partial HTML for reference
                    "meta":  {"description": meta_desc, "depth": current_depth},
                })

                log.info(f"Crawled [{len(pages)}/{max_pages}]: {current_url}")

                # Discover internal links if depth allows
                if depth == -1 or current_depth < depth:
                    links = await page.evaluate("""
                        () => Array.from(document.querySelectorAll('a[href]'))
                            .map(a => a.href)
                            .filter(h => h.startsWith('http'))
                    """)
                    for link in links:
                        parsed = urlparse(link)
                        # Internal links only, strip fragments
                        clean_link = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                        if (parsed.netloc == base_domain
                                and clean_link not in visited
                                and len(queue) < 500):
                            queue.append((clean_link, current_depth + 1))

                await page.close()

            except Exception as e:
                log.warning(f"Failed to crawl {current_url}: {e}")
                continue

        await browser.close()

    return pages


# ── Step 2: Structured extraction per page ─────────────────────────────────

async def extract_structured(page: dict, schema: dict) -> dict:
    """
    Use LiteLLM (Qwen3-30B) to extract structured data from page text.
    Falls back to basic extraction if LLM fails.
    """
    if not page["text"].strip():
        return {"url": page["url"], "title": page["title"], "raw_text": ""}

    if not schema:
        schema = {
            "title": "page title",
            "main_topic": "main topic in 1 sentence",
            "key_points": ["list of key points"],
            "entities": ["named entities: people, companies, products"],
            "category": "content category",
            "language": "detected language code",
        }

    prompt = f"""Extract structured data from this webpage and return ONLY valid JSON.

URL: {page['url']}
Title: {page['title']}

Text (first 2000 chars):
{page['text'][:2000]}

Return JSON matching this schema:
{json.dumps(schema, indent=2)}

Return ONLY the JSON. No markdown. No explanation."""

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                f"{GATEWAY_URL}/v1/chat/completions",
                headers={"Authorization": f"Bearer {MASTER_KEY}"},
                json={
                    "model": EXTRACT_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                    "max_tokens": 1024,
                    "response_format": {"type": "json_object"},
                },
            )
            r.raise_for_status()
            content = r.json()["choices"][0]["message"]["content"]
            structured = json.loads(content)
            structured["url"]   = page["url"]
            structured["title"] = page["title"]
            return structured
    except Exception as e:
        log.warning(f"Structured extraction failed for {page['url']}: {e}")
        return {
            "url":        page["url"],
            "title":      page["title"],
            "raw_text":   page["text"][:500],
            "error":      str(e),
        }


# ── Step 3: Generate embeddings ────────────────────────────────────────────

async def embed_chunks(chunks: list[str]) -> list[list[float]]:
    """Generate embeddings for text chunks using nomic-embed-text via Ollama."""
    if not chunks:
        return []
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(
                f"{OLLAMA_URL}/api/embed",
                json={"model": EMBED_MODEL, "input": chunks},
            )
            r.raise_for_status()
            return r.json()["embeddings"]
    except Exception as e:
        log.error(f"Embedding failed: {e}")
        return [[] for _ in chunks]


# ── Step 4: Store in SurrealDB ─────────────────────────────────────────────

async def surreal_query(sql: str, params: dict = None) -> Any:
    """Execute SurrealDB SQL query."""
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            f"{SURREAL_URL}/sql",
            headers={
                "Authorization": f"Basic {__import__('base64').b64encode(f'{SURREAL_USER}:{SURREAL_PASS}'.encode()).decode()}",
                "NS": SURREAL_NS,
                "DB": SURREAL_DB,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            content=sql,
        )
        r.raise_for_status()
        return r.json()


async def setup_collection(collection: str):
    """Create SurrealDB table + MTREE vector index if not exists."""
    await surreal_query(f"""
        DEFINE TABLE IF NOT EXISTS {collection} SCHEMAFULL;
        DEFINE FIELD IF NOT EXISTS url        ON {collection} TYPE string;
        DEFINE FIELD IF NOT EXISTS title      ON {collection} TYPE string;
        DEFINE FIELD IF NOT EXISTS chunk_text ON {collection} TYPE string;
        DEFINE FIELD IF NOT EXISTS chunk_idx  ON {collection} TYPE int;
        DEFINE FIELD IF NOT EXISTS embedding  ON {collection} TYPE array;
        DEFINE FIELD IF NOT EXISTS structured ON {collection} TYPE object;
        DEFINE FIELD IF NOT EXISTS crawled_at ON {collection} TYPE datetime;
        DEFINE INDEX IF NOT EXISTS {collection}_vector
            ON {collection} FIELDS embedding
            MTREE DIMENSION {EMBED_DIM} TYPE F32 DIST COSINE;
    """)


async def store_page(collection: str, page: dict, chunks: list[str],
                     embeddings: list[list[float]], structured: dict):
    """Store all chunks from a page into SurrealDB."""
    if not chunks:
        return

    for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
        if not emb:
            continue
        record_id = f"{collection}:{hashlib.md5(f'{page['url']}{i}'.encode()).hexdigest()[:12]}"
        await surreal_query(f"""
            UPSERT {record_id} SET
                url        = '{page['url'].replace("'", "\\'")}',
                title      = '{page['title'].replace("'", "\\'")}',
                chunk_text = '{chunk.replace("'", "\\'")[:1000]}',
                chunk_idx  = {i},
                embedding  = {json.dumps(emb)},
                structured = {json.dumps(structured)},
                crawled_at = time::now();
        """)


# ── Step 5: RAG query ──────────────────────────────────────────────────────

async def rag_search(collection: str, query: str, top_k: int) -> list[dict]:
    """Vector search against a collection."""
    query_emb = await embed_chunks([query])
    if not query_emb or not query_emb[0]:
        return []

    result = await surreal_query(f"""
        SELECT url, title, chunk_text, structured,
               vector::similarity::cosine(embedding, {json.dumps(query_emb[0])}) AS score
        FROM {collection}
        ORDER BY score DESC
        LIMIT {top_k};
    """)

    if isinstance(result, list) and result:
        return result[0].get("result", [])
    return []


# ── Main pipeline ──────────────────────────────────────────────────────────

async def run_pipeline(job_id: str, req: ScrapeRequest):
    """Full pipeline: crawl → extract → embed → store."""
    jobs[job_id].update({"status": "crawling", "started_at": time.time()})

    try:
        collection = req.collection or url_to_collection(req.url)
        jobs[job_id]["collection"] = collection

        # Step 1: Crawl
        log.info(f"[{job_id}] Crawling {req.url} depth={req.depth}")
        pages = await crawl_site(
            req.url, req.depth, min(req.max_pages, MAX_PAGES),
            req.headless, req.wait_for, req.exclude_patterns, job_id
        )
        jobs[job_id].update({"status": "extracting", "total_pages": len(pages)})
        log.info(f"[{job_id}] Crawled {len(pages)} pages")

        # Setup SurrealDB collection
        await setup_collection(collection)

        total_chunks = 0
        for i, page in enumerate(pages):
            jobs[job_id]["current_page"] = i + 1

            # Step 2: Structured extraction
            structured = await extract_structured(page, req.extract_schema)

            # Step 3: Chunk + embed
            chunks = chunk_text(page["text"])
            if not chunks:
                continue

            jobs[job_id]["status"] = "embedding"
            embeddings = await embed_chunks(chunks)

            # Step 4: Store
            jobs[job_id]["status"] = "storing"
            await store_page(collection, page, chunks, embeddings, structured)
            total_chunks += len(chunks)

        elapsed = round(time.time() - jobs[job_id]["started_at"], 1)
        jobs[job_id].update({
            "status":       "complete",
            "total_chunks": total_chunks,
            "collection":   collection,
            "elapsed_sec":  elapsed,
            "rag_ready":    True,
        })
        log.info(f"[{job_id}] Complete. {len(pages)} pages, {total_chunks} chunks, {elapsed}s")

    except Exception as e:
        log.error(f"[{job_id}] Pipeline failed: {e}")
        jobs[job_id].update({"status": "failed", "error": str(e)})


# ── API endpoints ──────────────────────────────────────────────────────────

@app.post("/scrape")
async def scrape(req: ScrapeRequest, background_tasks: BackgroundTasks):
    """Start a scrape job. Returns job_id immediately. Poll /status/{job_id}."""
    job_id = str(uuid.uuid4())[:8]
    collection = req.collection or url_to_collection(req.url)
    jobs[job_id] = {
        "job_id":        job_id,
        "url":           req.url,
        "depth":         req.depth,
        "collection":    collection,
        "status":        "queued",
        "pages_crawled": 0,
        "total_pages":   0,
        "current_page":  0,
        "total_chunks":  0,
        "rag_ready":     False,
    }
    background_tasks.add_task(run_pipeline, job_id, req)
    return {"job_id": job_id, "collection": collection, "status": "queued"}


@app.get("/status/{job_id}")
async def status(job_id: str):
    """Get job status and progress."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return jobs[job_id]


@app.post("/query")
async def query(req: QueryRequest):
    """RAG search against a stored collection."""
    results = await rag_search(req.collection, req.query, req.top_k)
    return {
        "collection": req.collection,
        "query":      req.query,
        "results":    results,
        "count":      len(results),
    }


@app.get("/collections")
async def list_collections():
    """List all stored site collections."""
    result = await surreal_query("INFO FOR DB;")
    if isinstance(result, list) and result:
        tables = list(result[0].get("result", {}).get("tables", {}).keys())
        site_tables = [t for t in tables if t.startswith("site_")]
        return {"collections": site_tables, "count": len(site_tables)}
    return {"collections": [], "count": 0}


@app.delete("/collection/{name}")
async def delete_collection(name: str):
    """Delete a site collection and all its data."""
    await surreal_query(f"REMOVE TABLE {name};")
    return {"deleted": name}


@app.get("/health")
async def health():
    return {"status": "ok", "embed_model": EMBED_MODEL, "extract_model": EXTRACT_MODEL}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8400)
