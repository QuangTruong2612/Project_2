import os
from Project_2.constants import *
from Project_2.entity.config_entity import CrawlDataConfigure
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

