from langchain_core.tools import tool
from src.core import supabase
from pydantic import BaseModel, Field
from typing import Optional, Union, List
import dateparser
from datetime import datetime, time

# ==========================================
# CẤU TRÚC DỮ LIỆU ĐẦU VÀO (SCHEMAS)
# ==========================================

class AddExpenseInput(BaseModel):
    user_id: str = Field(description="ID của người dùng (tự động lấy từ system)")
    amount: float = Field(description="Số tiền chi tiêu (ví dụ: 50000)")
    category: str = Field(description="Hạng mục (ví dụ: 'Ăn uống', 'Di chuyển', 'Mua sắm')")
    description: str = Field(description="Mô tả cụ thể khoản chi (ví dụ: 'Ăn phở sáng')")
    expense_date: str = Field(description="Ngày giờ chi tiêu (ví dụ: '14:30 hôm nay', 'hôm qua', '2026-04-12 10:00:00')")

class GetExpenseInput(BaseModel):
    user_id: str = Field(description="ID của người dùng")
    category: Optional[str] = Field(None, description="Hạng mục cần lọc (nếu cần)")
    start_date: Optional[str] = Field(None, description="Ngày bắt đầu khoảng thời gian (ví dụ: 'hôm qua', 'đầu tuần này', '2026-04-01')")
    end_date: Optional[str] = Field(None, description="Ngày kết thúc khoảng thời gian (ví dụ: 'hôm nay', '2026-04-30')")

class UpdateExpenseInput(BaseModel):
    user_id: str = Field(description="ID của người dùng")
    id: int = Field(description="ID duy nhất của khoản chi tiêu cần sửa (Lấy từ get_expense_tool)")
    amount: Optional[float] = Field(None, description="Số tiền mới")
    category: Optional[str] = Field(None, description="Hàng mục mới")
    description: Optional[str] = Field(None, description="Mô tả mới")
    expense_date: Optional[str] = Field(None, description="Ngày giờ chi tiêu mới")

class DeleteExpenseInput(BaseModel):
    user_id: str = Field(description="ID của người dùng")
    id: int = Field(description="ID duy nhất của khoản chi tiêu cần xóa (Lấy từ get_expense_tool)")

# ==========================================
# HÀM BỔ TRỢ (HELPERS)
# ==========================================

def _parse_datetime(dt_str: str, prefer_end_of_day: bool = False) -> Optional[str]:
    """Chuẩn hóa ngày tháng về định dạng ISO 8601 (timestamptz)."""
    if not dt_str:
        return None
    
    parsed = dateparser.parse(dt_str, settings={'PREFER_DATES_FROM': 'past'})
    if not parsed:
        return None
        
    if prefer_end_of_day and parsed.time() == time(0, 0):
        parsed = datetime.combine(parsed.date(), time(23, 59, 59))
        
    return parsed.isoformat()

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
        final_dt = _parse_datetime(expense_date) or datetime.now().isoformat()
        insert_data = {
            "user_id": user_id,
            "amount": amount,
            "category": category,
            "description": description,
            "expense_date": final_dt
        }

        result = supabase.table("expenses").insert(insert_data).execute()
        if result.data:
            return f"✅ Đã ghi nhận: {description} ({category}) - {amount:,.0f} VNĐ. Thời gian: {final_dt}."
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
            parsed_start = _parse_datetime(start_date)
            if parsed_start:
                query = query.gte("expense_date", parsed_start)

        if end_date:
            parsed_end = _parse_datetime(end_date, prefer_end_of_day=True)
            if parsed_end:
                query = query.lte("expense_date", parsed_end)

        result = query.execute()
        if result.data:
            return result.data
        return "🔍 Không tìm thấy khoản chi tiêu nào khớp với khoảng thời gian và hạng mục yêu cầu."
    except Exception as e:
        return f"⚠️ Lỗi truy vấn: {str(e)}"

@tool(args_schema=UpdateExpenseInput)
async def update_expense_tool(user_id: str,
                               id: int,
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
            return f"✅ Đã cập nhật thành công khoản chi ID: {id}."
        return f"❌ Không tìm thấy thông tin để cập nhật."
    except Exception as e:
        return f"⚠️ Lỗi cập nhật: {str(e)}"

@tool(args_schema=DeleteExpenseInput)
async def delete_expense_tool(user_id: str, id: int) -> str:
    """XÓA khoản chi tiêu dựa trên ID."""
    try:
        result = supabase.table("expenses").delete().eq("id", id).eq("user_id", user_id).execute()
        if result.data:
            return f"🗑️ Đã xóa thành công khoản chi ID: {id}."
        return f"❌ Không tìm thấy ID để xóa."
    except Exception as e:
        return f"⚠️ Lỗi khi xóa: {str(e)}"