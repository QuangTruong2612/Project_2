from .expense_tool import add_expense_tool, delete_expense_tool, get_expense_tool, update_expense_tool
from .weather_tool import get_weather_current_tool, get_weather_forecast_tool
from .news_tool import get_news_url


TOOLS_MAPPING = {
    # tool expense
    'add_expense_tool': add_expense_tool,
    'delete_expense_tool': delete_expense_tool,
    'get_expense_tool': get_expense_tool,
    'update_expense_tool': update_expense_tool,
    
    # tools weather
    'get_weather_current_tool': get_weather_current_tool,
    'get_weather_forecast_tool': get_weather_forecast_tool,

    # tools news
    'get_news_url': get_news_url

}

AGENT_TOOLS_LIST = {
    "agent_main": [],
    "agent_expense": [
        {
            "name": "add_expense_tool",
            "description": "GHI NHẬN một khoản chi tiêu mới. Hỗ trợ cả ngày và giờ. Ví dụ: 'Ghi lại 50k ăn trưa lúc 12h'.",
            "args": "user_id: str, amount: float, category: str, description: str, expense_date: str"
        },
        {
            "name": "get_expense_tool",
            "description": "TRUY VẤN danh sách chi tiêu theo KHOẢNG THỜI GIAN hoặc HẠNG MỤC. Dùng cho các câu hỏi: 'Tháng này tiêu gì?', 'Chi tiêu từ đầu tuần', 'Hôm qua hết bao nhiêu?'. LƯU Ý: Phải lấy 'id' từ đây trước khi Cập nhật hoặc Xóa.",
            "args": "user_id: str, category: Optional[str], start_date: Optional[str], end_date: Optional[str]"
        },
        {
            "name": "update_expense_tool",
            "description": "SỬA ĐỔI thông tin một khoản chi (bao gồm cả cập nhật thời gian). PHẢI tìm ID bằng get_expense_tool trước.",
            "args": "user_id: str, id: int, amount: Optional[float], category: Optional[str], description: Optional[str], expense_date: Optional[str]"
        },
        {
            "name": "delete_expense_tool",
            "description": "XÓA khoản chi tiêu dựa trên ID.",
            "args": "user_id: str, id: int"
        }
    ],
    "agent_news": [
        {
            "name": "get_news_url",
            "description": "Lấy tin tức theo url mà người dùng gửi để phục vụ cho việc tóm tắt tin tức",
            "args": "url_news: str"
        }
    ],
    "agent_weather": [
        {
            "name": "get_weather_current_tool",
            "description": "Lấy thông tin thời tiết HIỆN TẠI (ngay bây giờ). PHẢI dịch tên địa điểm sang tiếng Anh trước khi gọi.",
            "args": "location: str"
        },
        {
            "name": "get_weather_forecast_tool",
            "description": "Dự báo thời tiết cho một THỜI ĐIỂM CỤ THỂ hoặc trong tương lai (ví dụ: ngày mai, chiều nay). PHẢI dịch tên địa điểm sang tiếng Anh trước khi gọi.",
            "args": "location: str, time: str"
        }
    ]
}

