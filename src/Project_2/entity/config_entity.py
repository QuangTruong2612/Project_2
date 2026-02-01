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
@dataclass(frozen=True)
class ProcessedDataConfigure:
    root_dir: Path
    train_path: Path
    test_path: Path
    data_path: Path
    test_size: int
    random_state: int
    target: str
    cols_not_use: list
    ngram: tuple
    max_features: int
    min_df: int
