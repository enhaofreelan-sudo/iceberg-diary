import sqlite3

conn = sqlite3.connect('data/iceberg.db')

# 新增用户注册扩展字段
columns = [
    ("enrollment_status", "TEXT DEFAULT ''"),   # enrolled / not_enrolled
    ("relationship", "TEXT DEFAULT ''"),         # 爸爸 / 妈妈 / 自定义
    ("child_age", "TEXT DEFAULT ''"),            # 孩子年龄（未入校用）
    ("problem_desc", "TEXT DEFAULT ''"),         # 孩子的问题（未入校用）
]

for col_name, col_type in columns:
    try:
        conn.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
        print(f"已添加字段: {col_name}")
    except Exception as e:
        if "duplicate column" in str(e).lower():
            print(f"字段已存在: {col_name}")
        else:
            print(f"添加 {col_name} 失败: {e}")

conn.commit()
conn.close()
print("完成")
