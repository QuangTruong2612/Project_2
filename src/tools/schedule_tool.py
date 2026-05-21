from langchain_core.tools import tool
from src.core import supabase
from pydantic import BaseModel, Field
from typing import Optional, Union, List    
import re
import dateparser
from datetime import datetime, time, timedelta, timezone as tz

# =========================================
# SCHEMAS INPUT
# =========================================

class AddScheduleInput(BaseModel):
    user_id: Optional[str] = Field(None, description="ID của người dùng (tự động lấy từ system, không cần điền)")
    schedule_date: str = Field(description="Ngày diễn ra hoạt động (ví dụ: '2024-12-25 ')")
    start_time: str = Field(description="Giờ diễn ra hoạt động (ví dụ: '18:00', '6pm')")
    end_time: str = Field(description="Giờ kết thúc hoạt động (ví dụ: '19:00', '7pm')")
    activity: str = Field(description="Nội dung của hoạt động (ví dụ: 'Họp với khách hàng', 'Đi uống cà phê')")
    location_address: str = Field(description="Địa chỉ diễn ra hoạt động (ví dụ: '123 Đường ABC, Quận 1, TP.HCM')")

class GetScheduleInput(BaseModel):
    user_id: Optional[str] = Field(None, description="ID của người dùng (tự động lấy từ system, không cần điền)")
    schedule_date: str = Field(description="Ngày diễn ra hoạt động (ví dụ: '2024-12-25 ')")
    start_time: str = Field(description="Giờ diễn ra hoạt động (ví dụ: '18:00', '6pm')")
    end_time: str = Field(description="Giờ kết thúc hoạt động (ví dụ: '19:00', '7pm')")
    activity: str = Field(description="Nội dung của hoạt động (ví dụ: 'Họp với khách hàng', 'Đi uống cà phê')")
    location_address: str = Field(description="Địa chỉ diễn ra hoạt động (ví dụ: '123 Đường ABC, Quận 1, TP.HCM')")



# =========================================
# FUNCTION HELPERS
# =========================================    

def _normalize_date(dt_str: str) -> str:
    dt_str = dt_str.replace("hôm này", "hôm nay").replace("bửa nay", "hôm nay").replace("bữa nay", "hôm nay")
    
    # Chuẩn hoá buổi
    dt_str = dt_str.replace("trưa", "").replace("sáng", "").replace("tối", "")

    return dt_str


def _parse_datetime(
    dt_str: str,
    prefer_end_of_day: bool = False,
    prefer_start_of_day: bool = False
) -> Optional[str]:
    """Chuẩn hóa ngày tháng về ISO 8601 có timezone UTC.
    - prefer_start_of_day=True: force về 00:00:00 (dùng cho giới hạn dưới)
    - prefer_end_of_day=True:   force về 23:59:59 (dùng cho giới hạn trên)
    """
    if not dt_str:
        return None

    # Chuẩn hoá biểu thức giờ tiếng Việt trước khi đưa vào dateparser
    normalized = _normalize_date(dt_str)

    _DATEPARSER_SETTINGS = {
        'PREFER_DATES_FROM': 'current_period',
        'RETURN_AS_TIMEZONE_AWARE': False,
        'TIMEZONE': 'Asia/Ho_Chi_Minh',
    }

    parsed = dateparser.parse(normalized, languages=['vi', 'en'], settings=_DATEPARSER_SETTINGS)

    if not parsed and normalized != dt_str:
        parsed = dateparser.parse(dt_str, languages=['vi', 'en'], settings=_DATEPARSER_SETTINGS)

    if not parsed:
        return None

    if prefer_start_of_day:
        parsed = datetime.combine(parsed.date(), time(0, 0, 0))
    elif prefer_end_of_day:
        parsed = datetime.combine(parsed.date(), time(23, 59, 59))

    return parsed.isoformat()


def _format_display_time(iso_str: str) -> str:
    """Định dạng chuỗi thời gian hiển thị (mặc định đang lưu là giờ VN)."""
    if not iso_str:
        return ""
    try:
        # Nếu chuỗi có Z hoặc +00:00 do db tự thêm, xoá đi để parse thành naive
        clean_str = iso_str.replace("Z", "").split("+")[0]
        dt = datetime.fromisoformat(clean_str)
        return dt.strftime("%d/%m/%Y %H:%M")
    except Exception:
        return iso_str


print(_parse_datetime("hôm nay", prefer_end_of_day=True))