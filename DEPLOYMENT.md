# Vercel 部署指南

## 环境变量配置

在 Vercel 项目设置中，添加以下环境变量：

### 飞书配置

| 变量名 | 说明 | 示例值 |
|--------|------|--------|
| `FEISHU_APP_ID` | 飞书应用 ID | `cli_a9d43b9265b81cda` |
| `FEISHU_APP_SECRET` | 飞书应用密钥 | `your_app_secret` |
| `FEISHU_APP_TOKEN` | 飞书多维表格 App Token（从表格URL获取） | `Ef6AbW9CxaASWHsJXqLcezb5npO` |
| `FEISHU_TABLE_ID` | 飞书数据表 ID（从表格URL获取） | `tblo08seyidw9a3h` |
| `FEISHU_WEBHOOK_URL` | 飞书机器人 Webhook URL | `https://open.feishu.cn/open-apis/bot/v2/hook/xxx` |

**如何获取飞书配置：**

1. **App ID 和 App Secret**:
   - 访问 https://open.feishu.cn/
   - 创建应用或选择现有应用
   - 在「凭证与基础信息」中查看

2. **App Token 和 Table ID**:
   - 打开飞书多维表格
   - URL 格式：`https://xxx.feishu.cn/base/{APP_TOKEN}?table={TABLE_ID}&view=xxx`
   - 从 URL 中提取对应值

3. **Webhook URL**:
   - 在飞书群中添加机器人
   - 选择「自定义机器人」
   - 复制 Webhook 地址

### LLM 配置

| 变量名 | 说明 | 示例值 |
|--------|------|--------|
| `LLM_PROVIDER` | LLM 提供商 | `siliconflow` |
| `LLM_MODEL` | 模型名称 | `deepseek-ai/DeepSeek-V3` |
| `LLM_API_KEY` | API 密钥 | `sk-xxxxx` |
| `LLM_BASE_URL` | API 地址 | `https://api.siliconflow.cn/v1` |

**如何获取 LLM API Key：**

1. 注册硅基流动账号：https://siliconflow.cn/
2. 进入控制台，创建 API Key
3. 复制 API Key 到环境变量

### 可选配置

| 变量名 | 说明 | 是否必需 |
|--------|------|----------|
| `WECHAT_MP_COOKIES` | 微信公众号平台 Cookie | 否（需要高级功能时） |
| `XHS_COOKIES` | 小红书 Cookie | 否（需要小红书采集时） |

## 飞书权限配置

确保你的飞书应用已开通以下权限：

1. **多维表格权限**:
   - `bitable:app` - 访问多维表格
   - `base:record:create` - 创建记录
   - `base:record:retrieve` - 读取记录

2. **将应用添加为表格协作者**:
   - 打开飞书多维表格
   - 点击右上角「协作」
   - 搜索你的应用名称并添加

## 部署步骤

1. **Fork 项目**
   - Fork https://github.com/Azurboy/wechat_Public_Opinion_Monitoring 到你的 GitHub

2. **导入到 Vercel**
   - 访问 https://vercel.com/new
   - 选择你 Fork 的项目
   - 点击 Import

3. **配置环境变量**
   - 在 Vercel 项目设置中，找到「Environment Variables」
   - 逐一添加上述环境变量
   - 确保所有变量值正确

4. **部署**
   - 点击 Deploy
   - 等待部署完成
   - 访问生成的域名

5. **验证**
   - 访问部署的网站
   - 检查首页配置状态是否正确
   - 尝试执行一次采集任务

## 常见问题

### Q: 部署后访问报错 500

**A**: 检查环境变量是否配置完整，特别是飞书相关配置。

### Q: 飞书写入失败

**A**: 
1. 确认飞书应用权限已正确配置
2. 确认应用已添加为表格协作者
3. 确认 APP_TOKEN 和 TABLE_ID 正确

### Q: LLM 简报生成失败

**A**: 
1. 检查 LLM_API_KEY 是否有效
2. 检查账户余额是否充足
3. 检查模型名称是否正确

### Q: Cookie 配置

**A**: Cookie 配置用于高级功能（如微信公众号平台登录），一般情况下使用搜狗搜索即可，无需配置。

## 注意事项

1. **环境变量安全**: 不要在代码中硬编码敏感信息
2. **配置文件**: `config/` 目录下的 YAML 文件不应包含敏感信息
3. **数据目录**: Vercel 是无状态部署，`data/` 目录的 Cookie 等文件在重启后会丢失
4. **定时任务**: Vercel Serverless 不支持长时间运行的定时任务，需要使用外部 Cron 服务触发

## 定时采集配置（可选）

可以使用 Vercel Cron Jobs 或第三方服务（如 cron-job.org）定期调用 API：

```bash
# 每天早上8点执行采集
curl -X POST https://your-domain.vercel.app/api/crawl/quick
```

## 更新部署

推送代码到 GitHub 主分支，Vercel 会自动重新部署。


