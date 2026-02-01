import os
from Project_2.constants import *
from Project_2.entity.config_entity import CrawlDataConfigure, ProcessedDataConfigure
from Project_2.utils.common import read_yaml, create_directories
from pathlib import Path

class ConfigureManager:
    def __init__(self,
                config_filepath: Path = CONFIG_FILE_PATH,
                params_filepath: Path = PARAMS_FILE_PATH):
        self.config = read_yaml(config_filepath)
        self.params = read_yaml(params_filepath)
        create_directories([self.config.artifacts_root])

    def get_crawl_data_config(self) -> CrawlDataConfigure:
        crawldata = self.config.crawl_data
        params = self.params
        create_directories([crawldata.root_dir])

        crawl_data_config = CrawlDataConfigure(
            root_dir = Path(crawldata.root_dir),
            data_path = Path(crawldata.data_path),
            url = params.PARAMS_CRAWL_DATA.URL,
            ids_url = params.PARAMS_CRAWL_DATA.URL_IDS,
            max_comments= params.PARAMS_CRAWL_DATA.MAX_COMMENTS,
            max_products= params.PARAMS_CRAWL_DATA.MAX_PRODCUTS,
            use_crawl_data= params.USE_CRAWL_DATA
        )
        return crawl_data_config

    def get_processed_data_config(self) -> ProcessedDataConfigure:
        processed = self.config.data_process
        params = self.params
        create_directories([processed.root_dir])

        processed_data_config = ProcessedDataConfigure(
            root_dir = Path(processed.root_dir),
            train_path = Path(processed.train_path),
            test_path = Path(processed.test_path),
            data_path = Path(processed.data_path),
            test_size = params.TEST_SIZE,
            random_state= params.RANDOM_STATE,
            target= params.TARGET,
            cols_not_use = params.COLS_NOT_USE,
            ngram = tuple(params.NGRAM),
            max_features = params.MAX_FEATURES,
            min_df = params.MIN_DF,
        )
        return processed_data_config


