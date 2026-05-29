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

    print("获取多维表格字段列表...")
    url_fields = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{FEISHU_TABLE_ID}/fields"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    async with httpx.AsyncClient() as client:
        resp = await client.get(url_fields, headers=headers)
        fields_data = resp.json()
        if fields_data.get("code") != 0:
            print("获取字段失败:", fields_data)
            return
        
        fields = fields_data["data"]["items"]
        print(f"当前共有 {len(fields)} 个字段:")
        for f in fields:
            print(f"  - {f['field_name']} (ID: {f['field_id']}, Type: {f['type']})")

if __name__ == "__main__":
    asyncio.run(main())
