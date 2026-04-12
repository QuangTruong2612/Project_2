from langchain_core.tools import tool
from src.core.database import supabase
from pydantic import BaseModel, Field
from typing import Optional
import dateparser

class ExpenseInput(BaseModel):
    user_id: str = Field(description="id của user (hệ thống tự lấy)")
    amount: float = Field(description="Số tiền chi tiêu (luôn là số, vd: 50k -> 50000)")
    category: str = Field(description="Hạng mục chi tiêu (Ăn uống, Đi lại, Mua sắm, v.v.)")
    description: str = Field(description="Mô tả chi tiết khoản chi tiêu")
    expenses_date: str = Field(description="Thời gian chi tiêu.")

# ==========================================
# TOOL 1: THÊM CHI TIÊU
# ==========================================

@tool(args_schema=ExpenseInput)
async def add_expense_tool(user_id: str, 
                           amount: float,
                           category: str,
                           description: str,
                           expenses_date: str) -> str:
    """
    Dùng để GHI LẠI (LƯU) một khoản chi tiêu mới vào cơ sở dữ liệu.
    Kích hoạt khi người dùng báo cáo một giao dịch chi tiền. Ví dụ: 'Mình vừa ăn phở hết 50k'.
    """
    try:
        insert_data = {
            "user_id": user_id,
            "amount": amount,
            "category": category,
            "description": description
        }

        final_date_str = None
        if expenses_date:
            parsed_date = dateparser.parse(expenses_date, settings={'PREFER_DATES_FROM': 'past'})
            if parsed_date:
                final_date_str = parsed_date.strftime('%Y-%m-%d') # Chuẩn hóa về YYYY-MM-DD
                insert_data["expenses_date"] = final_date_str

        result = supabase.table("expenses").insert(insert_data).execute()   
        if result.data:
            time_str = f" vào '{final_date_str}'" if final_date_str else ""
            return f"✅ Đã ghi nhận: {description} - {amount:,.0f} VNĐ{time_str}."
        
        return "❌ Lỗi: Không thể lưu vào database."
    except Exception as e:
        return f"⚠️ Lỗi hệ thống: {str(e)}"

# ==========================================
# TOOL 2: TÌM KIẾM / TRUY VẤN CHI TIÊU
# ==========================================

@tool(args_schema=ExpenseInput)
async def get_expense_tool(user_id: str,
                           category: str,
                           expenses_date: str) -> list[dict] | str:
    """
    Dùng để TRUY VẤN, XEM, THỐNG KÊ danh sách khoản chi tiêu.
    Kích hoạt khi người dùng đặt câu hỏi: 'Hôm nay tôi tiêu gì?', 'Tìm khoản chi mua sắm'.
    CŨNG ĐƯỢC SỬ DỤNG ĐỂ TÌM ID CỦA KHOẢN CHI KHI CẦN CẬP NHẬT.
    """
    try:
        query = supabase.table("expenses").select("*").eq("user_id", user_id)

        if category and category.lower() != "all":
            query = query.eq("category", category)

        if expenses_date:
            parsed_date = dateparser.parse(expenses_date, settings={'PREFER_DATES_FROM': 'past'})
            if parsed_date:
                query = query.eq("expenses_date", parsed_date.strftime('%Y-%m-%d'))

        result = query.execute()
        if result.data:
            return result.data
        else:
            return "Không tìm thấy chi tiêu nào phù hợp."
    except Exception as e:
        return f"Lỗi truy vấn: {str(e)}"

# ==========================================
# TOOL 3: CẬP NHẬT / SỬA CHI TIÊU
# ==========================================
# class UpdateExpenseInput(BaseModel):
#     user_id: str = Field(description="id của user")
#     id: str = Field(description="ID của khoản chi tiêu cần sửa (BẮT BUỘC)")
#     amount: float = Field(description="Số tiền mới")
#     category: str = Field(description="Hạng mục mới")
#     description: str = Field(description="Mô tả mới")
#     expenses_date: str = Field(description="Thời gian mới")

# @tool(args_schema=UpdateExpenseInput)
# async def update_expense_tool(user_id: str,
#                               id: str,
#                               amount: float,
#                               category: str, 
#                               description: str,
#                               expenses_date: str) -> str:
#     """
#     Dùng để CẬP NHẬT hoặc CHỈNH SỬA một khoản chi tiêu đã lưu.
    
#     LUẬT THÉP CẤM QUÊN VỀ ID:
#         + Phải sử dụng công cụ get_expense_tool và truyền các thông tin cần thiết để tìm kiếm và xác định đúng 'id' trước, sau đó mới gọi lại công cụ này.
#     """
#     try:
#         update_data = {}
#         if amount is not None: update_data["amount"] = amount
#         if category is not None: update_data["category"] = category
#         if description is not None: update_data["description"] = description
        
#         # Sửa lỗi quên parse date ở bản cũ của bạn
#         if expenses_date:
#             parsed_date = dateparser.parse(expenses_date, settings={'PREFER_DATES_FROM': 'past'})
#             if parsed_date:
#                 update_data["expenses_date"] = parsed_date.strftime('%Y-%m-%d')

#         if not update_data:
#             return "Không có thông tin nào được yêu cầu cập nhật."

#         result = supabase.table("expenses").update(update_data).eq("id", id).execute()
#         if result.data:
#             return f"✅ Đã cập nhật thành công khoản chi tiêu ID: {id}"
#         else:
#             return f"❌ ID '{id}' KHÔNG TỒN TẠI. Hãy gọi 'get_expense_tool' để lấy lại ID đúng."

#     except Exception as e:
#         return f"Lỗi cập nhật: {str(e)}"