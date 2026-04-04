from langchain_core.tools import tool
from src.core.database import supabase
from pydantic import BaseModel, Field
from typing import Optional
import dateparser
from datetime import datetime, timedelta


class addExpenseInput(BaseModel):
    user_id: str = Field(description= "id của user")
    amount: float = Field(description="Số tiền chi tiêu")
    category: str = Field(description="Hạn mục chi tiêu")
    description: str = Field(description="Mô tả chi tiết khoản chi tiêu")
    created_at: Optional[str] = Field(
        default=None, 
        description="Thời gian chi tiêu nếu người dùng nhắc tới (Ví dụ: 'hôm qua', 'thứ 2 tuần trước'). Định dạng ISO hoặc mô tả text."
    ) 

# add expense tool 
@tool(args_schema=addExpenseInput)
async def addExpenseTool(user_id: str, 
                         amount: Optional[float] = None,
                         category: Optional[str] = None,
                         description: Optional[str] = None,
                         created_at: Optional[str] = None) -> str:
    """
    Công cụ này dùng để GHI LẠI (LƯU) một khoản chi tiêu mới của người dùng vào cơ sở dữ liệu.
    Kích hoạt khi người dùng báo cáo một giao dịch chi tiền hoặc muốn lưu lại số tiền đã tiêu.
    Ví dụ: 'Mình vừa ăn phở hết 50k', 'Đổ xăng 30k', 'Hôm qua mua quần áo 500 ngàn', 'Ghi lại cho anh tiền cafe 30000'.

    Hướng dẫn trích xuất tham số:
    - amount: Yêu cầu bắt buộc phải chuyển đổi số tiền viết tắt hoặc bằng chữ thành con số thực tế đầy đủ. Ví dụ: '50k' hoặc '50 ngàn' -> 50000; '1 triệu' hoặc '1 củ' -> 1000000; '5 lít' -> 500000. Tham số này luôn là dạng số.
    - category: Phân loại khoản chi này vào một danh mục phù hợp, ngắn gọn (ví dụ: 'Ăn uống', 'Đi lại', 'Mua sắm', 'Hóa đơn', 'Giải trí', 'Sức khỏe', 'Khác').
    - description: Tóm tắt ngắn gọn và rõ ràng mục đích chi tiêu (ví dụ: 'Ăn bát phở bò', 'Đổ bình xăng', 'Mua quần áo mới').
    - created_at: Trích xuất nguyên văn cụm từ chỉ thời gian nếu người dùng có nhắc đến (ví dụ: 'hôm qua', 'sáng nay', 'tuần trước', '10/3'). Nếu người dùng không nhắc đến thời gian, hãy bỏ trống tham số này.
    """
    try:

        # extract date
        final_date = None
        if created_at:
            # Sử dụng dateparser để hiểu "hôm qua", "2 days ago", "10/3"
            parsed_date = dateparser.parse(created_at, settings={'PREFER_DATES_FROM': 'past'})
            if parsed_date:
                final_date = parsed_date.isoformat()

        insert_data = {
            "user_id": user_id,
            "amount": amount,
            "category": category,
            "description": description
        }

        
        if final_date:
            insert_data["created_at"] = final_date

        result = supabase.table("expenses").insert(insert_data).execute()   
        if result.data:
            time_str = f" vào '{final_date}'" if final_date else ""
            return f"✅ Đã ghi nhận: {description} - {amount:,.0f} VNĐ{time_str}."
        
        return "❌ Lỗi: Không thể lưu vào database."

    except Exception as e:
        return f"⚠️ Lỗi hệ thống: {str(e)}"



class getExpenseInput(BaseModel):
    user_id: str = Field(description= "id của user")
    category: str = Field(description="Hạn mục chi tiêu")
    created_at: Optional[str] = Field(
        default=None, 
        description="Thời gian chi tiêu nếu người dùng nhắc tới (Ví dụ: 'hôm qua', 'thứ 2 tuần trước'). Định dạng ISO hoặc mô tả text."
    ) 


