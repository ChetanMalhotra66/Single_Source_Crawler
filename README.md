# DarkTrace Crawling Engine — single-source prototype

This is the first slice of the Crawling Engine described in the design doc:
one authorized seed URL in, one crawl-result record out. No scheduler, task
queue, or link-following yet — those layer on top of this without changing
what's here.

## Setup

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

You need PySocks installed for Scrapy to support `socks5h://` proxy URLs —
it's in requirements.txt.

### Tor

Run a Tor daemon (or point at a controlled Tor gateway) exposing a SOCKS5
proxy, default `127.0.0.1:9050`. Quick local option:

```bash
sudo apt install tor
sudo systemctl start tor
```

### I2P

Run an I2P router; its HTTP proxy defaults to `127.0.0.1:4444`.

Both endpoints are configurable in `darktrace_crawler/settings.py`
(`TOR_SOCKS_PROXY`, `I2P_HTTP_PROXY`) — point them at whatever controlled
gateway your environment uses instead of a local daemon.

## Running it

```bash
# normal site
scrapy crawl single_source -a url="https://example.com" -a source_type="normal"

# onion site (routed through Tor automatically — no extra flag needed)
scrapy crawl single_source -a url="http://<address>.onion/" -a source_type="onion_site"

# i2p site
scrapy crawl single_source -a url="http://<address>.i2p/" -a source_type="blog_news"
```

`-a source_name=` is optional (defaults to `source_1`) — it's just the label
that ends up in the metadata record.

## How routing works

`ProxyRoutingMiddleware` (middlewares.py) looks at the hostname of each
request: `.onion` → Tor SOCKS5 proxy, `.i2p` → I2P HTTP proxy, anything else
→ direct connection. Same spider, same code path, for all three.

## What you get out

- `crawl_output/raw/<sha256>.html` — the untouched original page content,
  preserved before any later processing (evidence).
- `crawl_output/crawl_results.jsonl` — one JSON record per fetch: source,
  URL, network used, fetch timestamp, crawler build, HTTP status,
  attempt count, content hash, and whether the hash was already seen
  (cheap duplicate flag).

## Reliability behavior already wired in

- `DOWNLOAD_TIMEOUT = 60` — generous, since Tor/I2P circuit setup is slow.
- Retryable failures (5xx, 408, 429, and connection errors) get retried with
  **exponential backoff, capped at 3 attempts** (`BackoffRetryMiddleware`),
  matching the design doc.
- Requests that exhaust retries are logged as `DEAD-LETTER` and counted in
  `darktrace/dead_letter_count` in Scrapy's stats — the queue/operator-review
  step from the doc isn't built yet, but the hook point is there.
- `AUTOTHROTTLE` + per-domain concurrency limit (`1`) keep this polite to a
  single source by default.

## Not built yet (next layers, per the doc)

- Scheduler / multi-source task queue (Celery + Redis, per the doc).
- Link-following within scope/depth limits.
- Incremental crawling (ETag/Last-Modified, forum thread cursors).
- Dead-letter *queue* (currently just logged + counted, not requeued).
