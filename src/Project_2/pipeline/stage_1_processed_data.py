from Project_2.components.processed_data import ProcessedData
from Project_2.configs.configurations import ConfigureManager
from Project_2 import logger
from Project_2.entity.config_entity import ProcessedDataConfigure

STAGE_NAME = "Process data"
class ProcessedDataPipeline:
    def __init__(self):
        pass

    def main(self):
        config_manager = ConfigureManager()
        processed_data_config = config_manager.get_processed_data_config()

        processed_data = ProcessedData(config=processed_data_config)
        data = processed_data.load_data()
        processed_data.process_data(data)