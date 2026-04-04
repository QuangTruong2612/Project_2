import logging

# Thiết lập log cho toàn bộ dự án mỗi khi src được gọi
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PersonalAgent")

logger.info("Hệ thống Agent đang được khởi tạo...")