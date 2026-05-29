import httpx
import asyncio
from config import FEISHU_APP_ID, FEISHU_APP_SECRET, FEISHU_APP_TOKEN, FEISHU_TABLE_ID

async def main():
    print("获取 tenant_access_token...")
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    payload = {
        "app_id": FEISHU_APP_ID,
        "app_secret": FEISHU_APP_SECRET
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json=payload)
        data = resp.json()
        if data.get("code") != 0:
            print("获取 Token 失败:", data)
            return
        token = data["tenant_access_token"]
        print("Token 获取成功!")

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # 删除感受的感受 (fldB9Uyeco) 和 期待 (fldEok8tyB)
    fields_to_delete = ["fldB9Uyeco", "fldEok8tyB"]
    for field_id in fields_to_delete:
        print(f"删除字段: {field_id}...")
        del_url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{FEISHU_TABLE_ID}/fields/{field_id}"
        async with httpx.AsyncClient() as client:
            resp = await client.delete(del_url, headers=headers)
            print("删除结果:", resp.json())

    # 增加新字段
    new_fields = ["期待自己", "期待他人", "别人对我的期待"]
    add_url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{FEISHU_TABLE_ID}/fields"
    for field_name in new_fields:
        print(f"添加字段: {field_name}...")
        add_payload = {
            "field_name": field_name,
            "type": 1
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(add_url, headers=headers, json=add_payload)
            print("添加结果:", resp.json())

if __name__ == "__main__":
    asyncio.run(main())
