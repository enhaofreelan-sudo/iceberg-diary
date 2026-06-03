import asyncio
import httpx
import time
from config import FEISHU_APP_ID, FEISHU_APP_SECRET, FEISHU_APP_TOKEN, FEISHU_TABLE_ID
from database import get_db, init_tables

_feishu_token_cache = {"token": None, "expire_at": 0}

async def get_tenant_access_token():
    current_time = time.time()
    if _feishu_token_cache["token"] and current_time < _feishu_token_cache["expire_at"]:
        return _feishu_token_cache["token"]

    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    payload = {"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json=payload)
        data = resp.json()
        token = data["tenant_access_token"]
        _feishu_token_cache["token"] = token
        _feishu_token_cache["expire_at"] = current_time + data["expire"] - 300
        return token

async def migrate_data():
    print("开始从飞书迁移数据...")
    token = await get_tenant_access_token()
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{FEISHU_TABLE_ID}/records"
    headers = {"Authorization": f"Bearer {token}"}
    
    has_more = True
    page_token = ""
    total = 0
    
    with get_db() as db:
        # Create a dummy user for migrated records if needed
        cursor = db.execute("SELECT id FROM users WHERE phone = '00000000000'")
        user = cursor.fetchone()
        if not user:
            db.execute("INSERT INTO users (phone, username, password_hash, role, display_name) VALUES ('00000000000', 'migrated', 'none', 'parent', '历史数据')")
            cursor = db.execute("SELECT id FROM users WHERE phone = '00000000000'")
            user = cursor.fetchone()
        user_id = user["id"]
        
        async with httpx.AsyncClient() as client:
            while has_more:
                params = {"page_size": 100}
                if page_token:
                    params["page_token"] = page_token
                resp = await client.get(url, headers=headers, params=params)
                data = resp.json()
                if data.get("code") != 0:
                    print(f"获取失败: {data}")
                    break
                    
                items = data.get("data", {}).get("items", [])
                for item in items:
                    fields = item.get("fields", {})
                    # Insert into sqlite
                    db.execute("""
                        INSERT INTO diaries (
                            user_id, submit_time, parent_name, student_name, psychology_teacher, companion_teacher,
                            behavior, coping, feelings, beliefs, expectations_self, expectations_other, expectations_perceived,
                            desires, self_view
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        user_id,
                        fields.get("提交时间", ""), fields.get("家长姓名", ""), fields.get("学生姓名", ""),
                        fields.get("心理老师", ""), fields.get("陪伴老师", ""),
                        fields.get("行为", ""), fields.get("应对方式", ""), fields.get("感受", ""), fields.get("观点", ""),
                        fields.get("期待自己", ""), fields.get("期待他人", ""), fields.get("别人对我的期待", ""),
                        fields.get("渴望", ""), fields.get("自我", "")
                    ))
                    total += 1
                
                has_more = data.get("data", {}).get("has_more", False)
                page_token = data.get("data", {}).get("page_token", "")
                
    print(f"迁移完成！共迁移了 {total} 条记录。")

if __name__ == "__main__":
    init_tables()
    asyncio.run(migrate_data())
