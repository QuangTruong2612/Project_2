import asyncio
from src.agents.llm_agent_graph import agent
import uuid

async def run_test(query: str, user_id: str = "f9d65957-842b-4127-aefd-8c94427968a1"):
    print(f"\n{'='*20} TESTING QUERY {'='*20}")
    print(f"Query: {query}")
    
    initial_state = {
        "query": query,
        "user_id": user_id,
        "last_agent_response": "",
        "last_agent": "",
        "tool_observations": [],
        "num_steps": 0
    }
    
    # Cấu hình thread_id cho MemorySaver
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    
    final_state = await agent.ainvoke(initial_state, config=config)
    answer = final_state.get("last_agent_response", "")
    
    if answer.startswith("ANSWER:"):
        answer = answer.split("ANSWER:")[1].strip()
    
    print(f"\n[FINAL RESPONSE]:\n{answer}")
    print(f"{'='*55}\n")

async def main():
    # await run_test("Thời tiết ở Đà Nẵng hôm nay thế nào?")

    # # 2. Test Expense
    # await run_test("Mình vừa ăn trưa hết 50k, ghi lại giúp mình vào mục Ăn uống nhé")

    # # 3. Test News
    # await run_test("Tóm tắt giúp mình tin tức từ link này: https://vnexpress.net/di-san-cua-ong-nguyen-phu-trong-4772186.html")

    # # 4. Test Tra cứu chi tiêu
    await run_test("Hôm nay mình đã tiêu những gì rồi?")

if __name__ == "__main__":
    asyncio.run(main())
