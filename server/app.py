"""
冰山日记 - 后端服务
接收前端表单数据，通过企业微信群机器人 Webhook 推送到群里
"""

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import time
from config import FEISHU_APP_ID, FEISHU_APP_SECRET, FEISHU_APP_TOKEN, FEISHU_TABLE_ID, PORT

app = FastAPI(title="冰山日记后端")

# 跨域配置（允许前端页面调用）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)

# 用于缓存飞书 tenant_access_token
_feishu_token_cache = {
    "token": None,
    "expire_at": 0
}

async def get_tenant_access_token() -> str:
    """获取飞书 tenant_access_token 并带缓存"""
    current_time = time.time()
    if _feishu_token_cache["token"] and current_time < _feishu_token_cache["expire_at"]:
        return _feishu_token_cache["token"]

    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    payload = {
        "app_id": FEISHU_APP_ID,
        "app_secret": FEISHU_APP_SECRET
    }
    
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(url, json=payload)
        data = resp.json()
        if data.get("code") == 0:
            token = data["tenant_access_token"]
            # 提前 5 分钟过期
            _feishu_token_cache["token"] = token
            _feishu_token_cache["expire_at"] = current_time + data["expire"] - 300
            return token
        else:
            raise Exception(f"获取飞书 Token 失败: {data.get('msg')}")

async def send_to_feishu_bitable(data: dict) -> dict:
    """发送数据到飞书多维表格"""
    if "待替换" in FEISHU_APP_TOKEN or "待替换" in FEISHU_TABLE_ID:
        raise Exception("飞书多维表格凭证尚未配置，请先在 config.py 中填写配置信息。")

    token = await get_tenant_access_token()
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{FEISHU_TABLE_ID}/records"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # 构造飞书多维表格需要的字段映射
    user_info = data.get("userInfo", {})
    layers = data.get("layers", {})
    
    # 这里的键名必须与飞书多维表格中设置的列名完全一致
    fields = {
        "提交时间": data.get("submitTime", ""),
        "家长姓名": user_info.get("parentName", ""),
        "学生姓名": user_info.get("studentName", ""),
        "心理老师": user_info.get("psychologyTeacher", ""),
        "陪伴老师": user_info.get("companionTeacher", ""),
        "行为": layers.get("behavior", ""),
        "应对方式": layers.get("coping", ""),
        "感受": layers.get("feelings", ""),
        "观点": layers.get("beliefs", ""),
        "期待自己": layers.get("expectations-self", ""),
        "期待他人": layers.get("expectations-other", ""),
        "别人对我的期待": layers.get("expectations-perceived", ""),
        "渴望": layers.get("desires", ""),
        "自我": layers.get("self", "")
    }
    
    payload = {
        "fields": fields
    }

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(url, headers=headers, json=payload)
        return resp.json()

@app.post("/api/submit")
async def submit_diary(request: Request):
    """接收前端提交的冰山日记数据"""
    try:
        data = await request.json()

        # 基础校验
        if not data.get("userInfo") and not data.get("layers"):
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "提交数据为空"}
            )

        # 发送到飞书多维表格
        result = await send_to_feishu_bitable(data)

        if result.get("code") == 0:
            return {"success": True, "message": "提交成功"}
        else:
            return JSONResponse(
                status_code=500,
                content={"success": False, "message": f"飞书写入失败: {result.get('msg', '未知错误')}"}
            )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": str(e)}
        )


@app.get("/api/health")
async def health_check():
    """健康检查接口"""
    return {"status": "ok", "service": "冰山日记后端"}


# 挂载静态文件（前端页面），放在路由定义之后
# 将 index.html、cover.png 等放在上级目录
app.mount("/", StaticFiles(directory="..", html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    print(f"冰山日记后端启动: http://0.0.0.0:{PORT}")
    uvicorn.run(app, host="0.0.0.0", port=PORT)
