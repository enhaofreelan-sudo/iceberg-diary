# 冰山日记 - 心理觉察工具

基于萨提亚冰山理论的心理觉察 Web 工具，面向家长/学生在心理老师引导下使用。

## 项目开发进度

- [x] 8 层冰山内容填写（行为/应对方式/感受/感受的感受/观点/期待/渴望/自我）
- [x] 情绪词汇标签点选
- [x] 渴望词汇标签点选（依附需求 + 依附恐惧）
- [x] Canvas 2x 高分辨率长图生成
- [x] 图片保存/分享/文字导出
- [x] 个人信息录入（家长姓名、学生姓名、心理老师、陪伴老师）
- [x] GitHub Pages 部署
- [x] 前端数据提交逻辑
- [x] 后端 FastAPI 服务
- [x] 从飞书多维表格迁移为本地 SQLite 数据库持久化
- [x] 引入 JWT 与 bcrypt 鉴权，构建基于角色（家长/老师）的权限体系
- [x] 老师管理控制台（家长账号管理、密码重置、学生日记汇总查看）
- [x] 家长多模式自主注册流程（已入校/未入校）与全局邀请码防恶意注册机制
- [x] 腾讯云服务器部署 + systemd 进程守护
- [x] 后端防空提交校验与拦截逻辑
- [x] 开发者中控台（iframe 实时预览、API 检测、页面自动发现）

## 已完成功能

1. 移动端交互式冰山日记填写界面
2. 分层引导问题与参考示例
3. 情绪/渴望标签交互选择
4. Canvas 生成冰山日记长图（2x 分辨率，并在图片底部整合冰山风格的咨询师二维码名片）
5. 优化移动端图片保存体验，支持在手机浏览器中长按图片保存到相册
6. 图片下载、剪贴板复制、文字记录导出
7. localStorage 本地数据持久化
8. FastAPI 后端服务 + 本地 SQLite 数据库
9. 基于角色的多用户鉴权系统（老师管理后台与家长填写端隔离）
10. `login.html` 集成家长登录与注册流程（支持已入校与未入校双模式采集，并增加全局机构邀请码防恶意注册机制）
11. 老师后台 `teacher.html` 包含日记审查、家长统一管理（录入、展示注册来源及密码重置）
12. 数据库完成历史冗余空行拦截与有效数据迁移
13. 后端拦截未填写冰山内容的空日记提交，防止飞书与数据库中生成空白记录行
14. 开发者中控台 `dashboard.html`，集成 iframe 页面实时预览、后端服务状态监测、API 快捷检测，支持新增页面自动发现
15. 教师端 `teacher.html` 界面全重构：支持基于家长（拼音搜索）的左侧列表和右侧同一 ID 冰山内容的横向滚动可视化布局
16. 增加飞书多维表格测试数据同步脚本 (`server/import_feishu.py`)

## 待开发功能列表

- 无（当前版本核心功能已全部开发完毕）

## 废弃功能

- Cloudflare Workers 中间层方案（已改为腾讯云服务器直接部署）
- 企业微信群机器人 Webhook 推送
- 飞书多维表格 API 持久化（架构升级，已完整迁移至本地 SQLite 数据库）

## 技术栈

- 前端：HTML + CSS + JavaScript（单文件应用）
- 字体：Noto Sans SC（Google Fonts）
- 后端：Python FastAPI + JWT + bcrypt
- 数据存储：SQLite (`data/iceberg.db`)
- 托管：腾讯云服务器 + systemd 进程守护

## 文件结构

```
冰山日记/
├── public/                 # 前端静态资源目录
│   ├── index.html          # 家长填写端（主应用）
│   ├── login.html          # 登录与注册页
│   ├── teacher.html        # 老师管理控制台
│   ├── dashboard.html      # 开发者中控台（仅本地可用）
│   ├── cover.png           # 封面引导图
│   ├── cover.webp          # 封面图 WebP 格式
│   ├── favicon.png         # 站点图标
│   └── robots.txt          # SEO 配置
├── .gitignore              # Git 忽略规则
├── README.md               # 项目文档
└── server/                 # 后端服务
    ├── app.py              # FastAPI 主服务
    ├── auth.py             # 认证与加密模块
    ├── database.py         # SQLite 数据库链接层
    ├── config.py           # 配置文件（环境变量，不上传）
    ├── config.example.py   # 配置模板
    └── requirements.txt    # Python 依赖
```

## 部署与启动方式

### 本地便捷启动 (Mac)
已在根目录提供 `start.command` 脚本。在 Finder（访达）中直接双击该文件，系统将自动弹出终端窗口并启动后台服务，随后自动在浏览器中打开开发者中控台（`http://127.0.0.1:8900/dashboard.html`）。中控台提供所有页面的 iframe 实时预览、服务状态监测和 API 检测功能。

### 服务器常规部署
1. 服务器安装 Python 3.8+
2. `cd server && pip install -r requirements.txt`
3. `cp config.example.py config.py` 并填入相关凭证
4. `python app.py` 启动服务（端口 8900）
5. 推荐配置 systemd 进程守护
