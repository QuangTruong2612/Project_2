from Project_2.components.crawldata import CrawlData
from Project_2.configs.configurations import ConfigureManager
from Project_2 import logger

STAGE_NAME = "Crawl data"

class CrawlDataPipeline:
    def __init__(self):
        pass

    def main(self):
        config = ConfigureManager()
        crawl_data_config = config.get_crawl_data_config()
        crawldata = CrawlData(config=crawl_data_config)
        crawldata.crawldata()

