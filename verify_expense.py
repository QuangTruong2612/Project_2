import asyncio
import os
import sys

# Add current directory to path to import src
sys.path.append(os.getcwd())

from src.tools.expense_tool import add_expense_tool, get_expense_tool, delete_expense_tool

async def verify():
    test_user = "f9d65957-842b-4127-aefd-8c94427968a1"
    
    print("--- 1. Testing Add Expense with Precise Time ---")
    await add_expense_tool.ainvoke({
        "user_id": test_user,
        "amount": 20000,
        "category": "Ăn uống",
        "description": "Cà phê sáng",
        "expense_date": "08:00 hôm nay"
    })
    await add_expense_tool.ainvoke({
        "user_id": test_user,
        "amount": 60000,
        "category": "Ăn uống",
        "description": "Ăn trưa",
        "expense_date": "12:30 hôm nay"
    })
    print("Done adding samples.")

    print("\n--- 2. Testing Range Query (Today only) ---")
    get_res = await get_expense_tool.ainvoke({
        "user_id": test_user,
        "start_date": "today",
        "end_date": "today"
    })
    print(f"Found {len(get_res) if isinstance(get_res, list) else 0} records for today.")
    if isinstance(get_res, list):
        for r in get_res:
            print(f"- {r['expense_date']}: {r['description']} - {r['amount']}")

    print("\n--- 3. Clean up ---")
    if isinstance(get_res, list):
        for r in get_res:
            await delete_expense_tool.ainvoke({"user_id": test_user, "id": r['id']})
    print("Cleanup done.")

if __name__ == "__main__":
    asyncio.run(verify())
