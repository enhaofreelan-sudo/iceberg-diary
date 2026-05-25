"""
冰山日记 - 后端服务
接收前端表单数据，通过企业微信群机器人 Webhook 推送到群里
"""

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from config import WEBHOOK_URL, PORT

app = FastAPI(title="冰山日记后端")

# 跨域配置（允许前端页面调用）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)

# 冰山层次标题映射
LAYER_TITLES = {
    "behavior": "🌊 行为",
    "coping": "🛡️ 应对方式",
    "feelings": "💭 感受",
    "feelings-about-feelings": "🔄 感受的感受",
    "beliefs": "💡 观点",
    "expectations": "⭐ 期待",
    "desires": "💖 渴望",
    "self": "🦋 自我",
}


def build_markdown(data: dict) -> str:
    """将表单数据构建为企业微信 Markdown 格式消息"""
    submit_time = data.get("submitTime", "未知时间")
    user_info = data.get("userInfo", {})
    layers = data.get("layers", {})

    # 标题
    lines = [f"## ❄️ 冰山日记提交"]
    lines.append(f"> 时间：{submit_time}")

    # 个人信息
    parent = user_info.get("parentName", "")
    student = user_info.get("studentName", "")
    teacher_psy = user_info.get("psychologyTeacher", "")
    teacher_comp = user_info.get("companionTeacher", "")

    info_parts = []
    if parent:
        info_parts.append(f"家长：**{parent}**")
    if student:
        info_parts.append(f"学生：**{student}**")
    if teacher_psy:
        info_parts.append(f"心理老师：{teacher_psy}")
    if teacher_comp:
        info_parts.append(f"陪伴老师：{teacher_comp}")

    if info_parts:
        lines.append("> " + "　".join(info_parts))

    lines.append("")

    # 各层内容
    for layer_id, title in LAYER_TITLES.items():
        content = layers.get(layer_id, "").strip()
        if content:
            lines.append(f"**{title}**")
            lines.append(f"{content}")
            lines.append("")

    return "\n".join(lines)


async def send_webhook(markdown_text: str) -> dict:
    """发送 Markdown 消息到企业微信群机器人"""
    payload = {
        "msgtype": "markdown",
        "markdown": {
            "content": markdown_text
        }
    }

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(WEBHOOK_URL, json=payload)
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

        # 构建消息
        markdown = build_markdown(data)

        # 发送到企业微信群
        webhook_result = await send_webhook(markdown)

        if webhook_result.get("errcode") == 0:
            return {"success": True, "message": "提交成功"}
        else:
            return JSONResponse(
                status_code=500,
                content={"success": False, "message": f"Webhook 发送失败: {webhook_result.get('errmsg', '未知错误')}"}
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