# get expense tool
@tool(args_schema=getExpenseInput)
async def get_expense_tool(
    user_id: str,
    category: Optional[str] = None,
    created_at: Optional[str] = None) -> list[dict]:
    """
    Công cụ này dùng để TRUY VẤN, XEM, THỐNG KÊ hoặc TÌM KIẾM các khoản chi tiêu của người dùng đã được lưu trong cơ sở dữ liệu.
    Kích hoạt khi người dùng đặt câu hỏi về lịch sử tiêu tiền.
    Ví dụ: 'Hôm nay tôi đã tiêu những gì?', 'Tìm các khoản chi ăn uống ngày hôm qua', 'Thống kê tiền cafe tuần trước'.

    Hướng dẫn trích xuất tham số:
    - user_id: Mã định danh của người dùng hiện tại (tự động lấy từ ngữ cảnh hệ thống).
    - category: Lọc theo hạng mục chi tiêu nếu người dùng có chỉ định mảng cụ thể (ví dụ: 'Ăn uống', 'Đi lại', 'Mua sắm'). CHÚ Ý: Nếu người dùng không nhắc đến hạng mục hoặc muốn xem toàn bộ, HÃY TRUYỀN TỪ KHÓA 'all'.
    - created_at: Cụm từ nguyên văn chỉ thời gian cần lọc nếu người dùng có đề cập (ví dụ: 'hôm nay', 'hôm qua', 'tuần trước', 'tháng này', '10/3'). Nếu người dùng muốn xem tất cả thời gian hoặc không nhắc tới, hãy bỏ trống tham số này (None).
    """
    try:
        query = supabase.table("expenses").select("*").eq("user_id", user_id)

        if category != "all":
            query = query.eq("category", category)

        if created_at:
            parsed_date = dateparser.parse(created_at, settings={'PREFER_DATES_FROM': 'past'})
            if parsed_date:
                query = query.eq("created_at", parsed_date.isoformat())

        result = query.execute()
        if result.data:
            return result.data
        else:
            return "Không tìm thấy chi tiêu nào."

    except Exception as e:
        return f"Lỗi truy vấn: {str(e)}"



class updateExpenseInput(BaseModel):
    user_id: str = Field(description= "id của user")
    id: str = Field(description= "id của khoản chi tiêu")
    amount: Optional[float] = Field(description= "Số tiền chi tiêu")
    category: Optional[str] = Field(description= "Hạn mục chi tiêu")
    description: Optional[str] = Field(description= "Mô tả chi tiết khoản chi tiêu")
    created_at: Optional[str] = Field(description= "Thời gian chi tiêu")

# update expenses tool
@tool(args_schema=updateExpenseInput)
async def update_expense_tool(
    user_id: str,
    id: str,
    amount: Optional[float] = None,
    category: Optional[str] = None,
    description: Optional[str] = None,
    created_at: Optional[str] = None) -> str:
    """
    Công cụ này dùng để CẬP NHẬT, SỬA ĐỔI hoặc CHỈNH SỬA một khoản chi tiêu đã được lưu trước đó.
    Kích hoạt khi người dùng muốn thay đổi thông tin của một giao dịch đã ghi nhận.
    Ví dụ: 'Sửa lại khoản ăn uống hôm qua thành 100k', 'Đổi lại ngày chi tiêu', 'Sửa mô tả cho khoản mua sắm'.

    Hướng dẫn trích xuất tham số:
    - user_id: Mã định danh của người dùng hiện tại (tự động lấy từ ngữ cảnh hệ thống).
    - id: Mã định danh duy nhất của khoản chi tiêu cần sửa (bắt buộc phải có).
    - amount: Số tiền mới nếu người dùng muốn thay đổi.
    - category: Hạng mục mới nếu người dùng muốn thay đổi.
    - description: Mô tả mới nếu người dùng muốn thay đổi.
    - created_at: Thời gian mới nếu người dùng muốn thay đổi.
    """
    try:
        update_data = {}
        if amount is not None:
            update_data["amount"] = amount
        if category is not None:
            update_data["category"] = category
        if description is not None:
            update_data["description"] = description
        if created_at is not None:
            update_data["created_at"] = created_at

        result = supabase.table("expenses").update(update_data).eq("id", id).execute()
        if result.data:
            return f"✅ Đã cập nhật khoản chi tiêu: {id}"
        else:
            return "❌ Không tìm thấy khoản chi tiêu cần cập nhật."

    except Exception as e:
        return f"Lỗi cập nhật: {str(e)}"