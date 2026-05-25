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
- [x] 后端 FastAPI 服务（接收数据 → Webhook 推送）
- [ ] 腾讯云服务器部署
- [ ] 企业微信群机器人 Webhook 对接

## 已完成功能

1. 移动端交互式冰山日记填写界面
2. 分层引导问题与参考示例
3. 情绪/渴望标签交互选择
4. Canvas 生成冰山日记长图（2x 分辨率）
5. 图片下载、剪贴板复制、文字记录导出
6. localStorage 本地数据持久化
7. FastAPI 后端服务 + 企业微信 Webhook 数据推送

## 待开发功能

1. 腾讯云服务器部署上线
2. 企业微信群机器人配置

## 废弃功能

- Cloudflare Workers 中间层方案（已改为腾讯云服务器直接部署）

## 技术栈

- 前端：HTML + CSS + JavaScript（单文件应用）
- 字体：Noto Sans SC（Google Fonts）
- 后端：Python FastAPI + httpx
- 数据推送：企业微信群机器人 Webhook
- 托管：腾讯云服务器

## 文件结构

```
冰山日记/
├── index.html          # 主应用（全部前端代码）
├── cover.png           # 封面引导图
├── cover.webp          # 封面图 WebP 格式
├── favicon.png         # 站点图标
├── robots.txt          # SEO 配置
├── .gitignore          # Git 忽略规则
├── README.md           # 项目文档
└── server/             # 后端服务
    ├── app.py           # FastAPI 主服务
    ├── config.py        # 配置文件（Webhook URL）
    └── requirements.txt # Python 依赖
```

## 部署方式

1. 腾讯云服务器安装 Python 3.8+
2. `cd server && pip install -r requirements.txt`
3. 配置 `config.py` 中的 `WEBHOOK_URL`
4. `python app.py` 启动服务（端口 8900）
5. 用户通过 `http://服务器IP:8900` 访问
