from database import init_tables, get_db
from auth import hash_password

def initialize():
    print("初始化数据库...")
    init_tables()
    
    with get_db() as db:
        # 检查是否已有管理员账户
        cursor = db.execute("SELECT id FROM users WHERE username = 'admin'")
        if not cursor.fetchone():
            # 创建初始管理员账户 (老师角色)
            pw_hash = hash_password("admin123")
            db.execute(
                "INSERT INTO users (username, password_hash, role, display_name) VALUES (?, ?, ?, ?)",
                ("admin", pw_hash, "teacher", "系统管理员")
            )
            print("已创建初始管理员账户: admin / admin123")
        else:
            print("管理员账户已存在。")

if __name__ == "__main__":
    initialize()
