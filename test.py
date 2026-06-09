#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test.py - Script lập trình kiểm thử tương tác chatbot thông minh.
Hỗ trợ kiểm thử trực tiếp Multi-Agent Graph (Direct Mode) và gọi qua API Endpoint (API Mode).
"""

import os
import sys
import uuid
import asyncio
import logging
from typing import List

# Nạp cấu hình các biến môi trường
from dotenv import load_dotenv
load_dotenv()

# Cấu hình logging tối giản để tránh chen lấn chữ của CLI
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("test_client")

# ANSI Colors
CLEAR_SCREEN = "\033[H\033[2J"
RESET = "\033[0m"
BOLD = "\033[1m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"
WHITE = "\033[37m"

def print_banner():
    print(f"{CYAN}{BOLD}" + "="*70)
    print("      助理机器人 Multi-Agent Chatbot - HỆ THỐNG KIỂM THỬ TƯƠNG TÁC      ")
    print("="*70 + f"{RESET}")
    print(f"Hệ thống hỗ trợ kiểm thử 2 chế độ độc lập:")
    print(f"  {GREEN}{BOLD}1. Chế độ Direct (Offline/CLI){RESET}: Gọi trực tiếp Multi-Agent LangGraph.")
    print(f"  {GREEN}{BOLD}2. Chế độ API (Online){RESET}: Gửi yêu cầu qua FastAPI server (cần bật Docker/Dev server).")
    print(f"{CYAN}" + "="*70 + f"{RESET}\n")

async def test_direct_mode():
    print(f"\n{BLUE}{BOLD}=== [CHẾ ĐỘ DIRECT - CHẠY TRỰC TIẾP GRAPH] ==={RESET}")
    print(f"{YELLOW}Đang khởi tạo các Agent và nạp mô hình từ Groq...{RESET}")
    
    try:
        from src.agents.llm_agent_graph import agent
        from langchain_core.messages import HumanMessage, AIMessage
        print(f"{GREEN}✓ Khởi tạo Multi-Agent Graph thành công!{RESET}")
    except Exception as e:
        print(f"{RED}✗ Lỗi khởi tạo Graph: {e}{RESET}")
        print(f"{YELLOW}Mẹo: Đảm bảo bạn đã khai báo đúng các biến môi trường trong file .env và đã cài đặt môi trường ảo (venv).{RESET}")
        return

    # Thiết lập ID người dùng và phiên
    user_id = input(f"{BOLD}Nhập User ID để test [mặc định: test_user]: {RESET}").strip() or "test_user"
    session_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": session_id}}

    print(f"\n{GREEN}✓ Đã tạo phiên hội thoại mới: {session_id}{RESET}")
    print(f"{CYAN}Gợi ý bạn có thể hỏi chatbot về:{RESET}")
    print(f"  - Thời tiết: 'Thời tiết Hà Nội hôm nay thế nào?' hoặc 'Dự báo thời tiết Đà Nẵng ngày mai'")
    print(f"  - Chi tiêu: 'Mình vừa ăn phở hết 50k' hoặc 'Xem danh sách chi tiêu của mình'")
    print(f"  - Tin tức: 'Có tin tức gì mới không?'")
    print(f"{YELLOW}Gõ 'exit' hoặc 'quit' để quay lại menu chính.{RESET}\n")

    # Lưu trữ lịch sử tin nhắn nội bộ cho CLI
    messages: List = []

    while True:
        try:
            user_input = input(f"{BOLD}{MAGENTA}User ({user_id}) > {RESET}").strip()
            if not user_input:
                continue
            if user_input.lower() in ["exit", "quit"]:
                print(f"{YELLOW}Đang thoát chế độ Direct...{RESET}")
                break

            print(f"{YELLOW}Đang xử lý yêu cầu qua các Specialist Agents...{RESET}")
            
            # Thêm tin nhắn mới vào state
            messages.append(HumanMessage(content=user_input))
            initial_state = {
                "user_id": user_id,
                "messages": messages,
            }

            # Thực thi graph
            final_state = await agent.ainvoke(initial_state, config=config)
            
            # Cập nhật lịch sử tin nhắn từ state mới nhất
            messages = final_state.get("messages", [])

            # Lấy tin nhắn phản hồi cuối cùng của AI
            last_human_idx = next(
                (i for i, m in reversed(list(enumerate(messages))) if isinstance(m, HumanMessage)),
                -1,
            )
            current_turn_msgs = messages[last_human_idx + 1:] if last_human_idx >= 0 else messages
            
            ai_reply = next(
                (m.content for m in reversed(current_turn_msgs) if isinstance(m, AIMessage) and m.content.strip()),
                "Xin lỗi, mình chưa có câu trả lời cho câu này.",
            )

            print(f"\n{BOLD}{GREEN}Assistant > {RESET}{ai_reply}\n")

        except KeyboardInterrupt:
            print(f"\n{YELLOW}Đang thoát chế độ Direct...{RESET}")
            break
        except Exception as e:
            print(f"{RED}⚠ Có lỗi xảy ra trong quá trình xử lý: {e}{RESET}\n")

def test_api_mode():
    print(f"\n{BLUE}{BOLD}=== [CHẾ ĐỘ API - GỬI YÊU CẦU QUA FASTAPI SERVER] ==={RESET}")
    
    # Import httpx để thực hiện cuộc gọi API
    try:
        import httpx
    except ImportError:
        print(f"{YELLOW}Chưa cài đặt 'httpx' trên host. Đang sử dụng 'urllib' để fallback...{RESET}")
        httpx = None

    base_url = "http://localhost:8000"
    health_url = f"{base_url}/health"
    chat_url = f"{base_url}/api/v1/chat"

    # Kiểm tra xem FastAPI Server có đang chạy không
    print(f"{YELLOW}Đang kiểm tra kết nối tới Server {base_url}...{RESET}")
    server_running = False
    
    if httpx:
        try:
            response = httpx.get(health_url, timeout=3.0)
            if response.status_code == 200:
                server_running = True
        except Exception:
            pass
    else:
        import urllib.request
        import json
        try:
            with urllib.request.urlopen(health_url, timeout=3) as req:
                if req.getcode() == 200:
                    server_running = True
        except Exception:
            pass

    if not server_running:
        print(f"{RED}✗ Không thể kết nối tới Server tại {base_url}!{RESET}")
        print(f"{YELLOW}Vui lòng chắc chắn rằng bạn đã khởi chạy môi trường bằng lệnh:{RESET}")
        print(f"  {CYAN}docker compose -f docker-compose.yml -f docker-compose.dev.yml up{RESET}")
        print(f"Hoặc nếu chạy local trực tiếp trên host:")
        print(f"  {CYAN}uvicorn src.main:app --reload{RESET}")
        return

    print(f"{GREEN}✓ Kết nối thành công tới FastAPI Server!{RESET}")
    
    user_id = input(f"{BOLD}Nhập User ID để test [mặc định: test_user]: {RESET}").strip() or "test_user"
    session_id = "" # Để trống để server tự sinh hoặc truyền vào
    print(f"{YELLOW}Gõ 'exit' hoặc 'quit' để quay lại menu chính.{RESET}\n")

    while True:
        try:
            user_input = input(f"{BOLD}{MAGENTA}User ({user_id}) > {RESET}").strip()
            if not user_input:
                continue
            if user_input.lower() in ["exit", "quit"]:
                print(f"{YELLOW}Đang thoát chế độ API...{RESET}")
                break

            payload = {
                "message": user_input,
                "user_id": user_id,
            }
            if session_id:
                payload["session_id"] = session_id

            print(f"{YELLOW}Đang gửi yêu cầu tới API Endpoint...{RESET}")
            
            # Gửi yêu cầu qua HTTP POST
            if httpx:
                try:
                    response = httpx.post(chat_url, json=payload, timeout=60.0)
                    if response.status_code == 200:
                        data = response.json()
                        ai_reply = data.get("response", "")
                        session_id = data.get("session_id", "")
                        print(f"\n{BOLD}{GREEN}Assistant > {RESET}{ai_reply}\n")
                    else:
                        print(f"{RED}✗ Lỗi API (HTTP {response.status_code}): {response.text}{RESET}\n")
                except Exception as e:
                    print(f"{RED}✗ Lỗi kết nối HTTP: {e}{RESET}\n")
            else:
                import urllib.request
                import json
                try:
                    req_payload = json.dumps(payload).encode("utf-8")
                    req = urllib.request.Request(
                        chat_url,
                        data=req_payload,
                        headers={"Content-Type": "application/json"},
                        method="POST"
                    )
                    with urllib.request.urlopen(req, timeout=60) as resp:
                        data = json.loads(resp.read().decode("utf-8"))
                        ai_reply = data.get("response", "")
                        session_id = data.get("session_id", "")
                        print(f"\n{BOLD}{GREEN}Assistant > {RESET}{ai_reply}\n")
                except Exception as e:
                    print(f"{RED}✗ Lỗi kết nối HTTP (Urllib): {e}{RESET}\n")

        except KeyboardInterrupt:
            print(f"\n{YELLOW}Đang thoát chế độ API...{RESET}")
            break

def main():
    while True:
        # Xóa màn hình cho sạch sẽ
        print(CLEAR_SCREEN, end="")
        print_banner()
        choice = input(f"{BOLD}Nhập lựa chọn của bạn (1-3): {RESET}").strip()
        
        if choice == "1":
            asyncio.run(test_direct_mode())
            input(f"\n{YELLOW}Ấn Enter để tiếp tục...{RESET}")
        elif choice == "2":
            test_api_mode()
            input(f"\n{YELLOW}Ấn Enter để tiếp tục...{RESET}")
        elif choice == "3":
            print(f"\n{GREEN}Cảm ơn bạn đã sử dụng hệ thống kiểm thử. Tạm biệt!{RESET}\n")
            break
        else:
            print(f"\n{RED}Lựa chọn không hợp lệ! Vui lòng nhập từ 1 đến 3.{RESET}")
            import time
            time.sleep(1.5)

if __name__ == "__main__":
    main()
