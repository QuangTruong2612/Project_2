import asyncio
import uuid

from langchain_core.messages import HumanMessage

from src.agents.llm_agent_graph import agent


async def run_test(query: str, user_id: str = "f9d65957-842b-4127-aefd-8c94427968a1"):
    print(f"\n{'=' * 20} TESTING QUERY {'=' * 20}")
    print(f"Query: {query}")

    initial_state = {
        "user_id": user_id,
        "messages": [HumanMessage(content=query)],
    }

    config = {"configurable": {"thread_id": str(uuid.uuid4())}}

    final_state = await agent.ainvoke(initial_state, config=config)
    messages = final_state.get("messages", [])
    answer = messages[-1].content if messages else ""

    print(f"\n[FINAL RESPONSE]:\n{answer}")
    print(f"{'=' * 55}\n")


async def main():
    # await run_test("Thời tiết ở Đà Nẵng hôm nay thế nào?")
    # await run_test("Mình vừa ăn trưa hết 50k, ghi lại giúp mình vào mục Ăn uống nhé")
    # await run_test("Tóm tắt giúp mình tin tức từ link này: https://vnexpress.net/...")
    await run_test("Hôm nay mình đã tiêu những gì rồi?")


if __name__ == "__main__":
    asyncio.run(main())
