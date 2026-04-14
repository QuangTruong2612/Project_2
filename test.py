from dateparser.search import search_dates
import datetime

def extract_time_for_weather(user_query):
    # Cấu hình để luôn ưu tiên ngày trong tương lai
    settings = {
        'PREFER_DATES_FROM': 'future',
        'RETURN_AS_TIMEZONE_AWARE': False, # Để dễ so sánh với dt_txt của OpenWeather
        'DATE_ORDER': 'DMY' # Ưu tiên hiểu Ngày/Tháng/Năm kiểu Việt Nam
    }
    
    results = search_dates(user_query, languages=['vi'], settings=settings)
    
    if results:
        # results là một list các tuple: [('ngày mai', datetime_object)]
        text_found, dt_object = results[0]
        return dt_object
    
    # Nếu không tìm thấy thời gian, mặc định là ngay bây giờ
    return datetime.datetime.now()

# Demo thực tế
query = "Cho mình hỏi thời tiết Đà Nẵng ngày mai?"
target_dt = extract_time_for_weather(query)

print(f"Thời gian Agent sẽ tra cứu: {target_dt}")