# ------------------------------------------
# 冰山日记后端配置（模板）
# ------------------------------------------
# 使用方法：复制此文件为 config.py，填入实际凭证
# cp config.example.py config.py

# 飞书自建应用凭证
FEISHU_APP_ID = "替换为你的APP_ID"
FEISHU_APP_SECRET = "替换为你的APP_SECRET"

# 飞书多维表格配置
FEISHU_APP_TOKEN = "替换为多维表格APP_TOKEN"
FEISHU_TABLE_ID = "替换为TABLE_ID"

# 服务端口
PORT = 8900

# JWT 认证配置
JWT_SECRET = "your_super_secret_key_change_me_in_production"
JWT_EXPIRE_DAYS = 30
