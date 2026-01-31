from Project_2 import logger
from Project_2.pipeline.stage_0_crawl_data import CrawlDataPipeline


STAGE_NAME = "Crawl data"
try:
    logger.info(f">>>>>> Stage {STAGE_NAME} started <<<<<<")
    obj = CrawlDataPipeline()
    obj.main()
    logger.info(f">>>>>> Stage {STAGE_NAME} completed <<<<<<\n\nx==========x")
except Exception as e:
    logger.exception(e)
    raise e

