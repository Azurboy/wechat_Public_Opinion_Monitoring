# 舆情监测系统 (Public Opinion Monitoring)

一个基于 Python 的舆情监测系统，支持微信公众号、小红书等平台的内容采集、情感分析和自动推送。

## ✨ 功能特性

- 🚀 **多平台采集**: 支持微信公众号（搜狗搜索 + 平台登录）、小红书等
- 🤖 **AI 智能分析**: 集成 DeepSeek LLM 进行情感分析和智能简报生成
- 📊 **飞书集成**: 自动存储到飞书多维表格，支持机器人消息推送
- 🎯 **智能过滤**: 关键词关联过滤，时间过滤，自动去重
- 🌐 **Web界面**: 现代化的Web管理界面
- ⏰ **定时任务**: 支持每日自动采集和报告推送

## 🚀 快速开始

1. **克隆项目**
```bash
git clone https://github.com/Azurboy/wechat_Public_Opinion_Monitoring.git
cd wechat_Public_Opinion_Monitoring
```

2. **安装依赖**
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python -m playwright install chromium
```

3. **配置文件**

复制示例配置：
```bash
cp config/feishu.yaml.example config/feishu.yaml
cp config/keywords.yaml.example config/keywords.yaml
```

编辑 `config/feishu.yaml`，填写飞书和LLM配置。

4. **启动方式**

**Web界面**（推荐）:
```bash
cd web
uvicorn app:app --host 0.0.0.0 --port 8000
```
访问 http://localhost:8000

**命令行**:
```bash
# 立即执行采集
python main.py

# 启动定时任务
python scheduler.py --time 09:00
```

## 📋 配置说明

### 飞书配置

1. 在[飞书开放平台](https://open.feishu.cn/)创建应用
2. 开通权限：
   - `bitable:app`（多维表格）
   - `base:record:create`（创建记录）
   - `base:record:retrieve`（读取记录）
3. 创建多维表格，获取 `app_token` 和 `table_id`
4. 创建机器人，获取 Webhook URL

### LLM 配置

支持使用硅基流动的 DeepSeek V3 模型：
1. 注册[硅基流动](https://siliconflow.cn/)账号
2. 获取 API Key
3. 填写到配置文件中

推荐模型：`deepseek-ai/DeepSeek-V3`（性价比最高）

### 关键词配置

在 `config/keywords.yaml` 或图形界面中配置：
```yaml
keywords:
  - 你的关键词1
  - 你的关键词2

relevance_keywords:
  关键词1:
    - 关联词1
    - 关联词2
```

## 📂 项目结构

```
.
├── main.py                # CLI入口
├── scheduler.py           # 定时任务调度器
│
├── crawlers/              # 爬虫模块
│   ├── sogou_wechat.py       # 搜狗微信搜索
│   ├── wechat_mp.py          # 微信公众号平台（登录）
│   └── xhs_crawler.py        # 小红书爬虫
│
├── processors/            # 数据处理
│   ├── dedup.py              # 去重
│   ├── sentiment.py          # 情感分析
│   └── filter.py             # 智能过滤
│
├── storage/               # 数据存储
│   └── feishu_client.py      # 飞书集成
│
├── reporters/             # 报告生成
│   └── daily_report.py       # 日报生成
│
├── utils/                 # 工具模块
│   └── llm_client.py         # LLM客户端
│
├── web/                   # Web应用
│   ├── app.py                # FastAPI应用
│   ├── routes/               # API路由
│   ├── templates/            # HTML模板
│   └── static/               # 静态资源
│
└── config/                # 配置文件
    ├── feishu.yaml.example
    └── keywords.yaml.example
```

## 📖 使用指南

### Web 界面

1. **首页**: 数据看板，查看采集统计和配置状态
2. **采集与日报**: 启动采集任务，生成AI简报
3. **数据概览**: 查看采集数据详情
4. **平台管理**: 配置平台登录状态（微信、小红书扫码）
5. **系统配置**: 配置飞书和LLM

### CLI 命令

```bash
# 执行采集
python main.py

# 仅采集特定平台
python main.py --platform wechat

# 生成日报
python main.py --report

# 生成AI简报
python main.py --briefing

# 启动定时任务
python scheduler.py --time 09:00

# 立即执行一次
python scheduler.py --run-now
```

## 🛠️ 技术栈

- **语言**: Python 3.8+
- **爬虫**: Requests, BeautifulSoup, Playwright
- **数据处理**: SnowNLP (情感分析)
- **LLM**: DeepSeek V3 (via SiliconFlow API)
- **存储**: 飞书多维表格（lark-oapi）
- **Web**: FastAPI, Uvicorn, Jinja2
- **前端**: HTML5, CSS3, Vanilla JavaScript

## 📦 打包说明

本项目主要为Web应用和命令行工具，推荐通过Git克隆后本地运行。

**环境要求**:
- Python 3.8+
- Playwright浏览器：`playwright install chromium`

详细文档：
- `QUICKSTART.md` - 快速开始
- `DEPLOYMENT.md` - 部署指南

## ⚠️ 注意事项

1. **平台服务条款**: 爬虫使用需遵守相关平台的服务条款
2. **请求频率**: 建议设置合理的请求间隔（默认3秒），避免被封禁
3. **配置安全**: 敏感配置请妥善保管，不要提交到Git
4. **浏览器依赖**: Playwright需要下载浏览器（约200MB）
5. **网络环境**: 建议在稳定的网络环境下运行

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📞 联系方式

如有问题，请通过 GitHub Issues 联系。
