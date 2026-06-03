import sqlite3

conn = sqlite3.connect('data/iceberg.db')
total = conn.execute('SELECT COUNT(*) FROM diaries').fetchone()[0]

# 判断空行：所有关键内容字段均为空
empty = conn.execute("""
    SELECT COUNT(*) FROM diaries 
    WHERE COALESCE(TRIM(parent_name),'') = '' 
      AND COALESCE(TRIM(student_name),'') = '' 
      AND COALESCE(TRIM(behavior),'') = '' 
      AND COALESCE(TRIM(feelings),'') = '' 
      AND COALESCE(TRIM(desires),'') = ''
      AND COALESCE(TRIM(coping),'') = ''
      AND COALESCE(TRIM(beliefs),'') = ''
      AND COALESCE(TRIM(self_view),'') = ''
""").fetchone()[0]

print(f"总计: {total} 条")
print(f"空行: {empty} 条") 
print(f"有效: {total - empty} 条")

# 删除空行
conn.execute("""
    DELETE FROM diaries 
    WHERE COALESCE(TRIM(parent_name),'') = '' 
      AND COALESCE(TRIM(student_name),'') = '' 
      AND COALESCE(TRIM(behavior),'') = '' 
      AND COALESCE(TRIM(feelings),'') = '' 
      AND COALESCE(TRIM(desires),'') = ''
      AND COALESCE(TRIM(coping),'') = ''
      AND COALESCE(TRIM(beliefs),'') = ''
      AND COALESCE(TRIM(self_view),'') = ''
""")
conn.commit()

after = conn.execute('SELECT COUNT(*) FROM diaries').fetchone()[0]
print(f"清理后剩余: {after} 条")
conn.close()
