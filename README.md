# DarkTrace Crawling Engine — single-source prototype

This is the first slice of the Crawling Engine:
one authorized seed URL in, one crawl-result record out. No scheduler, task
queue, or link-following yet — those layer on top of this without changing
what's here.

## Setup

### 1. Create & Activate Virtual Environment

On Windows (PowerShell):
python -m venv venv
.\venv\Scripts\Activate.ps1
*(If PowerShell blocks script execution, run "Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process" first)*

On macOS / Linux:
python3 -m venv venv
source venv/bin/activate

### 2. Install Dependencies

pip install -r requirements.txt

You need PySocks installed for Scrapy to support socks5h:// proxy URLs — it is included in requirements.txt.

---

## Proxy Services Setup

### Tor Setup
Run a Tor daemon (or point at a controlled Tor gateway) exposing a SOCKS5 proxy.

* Windows (Tor Browser method): Open Tor Browser in the background. It exposes a SOCKS5 proxy on 127.0.0.1:9150. Update TOR_SOCKS_PROXY in Crawler/settings.py to match 9150.
* Windows (Standalone Daemon): Install via Chocolatey (choco install tor) or Scoop (scoop install tor) and run "tor" in PowerShell (default port 9050).
* Linux (Ubuntu/Debian):
  sudo apt install tor
  sudo systemctl start tor

### I2P Setup
Run an I2P router; its HTTP proxy defaults to 127.0.0.1:4444.

Both endpoints are configurable in Crawler/settings.py (TOR_SOCKS_PROXY, I2P_HTTP_PROXY) — point them at whatever controlled gateway your environment uses instead of a local daemon.

---

## Running the Crawler

Ensure your virtual environment is active and terminal is inside the Single_Source_Crawler folder, then run:

# normal site
scrapy crawl single_source -a url="https://example.com" -a source_type="normal"

# onion site (routed through Tor automatically — no extra flag needed)
scrapy crawl single_source -a url="http://<address>.onion/" -a source_type="onion_site"

# i2p site
scrapy crawl single_source -a url="http://<address>.i2p/" -a source_type="blog_news"

-a source_name= is optional (defaults to source_1) — it's just the label that ends up in the metadata record.

---

## How routing works

ProxyRoutingMiddleware (Crawler/middlewares.py) looks at the hostname of each request:
* .onion -> Tor SOCKS5 proxy
* .i2p -> I2P HTTP proxy
* Anything else -> Direct connection

Same spider, same code path, for all three.

---

## What you get out

- crawl_output/raw/<sha256>.html — the untouched original page content, preserved before any later processing (evidence).
- crawl_output/crawl_results.jsonl — one JSON record per fetch: source, URL, network used, fetch timestamp, crawler build, HTTP status, attempt count, content hash, and whether the hash was already seen (cheap duplicate flag).

---

## Reliability behavior already wired in

- DOWNLOAD_TIMEOUT = 60 — generous, since Tor/I2P circuit setup is slow.
- Retryable failures (5xx, 408, 429, and connection errors) get retried with exponential backoff, capped at 3 attempts (BackoffRetryMiddleware), matching the design doc.
- Requests that exhaust retries are logged as DEAD-LETTER and counted in darktrace/dead_letter_count in Scrapy's stats — the queue/operator-review step from the doc isn't built yet, but the hook point is there.
- AUTOTHROTTLE + per-domain concurrency limit (1) keep this polite to a single source by default.

---

## Not built yet (next layers)

- Scheduler / multi-source task queue (Celery + Redis, per the doc).
- Link-following within scope/depth limits.
- Incremental crawling (ETag/Last-Modified, forum thread cursors).
- Dead-letter queue (currently just logged + counted, not requeued).