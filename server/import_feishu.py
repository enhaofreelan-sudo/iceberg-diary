"""
飞书多维表格数据同步脚本
从飞书拉取现有日记数据，导入本地 SQLite 数据库（仅用于本地测试）
"""

import httpx
import time
from config import FEISHU_APP_ID, FEISHU_APP_SECRET, FEISHU_APP_TOKEN, FEISHU_TABLE_ID
from database import get_db, init_tables


def get_tenant_access_token() -> str:
    """获取飞书 tenant_access_token（同步版本）"""
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    payload = {
        "app_id": FEISHU_APP_ID,
        "app_secret": FEISHU_APP_SECRET
    }
    resp = httpx.post(url, json=payload, timeout=10)
    data = resp.json()
    if data.get("code") == 0:
        return data["tenant_access_token"]
    else:
        raise Exception(f"获取飞书 Token 失败: {data.get('msg')}")


def fetch_all_records() -> list:
    """从飞书多维表格拉取所有记录（自动分页）"""
    token = get_tenant_access_token()
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{FEISHU_TABLE_ID}/records"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    all_records = []
    page_token = None

    while True:
        params = {"page_size": 100}
        if page_token:
            params["page_token"] = page_token

        resp = httpx.get(url, headers=headers, params=params, timeout=15)
        data = resp.json()

        if data.get("code") != 0:
            raise Exception(f"飞书 API 错误: {data.get('msg')}")

        items = data.get("data", {}).get("items", [])
        all_records.extend(items)

        has_more = data.get("data", {}).get("has_more", False)
        page_token = data.get("data", {}).get("page_token")

        if not has_more:
            break

    return all_records


def import_to_sqlite(records: list):
    """将飞书记录导入本地 SQLite"""
    # 确保表结构存在
    init_tables()

    # 确保有一个默认用户用于关联导入的日记
    with get_db() as db:
        cursor = db.execute("SELECT id FROM users WHERE username = 'admin'")
        admin = cursor.fetchone()
        if not admin:
            from auth import hash_password
            db.execute(
                "INSERT INTO users (username, password_hash, role, display_name) VALUES (?, ?, ?, ?)",
                ("admin", hash_password("admin123"), "teacher", "系统管理员")
            )
            cursor = db.execute("SELECT id FROM users WHERE username = 'admin'")
            admin = cursor.fetchone()
        admin_id = admin["id"]

    imported = 0
    skipped = 0

    for record in records:
        fields = record.get("fields", {})

        # 提取字段（飞书列名 → 本地字段）
        parent_name = fields.get("家长姓名", "")
        student_name = fields.get("学生姓名", "")
        submit_time = fields.get("提交时间", "")
        psychology_teacher = fields.get("心理老师", "")
        companion_teacher = fields.get("陪伴老师", "")
        behavior = fields.get("行为", "")
        coping = fields.get("应对方式", "")
        feelings = fields.get("感受", "")
        beliefs = fields.get("观点", "")
        expectations_self = fields.get("期待自己", "")
        expectations_other = fields.get("期待他人", "")
        expectations_perceived = fields.get("别人对我的期待", "")
        desires = fields.get("渴望", "")
        self_view = fields.get("自我", "")

        # 处理飞书多维表格中的富文本字段（可能是列表或字典）
        def extract_text(val):
            if isinstance(val, list):
                return ", ".join([v.get("text", str(v)) if isinstance(v, dict) else str(v) for v in val])
            if isinstance(val, dict):
                return val.get("text", str(val))
            return str(val) if val else ""

        parent_name = extract_text(parent_name)
        student_name = extract_text(student_name)
        submit_time = extract_text(submit_time)
        psychology_teacher = extract_text(psychology_teacher)
        companion_teacher = extract_text(companion_teacher)
        behavior = extract_text(behavior)
        coping = extract_text(coping)
        feelings = extract_text(feelings)
        beliefs = extract_text(beliefs)
        expectations_self = extract_text(expectations_self)
        expectations_other = extract_text(expectations_other)
        expectations_perceived = extract_text(expectations_perceived)
        desires = extract_text(desires)
        self_view = extract_text(self_view)

        # 跳过完全空白的记录
        has_content = any([behavior, coping, feelings, beliefs,
                          expectations_self, expectations_other,
                          expectations_perceived, desires, self_view])
        if not has_content and not parent_name and not student_name:
            skipped += 1
            continue

        with get_db() as db:
            db.execute("""
                INSERT INTO diaries (
                    user_id, submit_time, parent_name, student_name,
                    psychology_teacher, companion_teacher,
                    behavior, coping, feelings, beliefs,
                    expectations_self, expectations_other, expectations_perceived,
                    desires, self_view, image_path
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                admin_id, submit_time, parent_name, student_name,
                psychology_teacher, companion_teacher,
                behavior, coping, feelings, beliefs,
                expectations_self, expectations_other, expectations_perceived,
                desires, self_view, ""
            ))
            imported += 1

    return imported, skipped


if __name__ == "__main__":
    print("=" * 50)
    print("  飞书多维表格 → 本地 SQLite 数据同步")
    print("=" * 50)

    print("\n[1/3] 正在从飞书拉取数据...")
    records = fetch_all_records()
    print(f"      拉取到 {len(records)} 条记录")

    print("\n[2/3] 正在导入本地数据库...")
    imported, skipped = import_to_sqlite(records)

    print(f"\n[3/3] 同步完成")
    print(f"      ✅ 成功导入: {imported} 条")
    print(f"      ⏭️  跳过空记录: {skipped} 条")
    print(f"\n重启后端服务即可在教师端查看数据。")
