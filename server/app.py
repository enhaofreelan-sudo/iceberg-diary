"""
冰山日记 - 后端服务
接收前端表单数据，存储到本地 SQLite 并同步到飞书多维表格
"""

import httpx
import os
import json
import uuid
from typing import Optional
from fastapi import FastAPI, Request, Depends, HTTPException, status, File, UploadFile, Form
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import time
from config import FEISHU_APP_ID, FEISHU_APP_SECRET, FEISHU_APP_TOKEN, FEISHU_TABLE_ID, PORT, TEACHER_INVITE_CODE
from database import get_db, get_teachers_options
from auth import verify_password, create_access_token, decode_token

app = FastAPI(title="冰山日记后端")

# 跨域配置（允许前端页面调用）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===================== 认证基础设施 =====================
# 必须在路由定义之前声明，否则路由中的 Depends(get_current_user) 会因找不到函数而报错

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    """从请求头中提取并验证 JWT，返回当前登录用户信息"""
    payload = decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="凭证无效或已过期",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=401, detail="无效的凭证格式")
        
    with get_db() as db:
        cursor = db.execute("SELECT id, phone, username, role, display_name, parent_name, student_name, teacher_id FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        if user is None:
            raise HTTPException(status_code=401, detail="用户不存在")
        return dict(user)


# ===================== 飞书相关 =====================

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
        "用户ID": data.get("phone", ""),
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


# ===================== 认证路由 =====================

@app.post("/api/auth/login")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """统一登录接口：老师用用户名登录，家长用手机号登录"""
    identifier = form_data.username
    password = form_data.password
    
    with get_db() as db:
        cursor = db.execute("SELECT * FROM users WHERE username = ? OR phone = ?", (identifier, identifier))
        user = cursor.fetchone()
        
    if not user or not verify_password(password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="账号或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    access_token = create_access_token(data={"sub": str(user["id"]), "role": user["role"]})
    return {"access_token": access_token, "token_type": "bearer", "role": user["role"], "display_name": user["display_name"]}

@app.get("/api/auth/me")
async def read_users_me(current_user: dict = Depends(get_current_user)):
    """获取当前登录用户信息"""
    return current_user

class ParentRegister(BaseModel):
    phone: str
    password: str
    invite_code: str
    enrollment_status: str       # enrolled / not_enrolled
    # 已入校字段
    student_name: Optional[str] = ""
    relationship: Optional[str] = ""
    teacher_id: Optional[int] = None
    # 未入校字段
    child_age: Optional[str] = ""
    problem_desc: Optional[str] = ""

class TeacherRegister(BaseModel):
    phone: str
    password: str
    real_name: str
    invite_code: str

@app.post("/api/auth/register_teacher")
async def register_teacher(data: TeacherRegister):
    """老师自助注册接口"""
    import re
    from auth import hash_password

    if data.invite_code != TEACHER_INVITE_CODE:
        raise HTTPException(status_code=400, detail="邀请码错误，无法注册老师账号")

    if not re.match(r'^1[3-9]\d{9}$', data.phone):
        raise HTTPException(status_code=400, detail="请输入有效的11位手机号")

    if len(data.password) < 6:
        raise HTTPException(status_code=400, detail="密码至少6位")

    if not data.real_name or not data.real_name.strip():
        raise HTTPException(status_code=400, detail="请写真实姓名")

    with get_db() as db:
        cursor = db.execute("SELECT id FROM users WHERE phone = ?", (data.phone,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="该手机号已注册，请直接登录")

        pw_hash = hash_password(data.password)
        db.execute("""
            INSERT INTO users (phone, username, password_hash, role, display_name)
            VALUES (?, ?, ?, 'teacher', ?)
        """, (data.phone, data.phone, pw_hash, data.real_name.strip()))
        
        cursor = db.execute("SELECT id, role, display_name FROM users WHERE phone = ?", (data.phone,))
        user = cursor.fetchone()

    access_token = create_access_token(data={"sub": str(user["id"]), "role": user["role"]})
    return {
        "success": True,
        "access_token": access_token,
        "token_type": "bearer",
        "role": user["role"],
        "display_name": user["display_name"]
    }

@app.post("/api/auth/register")
async def register_parent(data: ParentRegister):
    """家长自助注册接口"""
    import re
    from auth import hash_password

    if data.invite_code != TEACHER_INVITE_CODE:
        raise HTTPException(status_code=400, detail="机构邀请码错误，无法注册")

    # 手机号格式校验
    if not re.match(r'^1[3-9]\d{9}$', data.phone):
        raise HTTPException(status_code=400, detail="请输入有效的11位手机号")

    # 密码长度校验
    if len(data.password) < 6:
        raise HTTPException(status_code=400, detail="密码至少6位")

    # 入校状态校验
    if data.enrollment_status not in ("enrolled", "not_enrolled"):
        raise HTTPException(status_code=400, detail="请选择入校状态")

    # 已入校必填项校验
    if data.enrollment_status == "enrolled":
        if not data.student_name or not data.student_name.strip():
            raise HTTPException(status_code=400, detail="请填写孩子姓名")
        if not data.relationship or not data.relationship.strip():
            raise HTTPException(status_code=400, detail="请选择与孩子的关系")

    # 未入校必填项校验
    if data.enrollment_status == "not_enrolled":
        if not data.child_age or not data.child_age.strip():
            raise HTTPException(status_code=400, detail="请填写孩子年龄")
        if not data.child_age.strip().isdigit():
            raise HTTPException(status_code=400, detail="年龄请输入阿拉伯数字")

    # 手机号去重
    with get_db() as db:
        cursor = db.execute("SELECT id FROM users WHERE phone = ?", (data.phone,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="该手机号已注册，请直接登录")

        # 构造显示名称
        if data.enrollment_status == "enrolled":
            display_name = f"{data.student_name}的{data.relationship}"
        else:
            display_name = f"家长({data.phone[-4:]})"

        pw_hash = hash_password(data.password)
        db.execute("""
            INSERT INTO users (phone, username, password_hash, role, display_name, 
                             student_name, enrollment_status, relationship,
                             child_age, problem_desc, teacher_id)
            VALUES (?, ?, ?, 'parent', ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.phone, data.phone, pw_hash, display_name,
            data.student_name or "", data.enrollment_status, data.relationship or "",
            data.child_age or "", data.problem_desc or "", data.teacher_id
        ))

    # 注册成功后自动签发 token
    with get_db() as db:
        cursor = db.execute("SELECT id, role, display_name FROM users WHERE phone = ?", (data.phone,))
        user = cursor.fetchone()

    access_token = create_access_token(data={"sub": str(user["id"]), "role": user["role"]})
    return {
        "success": True,
        "access_token": access_token,
        "token_type": "bearer",
        "role": user["role"],
        "display_name": user["display_name"]
    }


# ===================== 日记提交 =====================

@app.post("/api/diary/submit")
async def submit_diary(
    current_user: dict = Depends(get_current_user),
    data: str = Form(...),
    image: Optional[UploadFile] = File(None)
):
    """接收前端提交的冰山日记数据"""
    try:
        payload = json.loads(data)
        
        # 基础校验：防空行和空数据插入飞书
        user_info = payload.get("userInfo", {})
        layers = payload.get("layers", {})

        has_parent = bool(user_info.get("parentName", "").strip())
        has_student = bool(user_info.get("studentName", "").strip())
        has_layers = any(bool(val.strip()) for val in layers.values() if isinstance(val, str))

        # 若姓名缺失，则拦截提交
        if not (has_parent or has_student):
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "家长姓名与学生姓名不能为空"}
            )

        # 若所有填写的冰山内容层均为空，则拦截提交
        if not has_layers:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "提交数据内容为空，已被系统拦截"}
            )
            
        # 处理图片保存
        image_path = ""
        if image:
            img_filename = f"{uuid.uuid4().hex}.png"
            img_path = os.path.join(os.path.dirname(__file__), "data", "images", img_filename)
            os.makedirs(os.path.dirname(img_path), exist_ok=True)
            with open(img_path, "wb") as buffer:
                buffer.write(await image.read())
            image_path = f"data/images/{img_filename}"
            
        # 保存到 SQLite
        with get_db() as db:
            db.execute("""
                INSERT INTO diaries (
                    user_id, submit_time, parent_name, student_name, psychology_teacher, companion_teacher,
                    behavior, coping, feelings, beliefs, expectations_self, expectations_other, expectations_perceived,
                    desires, self_view, image_path
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                current_user["id"], payload.get("submitTime", ""),
                user_info.get("parentName", ""), user_info.get("studentName", ""),
                user_info.get("psychologyTeacher", ""), user_info.get("companionTeacher", ""),
                layers.get("behavior", ""), layers.get("coping", ""), layers.get("feelings", ""), layers.get("beliefs", ""),
                layers.get("expectations-self", ""), layers.get("expectations-other", ""), layers.get("expectations-perceived", ""),
                layers.get("desires", ""), layers.get("self", ""), image_path
            ))

        # 发送到飞书多维表格（失败不阻塞主流程）
        # 将当前用户手机号注入 payload，供飞书表格写入“用户ID”列
        payload["phone"] = current_user.get("phone", "")
        try:
            await send_to_feishu_bitable(payload)
        except Exception as e:
            print(f"飞书同步失败: {e}")

        return {"success": True, "message": "提交成功"}

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": str(e)}
        )


# ===================== 公共接口 =====================

@app.get("/api/teachers-options")
async def get_teachers():
    """获取老师选项列表（无需鉴权，供家长端下拉使用）"""
    return get_teachers_options()

@app.get("/api/health")
async def health_check():
    """健康检查接口"""
    return {"status": "ok", "service": "冰山日记后端"}


# ===================== 开发者中控台接口 =====================

@app.get("/api/dev/pages")
async def list_dev_pages():
    """扫描 public 目录下所有 HTML 页面（开发者中控台专用）"""
    import glob
    html_files = glob.glob(os.path.join(os.path.dirname(__file__), "../public/*.html"))
    pages = [os.path.basename(f) for f in html_files if os.path.basename(f) != "dashboard.html"]
    return {"pages": sorted(pages)}


# ===================== 老师端接口 =====================

@app.get("/api/teacher/diaries")
async def get_teacher_diaries(current_user: dict = Depends(get_current_user)):
    """获取全部日记列表（供老师端查看）"""
    if current_user["role"] != "teacher":
        raise HTTPException(status_code=403, detail="无权访问")
        
    with get_db() as db:
        cursor = db.execute("SELECT d.*, u.phone FROM diaries d LEFT JOIN users u ON d.user_id = u.id WHERE u.teacher_id = ? ORDER BY d.id DESC", (current_user["id"],))
        return [dict(row) for row in cursor.fetchall()]

@app.get("/api/teacher/diaries/grouped")
async def get_teacher_diaries_grouped(current_user: dict = Depends(get_current_user)):
    """按家长分组返回日记数据"""
    if current_user["role"] != "teacher":
        raise HTTPException(status_code=403, detail="无权访问")

    with get_db() as db:
        cursor = db.execute("SELECT d.*, u.phone FROM diaries d LEFT JOIN users u ON d.user_id = u.id WHERE u.teacher_id = ? ORDER BY d.id DESC", (current_user["id"],))
        all_diaries = [dict(row) for row in cursor.fetchall()]

    # 按 parent_name + student_name 分组
    from collections import OrderedDict
    groups = OrderedDict()
    for d in all_diaries:
        pn = (d.get("parent_name") or "").strip()
        sn = (d.get("student_name") or "").strip()
        if not pn and not sn:
            key = "__unknown__"
        else:
            key = f"{pn}/{sn}"

        if key not in groups:
            groups[key] = {
                "group_key": key,
                "parent_name": pn or "未知家长",
                "student_name": sn or "",
                "count": 0,
                "diaries": []
            }
        groups[key]["count"] += 1
        groups[key]["diaries"].append(d)

    # 按日记数量降序
    result = sorted(groups.values(), key=lambda g: g["count"], reverse=True)
    return result

@app.get("/api/teacher/parents")
async def get_parents_list(current_user: dict = Depends(get_current_user)):
    """获取家长列表"""
    if current_user["role"] != "teacher":
        raise HTTPException(status_code=403, detail="无权访问")
        
    with get_db() as db:
        cursor = db.execute("""
            SELECT id, phone, display_name, parent_name, student_name, 
                   enrollment_status, relationship, child_age, problem_desc, created_at 
            FROM users WHERE role = 'parent' AND teacher_id = ? ORDER BY id DESC
        """, (current_user["id"],))
        return [dict(row) for row in cursor.fetchall()]

class ParentCreate(BaseModel):
    phone: str
    display_name: str

@app.post("/api/teacher/parents")
async def create_parent(data: ParentCreate, current_user: dict = Depends(get_current_user)):
    """创建家长账号（默认密码为手机号后 6 位）"""
    if current_user["role"] != "teacher":
        raise HTTPException(status_code=403, detail="无权访问")
        
    if not data.phone or len(data.phone) != 11:
        raise HTTPException(status_code=400, detail="手机号格式不正确")
        
    from auth import hash_password
    default_pw = hash_password(data.phone[-6:])
    
    with get_db() as db:
        cursor = db.execute("SELECT id FROM users WHERE phone = ?", (data.phone,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="该手机号已存在")
            
        db.execute(
            "INSERT INTO users (phone, username, password_hash, role, display_name, teacher_id) VALUES (?, ?, ?, ?, ?, ?)",
            (data.phone, data.phone, default_pw, "parent", data.display_name, current_user["id"])
        )
    return {"success": True, "message": "添加成功"}

@app.post("/api/teacher/parents/{user_id}/reset_password")
async def reset_parent_password(user_id: int, current_user: dict = Depends(get_current_user)):
    """重置家长密码为手机号后 6 位"""
    if current_user["role"] != "teacher":
        raise HTTPException(status_code=403, detail="无权访问")
        
    from auth import hash_password
    with get_db() as db:
        cursor = db.execute("SELECT phone FROM users WHERE id = ? AND role = 'parent'", (user_id,))
        user = cursor.fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="家长不存在")
            
        new_pw = hash_password(user["phone"][-6:])
        db.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_pw, user_id))
    return {"success": True, "message": "密码已重置为手机号后6位"}


# ===================== 静态文件 & 启动 =====================

# 挂载静态文件（前端页面），放在路由定义之后
# 将 index.html、cover.png 等放在 public 目录
app.mount("/", StaticFiles(directory="../public", html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    print(f"冰山日记后端启动: http://0.0.0.0:{PORT}")
    uvicorn.run(app, host="0.0.0.0", port=PORT)
