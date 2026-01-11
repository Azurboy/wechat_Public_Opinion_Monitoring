# 舆情监测系统 (Public Opinion Monitoring)

一个基于 Python + FastAPI 的舆情监测系统，支持微信公众号、小红书等平台的内容采集、情感分析和自动推送。

## 功能特性

- 🚀 **多平台采集**: 支持微信公众号（搜狗搜索）、小红书等平台
- 🤖 **AI 智能分析**: 集成 DeepSeek LLM 进行情感分析和智能简报生成
- 📊 **飞书集成**: 自动存储到飞书多维表格，支持机器人消息推送
- 🎯 **智能过滤**: 关键词关联过滤，时间过滤，自动去重
- 🌐 **Web 界面**: 现代化的 Web 管理界面，支持可视化配置和任务管理
- ⏰ **定时任务**: 支持每日自动采集和报告推送

## 快速开始

### 本地运行

1. 克隆项目
```bash
git clone https://github.com/Azurboy/wechat_Public_Opinion_Monitoring.git
cd wechat_Public_Opinion_Monitoring
```

2. 安装依赖
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. 配置文件
复制 `.env.example` 到 `.env` 并填写配置：
```bash
cp .env.example .env
# 编辑 .env 填写飞书和 LLM 配置
```

或者编辑 `config/` 目录下的 YAML 配置文件：
- `config/feishu.yaml`: 飞书配置
- `config/keywords.yaml`: 监测关键词
- `config/platforms.yaml`: 平台配置

4. 启动服务
```bash
cd web
uvicorn app:app --host 0.0.0.0 --port 8000
```

访问 http://localhost:8000

### Vercel 部署

1. Fork 本项目到你的 GitHub

2. 在 Vercel 中导入项目

3. 配置环境变量：
   - `FEISHU_APP_ID`: 飞书应用 ID
   - `FEISHU_APP_SECRET`: 飞书应用密钥
   - `FEISHU_APP_TOKEN`: 飞书多维表格 App Token
   - `FEISHU_TABLE_ID`: 飞书数据表 ID
   - `FEISHU_WEBHOOK_URL`: 飞书机器人 Webhook URL
   - `LLM_PROVIDER`: LLM 提供商（默认：siliconflow）
   - `LLM_MODEL`: LLM 模型（默认：deepseek-ai/DeepSeek-V3）
   - `LLM_API_KEY`: LLM API 密钥
   - `LLM_BASE_URL`: LLM API 地址

4. 部署完成！

## 配置说明

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

### 关键词配置

在 `config/keywords.yaml` 中配置监测关键词和过滤规则：
```yaml
keywords:
  - 你的关键词1
  - 你的关键词2

relevance_keywords:
  关键词1:
    - 关联词1
    - 关联词2
```

## 项目结构

```
.
├── crawlers/           # 爬虫模块
│   ├── sogou_wechat.py    # 搜狗微信搜索
│   ├── xhs_crawler.py     # 小红书爬虫
│   └── wechat_mp.py       # 微信公众号平台
├── processors/         # 数据处理模块
│   ├── dedup.py           # 去重
│   ├── sentiment.py       # 情感分析
│   └── filter.py          # 过滤器
├── storage/            # 存储模块
│   └── feishu_client.py   # 飞书客户端
├── reporters/          # 报告生成
│   └── daily_report.py    # 日报生成
├── utils/              # 工具模块
│   └── llm_client.py      # LLM 客户端
├── web/                # Web 应用
│   ├── app.py             # FastAPI 应用
│   ├── routes/            # API 路由
│   ├── templates/         # HTML 模板
│   └── static/            # 静态资源
├── config/             # 配置文件
└── main.py             # CLI 入口
```

## 使用指南

### Web 界面

1. **首页**: 数据看板，查看采集统计和配置状态
2. **采集与日报**: 启动采集任务，生成AI简报
3. **数据概览**: 查看采集数据详情
4. **平台管理**: 配置平台登录状态
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
```

## 技术栈

- **后端**: Python 3.10+, FastAPI, Uvicorn
- **爬虫**: Requests, BeautifulSoup, Playwright
- **数据处理**: SnowNLP (情感分析)
- **LLM**: DeepSeek V3 (via SiliconFlow)
- **存储**: 飞书多维表格
- **前端**: HTML5, CSS3, JavaScript (原生)

## 注意事项

1. 爬虫使用需遵守相关平台的服务条款
2. 建议设置合理的请求间隔，避免被封禁
3. 敏感配置请妥善保管，不要提交到 Git
4. Playwright 需要安装浏览器：`playwright install chromium`

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！

## 联系方式

如有问题，请通过 GitHub Issues 联系。
