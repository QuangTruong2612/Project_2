from langchain_core.tools import tool
from src.core import supabase
from pydantic import BaseModel, Field
from typing import Optional, Union, List    
import re
import dateparser
from datetime import datetime, time, timedelta, timezone as tz

# ==========================================
# CẤU TRÚC DỮ LIỆU ĐẦU VÀO (SCHEMAS)
# ==========================================
class AddExpenseInput(BaseModel):
    user_id: Optional[str] = Field(None, description="ID của người dùng (tự động lấy từ system, không cần điền)")
    amount: float = Field(description="Số tiền chi tiêu (ví dụ: 50000)")
    category: str = Field(description="Hạng mục (ví dụ: 'Ăn uống', 'Di chuyển', 'Mua sắm')")
    description: str = Field(description="Mô tả cụ thể khoản chi (ví dụ: 'Ăn phở sáng')")
    expense_date: str = Field(description="Ngày giờ chi tiêu (ví dụ: '14:30 hôm nay', 'hôm qua', '2026-04-12 10:00:00')")

class GetExpenseInput(BaseModel):
    user_id: Optional[str] = Field(None, description="ID của người dùng (tự động lấy từ system, không cần điền)")
    category: Optional[str] = Field(None, description="Hạng mục cần lọc (nếu cần)")
    start_date: Optional[str] = Field(None, description="Ngày bắt đầu khoảng thời gian (ví dụ: 'hôm qua', 'đầu tuần này', '2026-04-01')")
    end_date: Optional[str] = Field(None, description="Ngày kết thúc khoảng thời gian (ví dụ: 'hôm nay', '2026-04-30')")

class UpdateExpenseInput(BaseModel):
    user_id: Optional[str] = Field(None, description="ID của người dùng (tự động lấy từ system, không cần điền)")
    id: str = Field(description="ID duy nhất của khoản chi tiêu cần sửa (Lấy từ get_expense_tool)")
    amount: Optional[float] = Field(None, description="Số tiền mới")
    category: Optional[str] = Field(None, description="Hàng mục mới")
    description: Optional[str] = Field(None, description="Mô tả mới")
    expense_date: Optional[str] = Field(None, description="Ngày giờ chi tiêu mới")

class DeleteExpenseInput(BaseModel):
    user_id: Optional[str] = Field(None, description="ID của người dùng (tự động lấy từ system, không cần điền)")
    id: str = Field(description="ID duy nhất của khoản chi tiêu cần xóa (Lấy từ get_expense_tool)")

# ==========================================
def _normalize_time_expr(dt_str: str) -> str:
    """Chuẩn hoá biểu thức giờ kiểu Việt sang dạng dateparser hiểu được."""
    # Sửa lỗi chính tả phổ biến
    dt_str = dt_str.replace("hôm này", "hôm nay").replace("bửa nay", "hôm nay").replace("bữa nay", "hôm nay")
    
    # Chuẩn hoá buổi
    dt_str = dt_str.replace("trưa", "").replace("sáng", "").replace("tối", "")
    # Xử lý riêng chữ chiều: ví dụ "2h chiều" -> "14:00", nhưng dateparser hỗ trợ pm.
    dt_str = dt_str.replace("chiều", "pm")
    dt_str = re.sub(
        r'(\d{1,2})h(\d{2})',
        lambda m: f"{int(m.group(1)):02d}:{m.group(2)}",
        dt_str,
    )
    # Dạng: 14h (chữ h cuối, không có phút)  ->  14:00
    dt_str = re.sub(    
        r'(\d{1,2})h\b',
        lambda m: f"{int(m.group(1)):02d}:00",
        dt_str,
    )
    # Dạng: "9 giờ 30" -> "09:30", "9 giờ" -> "09:00"
    dt_str = re.sub(
        r'(\d{1,2})\s*gi[ờo]\s*(\d{1,2})',
        lambda m: f"{int(m.group(1)):02d}:{int(m.group(2)):02d}",
        dt_str,
    )
    dt_str = re.sub(
        r'(\d{1,2})\s*gi[ờo]\b',
        lambda m: f"{int(m.group(1)):02d}:00",
        dt_str,
    )
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
    normalized = _normalize_time_expr(dt_str)

    _DATEPARSER_SETTINGS = {
        'PREFER_DATES_FROM': 'current_period',
        'RETURN_AS_TIMEZONE_AWARE': False,
        'TIMEZONE': 'Asia/Ho_Chi_Minh',
    }

    parsed = dateparser.parse(normalized, languages=['vi', 'en'], settings=_DATEPARSER_SETTINGS)

    # Thử lại với chuỗi gốc nếu normalized không parse được
    if not parsed and normalized != dt_str:
        parsed = dateparser.parse(dt_str, languages=['vi', 'en'], settings=_DATEPARSER_SETTINGS)

    if not parsed:
        return None

    # Luôn apply giới hạn ngày nếu được yêu cầu
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

