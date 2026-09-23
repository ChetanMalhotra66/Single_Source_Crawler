"""
Pipelines, in run order:

1. ContentHashPipeline       - computes sha256 of raw content (exact-duplicate
                                detection, evidence integrity).
2. RawEvidenceStoragePipeline - writes the untouched original content to disk
                                first ("Original content is preserved before
                                later processing").
3. CrawlResultLogPipeline    - appends the metadata record (source, URI,
                                fetch time, crawler build, hash, status) as a
                                JSON Lines audit log, for handoff to the next
                                DarkTrace stage.
"""
import hashlib
import json
import os
from datetime import datetime, timezone


class ContentHashPipeline:
    def process_item(self, item, spider):
        raw_html = item.get("raw_html", "") or ""
        item["content_hash"] = hashlib.sha256(raw_html.encode("utf-8", "ignore")).hexdigest()
        return item


class RawEvidenceStoragePipeline:
    def __init__(self, raw_dir):
        self.raw_dir = raw_dir

    @classmethod
    def from_crawler(cls, crawler):
        return cls(raw_dir=crawler.settings.get("RAW_STORAGE_DIR", "crawl_output/raw"))

    def open_spider(self, spider):
        os.makedirs(self.raw_dir, exist_ok=True)

    def process_item(self, item, spider):
        file_name = f"{item['content_hash']}.html"
        file_path = os.path.join(self.raw_dir, file_name)
        # Duplicate content -> file already exists, skip rewrite (cheap dedup).
        if not os.path.exists(file_path):
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(item.get("raw_html", "") or "")
        item["evidence_path"] = file_path
        return item


class CrawlResultLogPipeline:
    def __init__(self, log_path):
        self.log_path = log_path
        self._file = None
        self._seen_hashes = set()

    @classmethod
    def from_crawler(cls, crawler):
        return cls(log_path=crawler.settings.get("RESULT_LOG_PATH", "crawl_output/crawl_results.jsonl"))

    def open_spider(self, spider):
        os.makedirs(os.path.dirname(self.log_path) or ".", exist_ok=True)
        self._file = open(self.log_path, "a", encoding="utf-8")

    def close_spider(self, spider):
        if self._file:
            self._file.close()

    def process_item(self, item, spider):
        is_dup = item["content_hash"] in self._seen_hashes
        self._seen_hashes.add(item["content_hash"])

        record = {
            "source_name": item.get("source_name"),
            "source_type": item.get("source_type"),
            "url": item.get("url"),
            "network": item.get("network"),
            "fetch_timestamp": item.get("fetch_timestamp") or datetime.now(timezone.utc).isoformat(),
            "crawler_build": item.get("crawler_build"),
            "status": item.get("status", "success"),
            "http_status": item.get("http_status"),
            "attempt": item.get("attempt"),
            "title": item.get("title"),
            "content_hash": item.get("content_hash"),
            "duplicate_of_existing": is_dup,
            "evidence_path": item.get("evidence_path"),
        }
        self._file.write(json.dumps(record, ensure_ascii=False) + "\n")
        self._file.flush()
        return item
