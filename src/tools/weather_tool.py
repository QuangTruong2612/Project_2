from langchain_core.tools import tool
from pydantic import BaseModel, Field
import dateparser
import httpx
from datetime import datetime
from src.core import settings
from typing import Optional, List, Union

weather_url = settings.WEATHER_URL
weather_api = settings.WEATHER_API


# ==========================================
# CẤU TRÚC DỮ LIỆU ĐẦU VÀO (SCHEMAS)
# ==========================================

class WeatherCurrentInput(BaseModel):
    location: str = Field(description="Tên thành phố hoặc vị trí (văn bản tiếng Anh, ví dụ: 'Da Nang', 'London')")

class WeatherForecastInput(BaseModel):
    location: str = Field(description="Tên thành phố hoặc vị trí (văn bản tiếng Anh, ví dụ: 'Da Nang', 'London')")
    time: str = Field(description="Thời gian cụ thể cần dự báo (ví dụ: 'tomorrow', '2026-04-12 15:00:00')")


# ==========================================
# HÀM BỔ TRỢ (HELPERS)
# ==========================================

def _format_weather_data(item: dict, city_name: Optional[str] = None) -> dict:
    """Helper định dạng lại dữ liệu thời tiết cho đồng nhất."""
    return {
        "city": city_name or "N/A",
        "time": item.get("dt_txt", "Hiện tại"),
        "condition": item["weather"][0]["description"],
        "temp": item["main"]["temp"],
        "feels_like": item["main"]["feels_like"],
        "humidity": item["main"]["humidity"],
        "wind_speed": item["wind"]["speed"],
        "sunset": datetime.fromtimestamp(item["sys"]["sunset"]).strftime('%H:%M') if "sys" in item and "sunset" in item["sys"] else "N/A"
    }


# ==========================================
# CÔNG CỤ (TOOLS)
# ==========================================
# tool get weather current
@tool(args_schema=WeatherCurrentInput)
async def get_weather_current_tool(location: str) -> Union[dict, str]:
    """
    Lấy thông tin thời tiết HIỆN TẠI (ngay bây giờ).
    
    HƯỚNG DẪN:
    1. Chỉ sử dụng khi người dùng hỏi về thời tiết hiện tại hoặc không đề cập thời gian cụ thể.
    2. PHẢI dịch tên địa điểm sang tiếng Anh trước khi gọi (ví dụ: 'Hà Nội' -> 'Hanoi').
    3. Nếu người dùng chưa cung cấp địa điểm, hãy hỏi họ trước khi gọi tool.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{weather_url}/weather",
                params={
                    "q": location,
                    "lang": "vi",
                    "appid": weather_api,
                    "units": "metric"
                }
            )
            data = response.json()
            
            if response.status_code != 200:
                return f"Lỗi từ OpenWeatherMap: {data.get('message', 'Không xác định')}"

            return _format_weather_data(data, city_name=data.get("name"))
    except Exception as e:
        return f"Lỗi hệ thống dự báo: {str(e)}"


# tool get weather forecast
@tool(args_schema=WeatherForecastInput)
async def get_weather_forecast_tool(location: str, time: str) -> Union[List[dict], str]:
    """
    Dự báo thời tiết cho một THỜI ĐIỂM CỤ THỂ hoặc trong tương lai (ví dụ: ngày mai, chiều nay).
    
    HƯỚNG DẪN:
    1. Sử dụng khi câu hỏi có mốc thời gian (ví dụ: 'mai', 'thứ 2 tới', '15h chiều nay').
    2. PHẢI dịch tên địa điểm sang tiếng Anh trước khi gọi.
    3. Trả về các mốc thời gian gần nhất với yêu cầu để bạn có thể tổng hợp câu trả lời tốt nhất.
    """
    try:
        time_expect = dateparser.parse(time, settings={'PREFER_DATES_FROM': 'future'})
        if not time_expect:
            return "Không thể nhận diện thời gian yêu cầu. Vui lòng thử lại với định dạng khác."

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{weather_url}/forecast",
                params={
                    "q": location,
                    "lang": "vi",
                    "appid": weather_api,
                    "units": "metric"
                }
            )
            data = response.json()
            
            if response.status_code != 200:
                return f"Lỗi từ OpenWeatherMap: {data.get('message', 'Không xác định')}"

            city_name = data.get("city", {}).get("name")
            before_item = None
            after_item = None

            for item in data["list"]:
                item_dt = datetime.strptime(item['dt_txt'], '%Y-%m-%d %H:%M:%S')
                
                if item_dt == time_expect:
                    return _format_weather_data(item, city_name)
                elif item_dt < time_expect:
                    before_item = item
                elif item_dt > time_expect:
                    after_item = item
                    break     

            
            results = []
            if before_item:
                results.append(_format_weather_data(before_item, city_name))
            if after_item and (not before_item or after_item['dt_txt'] != before_item['dt_txt']):
                results.append(_format_weather_data(after_item, city_name))
                
            return results if results else "Không tìm thấy dữ liệu dự báo cho thời điểm này trong 5 ngày tới."
            
    except Exception as e:
        return f"Lỗi dự báo thời tiết: {str(e)}"
