from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class CrawlDataConfigure:
    root_dir: Path
    data_path: Path
    url: str
    ids_url: list
    max_products: int
    max_comments: int
    use_crawl_data: bool
