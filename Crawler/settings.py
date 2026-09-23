"""
Settings for the DarkTrace single-source Crawling Engine.

Only what's needed for "act like a normal crawler and retrieve content from
the specified webpage(s)" right now: single seed, no link-following, but the
request handling / reliability / metadata pieces from the design doc are
wired in so later stages (scheduler, queue, link-following) can be layered
on top without reworking this part.
"""

BOT_NAME = "Crawler"

SPIDER_MODULES = ["Crawler.spiders"]
NEWSPIDER_MODULE = "Crawler.spiders"

# Identifies the crawler/build in every crawl result record (audit trail).
CRAWLER_BUILD = "darktrace-crawler/0.1.0"

USER_AGENT = "darktrace-crawler/0.1 (+authorized-research-collection)"

# --- Scope / authorization -------------------------------------------------
# The design doc is explicit: only authorized sources, read-only collection.
# ROBOTSTXT_OBEY is off because collection targets (esp. onion sources) are
# pre-authorized out-of-band, not discovered/crawled opportunistically.
ROBOTSTXT_OBEY = False

# --- Concurrency / rate limiting --------------------------------------------
# "Per-source and global rate limits control how quickly requests are made."
CONCURRENT_REQUESTS = 4
CONCURRENT_REQUESTS_PER_DOMAIN = 2
DOWNLOAD_DELAY = 1.0            # baseline delay; randomized below
RANDOMIZE_DOWNLOAD_DELAY = True

AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 1.0
AUTOTHROTTLE_MAX_DELAY = 30.0
AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0

# --- Timeouts / retries ------------------------------------------------------
# "Timeouts prevent a slow source from holding a worker indefinitely."
# Onion/I2P circuits are slow to establish, so timeout is generous.
DOWNLOAD_TIMEOUT = 60

# "Retryable failures can be retried with exponential backoff, max 3 attempts."
RETRY_ENABLED = True
RETRY_TIMES = 3
RETRY_HTTP_CODES = [500, 502, 503, 504, 522, 524, 408, 429]

# --- Proxy routing (Tor / I2P) ----------------------------------------------
# Tor: local SOCKS5 proxy from a Tor daemon/gateway (default port 9050),
# or a controlled Tor gateway container in the deployment environment.
TOR_SOCKS_PROXY = "socks5h://127.0.0.1:9050"

# I2P: local HTTP proxy exposed by the I2P router console (default port 4444).
I2P_HTTP_PROXY = "http://127.0.0.1:4444"

# --- Middlewares --------------------------------------------------------------
DOWNLOADER_MIDDLEWARES = {
    "Crawler.middlewares.ProxyRoutingMiddleware": 350,
    "Crawler.middlewares.BackoffRetryMiddleware": 550,
    "scrapy.downloadermiddlewares.retry.RetryMiddleware": None,  # replaced above
}

ITEM_PIPELINES = {
    "Crawler.pipelines.ContentHashPipeline": 100,
    "Crawler.pipelines.RawEvidenceStoragePipeline": 200,
    "Crawler.pipelines.CrawlResultLogPipeline": 300,
}

# Where raw evidence (original content, preserved before processing) is written.
RAW_STORAGE_DIR = "crawl_output/raw"
# Where the crawl-result metadata log (JSON Lines) is written.
RESULT_LOG_PATH = "crawl_output/crawl_results.jsonl"

LOG_LEVEL = "INFO"

REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
FEED_EXPORT_ENCODING = "utf-8"