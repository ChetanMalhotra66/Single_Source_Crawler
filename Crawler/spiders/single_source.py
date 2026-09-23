"""
Single-source spider.

Scope, deliberately: start from one authorized seed URL, fetch it through the
right gateway (direct / Tor / I2P, handled by ProxyRoutingMiddleware), parse
it, and produce one crawl-result record. No link-following, no scheduling,
no multi-source queueing yet — that's the next layer on top of this.

Usage:
    scrapy crawl single_source \
        -a url="http://example.onion/page" \
        -a source_name="source_1" \
        -a source_type="onion_site"
"""
from datetime import datetime, timezone

import scrapy

from Crawler.items import CrawlResultItem


class SingleSourceSpider(scrapy.Spider):
    name = "single_source"

    custom_settings = {
        # Per-source limit: this spider only ever touches one host, so keep
        # it polite regardless of the global CONCURRENT_REQUESTS setting.
        "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
    }

    def __init__(self, url=None, source_name="source_1", source_type="normal", *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not url:
            raise ValueError("Provide the authorized seed URL: -a url=<...>")
        self.start_urls = [url]
        self.source_name = source_name
        self.source_type = source_type

    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(
                url,
                callback=self.parse,
                errback=self.handle_failure,
                meta={"attempt": 1},
                dont_filter=True,
            )

    def parse(self, response):
        title = response.xpath("//title/text()").get(default="").strip()
        text_content = " ".join(
            t.strip() for t in response.xpath("//body//text()").getall() if t.strip()
        )

        item = CrawlResultItem()
        item["source_name"] = self.source_name
        item["source_type"] = self.source_type
        item["url"] = response.url
        item["network"] = response.meta.get("network", "clearnet")
        item["fetch_timestamp"] = datetime.now(timezone.utc).isoformat()
        item["crawler_build"] = self.settings.get("CRAWLER_BUILD")
        item["status"] = "success"
        item["http_status"] = response.status
        item["attempt"] = response.meta.get("retry_times", 0) + 1
        item["title"] = title
        item["raw_html"] = response.text
        item["text_content"] = text_content

        yield item

    def handle_failure(self, failure):
        request = failure.request
        self.logger.error("Fetch failed permanently for %s: %s", request.url, failure.value)

        item = CrawlResultItem()
        item["source_name"] = self.source_name
        item["source_type"] = self.source_type
        item["url"] = request.url
        item["network"] = request.meta.get("network", "clearnet")
        item["fetch_timestamp"] = datetime.now(timezone.utc).isoformat()
        item["crawler_build"] = self.settings.get("CRAWLER_BUILD")
        item["status"] = "failed"
        item["http_status"] = getattr(failure.value, "response", None) and failure.value.response.status
        item["attempt"] = request.meta.get("retry_times", 0) + 1
        item["title"] = ""
        item["raw_html"] = ""
        item["text_content"] = ""

        yield item