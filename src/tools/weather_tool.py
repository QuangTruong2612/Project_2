from langchain_core.tools import tool
from pydantic import BaseModel, Field
import dateparser
from src.core import settings
import requests
from datetime import datetime

weather_url = settings.WEATHER_URL
weather_api = settings.WEATHER_API

class WeatherInput(BaseModel):
    location: str = Field(description="vị trí dự báo thời tiết")
    time: str = Field(description="thời gian dự báo thời tiết")


@tool(args_schema=WeatherInput)
async def get_weather_current_tool(location: str) -> str:
    """
    Dùng để  đưa ra thông tin thời tiết ngày tức thì
    Kích hoạt khi người dùng hỏi về thời tiết ngay tức thì

    * LƯU Ý: trước khi gọi tool phải đưa location về tiếng anh. 
    Nếu như người dùng chưa cho location thì phải hỏi người dùng muốn xem thời tiết ở đâu
    """
    try:
        data = requests.get(f"{weather_url}/weather?q={location}&lang=vi&appid={weather_api}&units=metric").json()

        clean_weather = {
            "city": data["name"],
            "condition": data["weather"][0]["description"],
            "current_temp": data["main"]["temp"],
            "feels_like": data["main"]["feels_like"],
            "humidity": data["main"]["humidity"],
            "wind_speed": data["wind"]["speed"],
            "sunset": datetime.fromtimestamp(data["sys"]["sunset"]).strftime('%H:%M')
            }
        return clean_weather
    except Exception as e:
        return f"Lỗi dự báo thời tiết: {str(e)}"


@tool(args_schema=WeatherInput)
async def get_weather_forecast_tool(location: str,
                           time: str) -> str:
    """
    Dùng để dự báo thời tiết theo time
    Kích hoạt khi người dùng hỏi về thời tiết theo time
    
    * LƯU Ý: trước khi gọi tool phải đưa location về tiếng anh. 
    Nếu như người dùng chưa cho location thì phải hỏi người dùng muốn xem thời tiết ở đâu
    """
    try:
        data = requests.get(f"{weather_url}/forecast?q={location}&lang=vi&appid={weather_api}&units=metric").json()

        time_expect = dateparser.parse(time, settings={'PREFER_DATES_FROM': 'future'})
        if not time_expect:
            return "Không thể nhận diện thời gian!"

        before_item = None
        after_item = None

        for item in data["list"]:
            item_dt = datetime.strptime(item['dt_txt'], '%Y-%m-%d %H:%M:%S')
            
            if item_dt < time_expect:
                before_item = item
            elif item_dt > time_expect:
                after_item = item
                break 
            else:
                return item
        
        result = []
        if before_item:
            result.append(before_item)
        if after_item and after_item not in result:
            result.append(after_item)
            
        return result if result else "Không có dữ liệu dự báo cho thời gian này."
    except Exception as e:
        return f"Lỗi dự báo thời tiết: {str(e)}"