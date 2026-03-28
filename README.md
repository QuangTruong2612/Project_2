# 🤖 Personal AI Agent - Trợ lý Ảo Cá nhân Đa dụng

Một hệ thống chatbot thông minh dựa trên kiến trúc AI Agent, có khả năng thấu hiểu ngôn ngữ tự nhiên, lập kế hoạch (reasoning), tự động gọi công cụ (tool calling) và sở hữu bộ nhớ dài hạn.

## 🎯 1. Mục tiêu Dự án
Xây dựng một trợ lý ảo cá nhân hỗ trợ các tác vụ hằng ngày, giảm tải khối lượng công việc thủ công và cung cấp khả năng lưu trữ, truy xuất thông tin cá nhân mạnh mẽ thông qua RAG và GraphRAG.

## 🏗️ 2. Kiến trúc Hệ thống (System Architecture)
Hệ thống được thiết kế theo mô hình Micro-services bao gồm:
- **Core AI Engine:** Quản lý luồng hội thoại, định tuyến ý định (intent routing) và gọi API công cụ.
- **Data & Memory Layer:** Quản lý trí nhớ ngắn hạn (Session), dài hạn (Vector DB) và siêu dữ liệu đồ thị (Graph DB).
- **Deployment:** Vận hành trên môi trường container hóa để đảm bảo tính ổn định.

## 🛠️ 3. Danh sách Công cụ (Tool Registry)

### 3.1. Các Công cụ Tiện ích Hằng ngày (Daily Utilities)
- **📰 News Summarizer Tool:** Cào dữ liệu web và tóm tắt tin tức nóng hổi theo chủ đề.
- **📅 Calendar & Schedule Tool:** Tích hợp Google Calendar API để quản lý, thêm/sửa/xóa và nhắc nhở lịch trình.
- **💰 Quick Expense Tracker:** Trích xuất tự động số tiền và phân loại chi tiêu từ tin nhắn tự nhiên.
- **🌤️ Weather & Local Tool:** Cung cấp thông tin thời tiết và tiện ích địa phương theo thời gian thực.

### 3.2. Các Công cụ Tri thức & Trí nhớ (RAG-based Tools)
- **🔖 Personal Bookmark RAG:** Lưu trữ, phân mảnh (chunking) và cho phép hỏi đáp trên các URL/bài báo đã lưu.
- **📄 Home Document RAG:** Tra cứu thông tin từ tài liệu cá nhân (PDF hướng dẫn sử dụng, hợp đồng, v.v.).
- **🧠 Graph Memory Tool:** Trích xuất thực thể và mối quan hệ từ hội thoại hằng ngày, tạo Knowledge Graph cá nhân để suy luận ngữ cảnh phức tạp.

## 💻 4. Công nghệ Sử dụng (Tech Stack)
- **Ngôn ngữ:** Python 3.12
- **Backend Framework:** FastAPI, Uvicorn, Pydantic v2
- **AI/Agent Framework:** LangChain, LangGraph / LlamaIndex
- **Cơ sở dữ liệu:**
  - *Vector DB:* ChromaDB (hoặc Milvus)
  - *Graph DB:* FalkorDB
- **Web Crawling:** BeautifulSoup4, HTTPX
- **Môi trường & Triển khai:** Docker, Docker Compose

## 🚀 5. Hướng dẫn Cài đặt (Installation)

### Yêu cầu môi trường
- Python 3.12+
- Docker (Tùy chọn cho Graph/Vector DB)

### Các bước cài đặt
1. **Clone repository:**
   ```bash
   git clone [https://github.com/your-username/personal-ai-agent.git](https://github.com/your-username/personal-ai-agent.git)
   cd personal-ai-agent