# ==========================================
# CÔNG CỤ (TOOLS)
# ==========================================

@tool(args_schema=AddExpenseInput)
async def add_expense_tool(user_id: str, 
                           amount: float,
                           category: str,
                           description: str,
                           expense_date: str) -> str:
    """
    GHI NHẬN một khoản chi tiêu mới. 
    Hỗ trợ cả ngày và giờ. Ví dụ: 'Ghi lại 50k ăn trưa lúc 12h'.
    """
    try:
        # Nếu không parse được, dùng giờ VN hiện tại
        fallback_dt = datetime.now(tz(timedelta(hours=7))).replace(tzinfo=None).isoformat()
        final_dt = _parse_datetime(expense_date) or fallback_dt
        insert_data = {
            "user_id": user_id,
            "amount": amount,
            "category": category,
            "description": description,
            "expense_date": final_dt
        }

        result = supabase.table("expenses").insert(insert_data).execute()
        if result.data:
            display_dt = _format_display_time(final_dt)
            return f"✅ Đã ghi nhận: {description} ({category}) - {amount:,.0f} VNĐ. Thời gian: {display_dt}."
        return "❌ Lỗi: Không thể lưu vào cơ sở dữ liệu."
    except Exception as e:
        return f"⚠️ Lỗi hệ thống: {str(e)}"

@tool(args_schema=GetExpenseInput)
async def get_expense_tool(user_id: str,
                           category: Optional[str] = None,
                           start_date: Optional[str] = None,
                           end_date: Optional[str] = None) -> Union[List[dict], str]:
    """
    TRUY VẤN danh sách chi tiêu theo KHOẢNG THỜI GIAN hoặc HẠNG MỤC. 
    Dùng cho các câu hỏi: 'Tháng này tiêu gì?', 'Chi tiêu từ đầu tuần', 'Hôm qua hết bao nhiêu?'.
    LƯU Ý: Phải lấy 'id' từ đây trước khi Cập nhật hoặc Xóa.
    """
    try:
        query = supabase.table("expenses").select("*").eq("user_id", user_id).order("expense_date", desc=True)

        if category and category.lower() != "all":
            query = query.ilike("category", f"%{category}%")

        if start_date:
            parsed_start = _parse_datetime(start_date, prefer_start_of_day=True)
            if parsed_start:
                query = query.gte("expense_date", parsed_start)

        if end_date:
            parsed_end = _parse_datetime(end_date, prefer_end_of_day=True)
            if parsed_end:
                query = query.lte("expense_date", parsed_end)

        results = query.execute()
        outputs = []
        if results:
            for row in results.data:
                display_dt = _format_display_time(row.get('expense_date', ''))
                outputs.append(
                    f"- #{row['id']} | {row['description'] or 'N/A'} | {row['amount']:,.0f} VNĐ | {display_dt}"
                )
            return "\n".join(outputs)

        return "Không tìm thấy khoản chi tiêu nào."
    except Exception as e:
        return f"⚠️ Lỗi truy vấn: {str(e)}"

@tool(args_schema=UpdateExpenseInput)
async def update_expense_tool(user_id: str,
                               id: str,
                               amount: Optional[float] = None,
                               category: Optional[str] = None, 
                               description: Optional[str] = None,
                               expense_date: Optional[str] = None) -> str:
    """
    SỬA ĐỔI thông tin một khoản chi (bao gồm cả cập nhật thời gian).
    PHẢI tìm ID bằng get_expense_tool trước.
    """
    try:
        update_data = {}
        if amount is not None: update_data["amount"] = amount
        if category: update_data["category"] = category
        if description: update_data["description"] = description
        if expense_date:
            final_dt = _parse_datetime(expense_date)
            if final_dt:
                update_data["expense_date"] = final_dt

        if not update_data:
            return "⚠️ Không có thông tin để cập nhật."

        result = supabase.table("expenses").update(update_data).eq("id", id).eq("user_id", user_id).execute()
        if result.data:
            updated_dt = _format_display_time(result.data[0].get('expense_date', ''))
            return f"✅ Đã cập nhật khoản chi #{id}. Thông tin mới nhất lúc {updated_dt}."
        return f"❌ Không tìm thấy thông tin để cập nhật."
    except Exception as e:
        return f"⚠️ Lỗi cập nhật: {str(e)}"

@tool(args_schema=DeleteExpenseInput)
async def delete_expense_tool(user_id: str, id: str) -> str:
    """XÓA khoản chi tiêu dựa trên ID."""
    try:
        result = supabase.table("expenses").delete().eq("id", id).eq("user_id", user_id).execute()
        if result.data:
            return f"🗑️ Đã xóa thành công khoản chi ID: {id}."
        return f"❌ Không tìm thấy ID để xóa."
    except Exception as e:
        return f"⚠️ Lỗi khi xóa: {str(e)}"