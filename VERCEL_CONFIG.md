# Vercel 环境变量配置清单

## 📋 必需配置的环境变量

### 1. 飞书配置（必需）

#### FEISHU_APP_ID
- **说明**: 飞书应用 ID
- **您的值**: `cli_a9d43b9265b81cda`
- **如何获取**: 飞书开放平台 > 应用详情 > 凭证与基础信息

#### FEISHU_APP_SECRET
- **说明**: 飞书应用密钥
- **您的值**: `ntA55CsYirxNvIYrk0Rcub8Ge8zJ6yIS`
- **如何获取**: 飞书开放平台 > 应用详情 > 凭证与基础信息

#### FEISHU_APP_TOKEN
- **说明**: 飞书多维表格 App Token
- **您的值**: `Ef6AbW9CxaASWHsJXqLcezb5npO`
- **如何获取**: 从飞书表格URL中提取
  - URL格式: `https://xxx.feishu.cn/base/{APP_TOKEN}?table={TABLE_ID}`

#### FEISHU_TABLE_ID
- **说明**: 飞书数据表 ID
- **您的值**: `tblo08seyidw9a3h`
- **如何获取**: 从飞书表格URL中提取

#### FEISHU_WEBHOOK_URL
- **说明**: 飞书机器人 Webhook URL
- **您的值**: `https://open.feishu.cn/open-apis/bot/v2/hook/cd349857-1019-48b4-b596-281d71807e1f`
- **如何获取**: 飞书群 > 添加机器人 > 自定义机器人 > 复制Webhook地址

---

### 2. LLM配置（必需，用于AI简报）

#### LLM_PROVIDER
- **说明**: LLM提供商
- **您的值**: `siliconflow`
- **可选值**: `siliconflow`, `openai`

#### LLM_MODEL
- **说明**: LLM模型名称
- **您的值**: `deepseek-ai/DeepSeek-V3`
- **推荐值**: `deepseek-ai/DeepSeek-V3`（性价比最高）

#### LLM_API_KEY
- **说明**: LLM API密钥
- **您的值**: `sk-diiiwyikbclbjjxizcoexrzfxzbqcteuywwcedebinumkbld`
- **如何获取**: 硅基流动控制台 > API Keys > 创建新密钥

#### LLM_BASE_URL
- **说明**: LLM API地址
- **您的值**: `https://api.siliconflow.cn/v1`
- **默认值**: `https://api.siliconflow.cn/v1`

---

## 🚀 Vercel配置步骤

### 步骤1: 访问Vercel
1. 登录 https://vercel.com
2. 点击 "Add New Project"

### 步骤2: 导入GitHub项目
1. 选择 "Import Git Repository"
2. 连接GitHub账号（如果还未连接）
3. 搜索并选择 `wechat_Public_Opinion_Monitoring`
4. 点击 "Import"

### 步骤3: 配置环境变量
在项目配置页面，找到 "Environment Variables" 部分，逐一添加以下变量：

```
变量名: FEISHU_APP_ID
值: cli_a9d43b9265b81cda

变量名: FEISHU_APP_SECRET
值: ntA55CsYirxNvIYrk0Rcub8Ge8zJ6yIS

变量名: FEISHU_APP_TOKEN
值: Ef6AbW9CxaASWHsJXqLcezb5npO

变量名: FEISHU_TABLE_ID
值: tblo08seyidw9a3h

变量名: FEISHU_WEBHOOK_URL
值: https://open.feishu.cn/open-apis/bot/v2/hook/cd349857-1019-48b4-b596-281d71807e1f

变量名: LLM_PROVIDER
值: siliconflow

变量名: LLM_MODEL
值: deepseek-ai/DeepSeek-V3

变量名: LLM_API_KEY
值: sk-diiiwyikbclbjjxizcoexrzfxzbqcteuywwcedebinumkbld

变量名: LLM_BASE_URL
值: https://api.siliconflow.cn/v1
```

### 步骤4: 选择环境
每个环境变量都需要选择应用的环境：
- ✅ Production（生产环境）
- ✅ Preview（预览环境）
- ✅ Development（开发环境）

建议全部勾选。

### 步骤5: 部署
1. 点击 "Deploy"
2. 等待构建和部署完成（大约2-3分钟）
3. 部署成功后，点击生成的URL访问

---

## ⚠️ 重要提醒

### 飞书权限检查
部署前确保飞书应用已开通以下权限：
- ✅ `bitable:app` - 访问多维表格
- ✅ `base:record:create` - 创建记录
- ✅ `base:record:retrieve` - 读取记录

**配置方法**：
1. 访问 https://open.feishu.cn/
2. 选择你的应用
3. 点击「权限管理」
4. 搜索并添加上述权限
5. 点击「发布版本」使权限生效

### 将应用添加为表格协作者
1. 打开飞书多维表格
2. 点击右上角「协作」按钮
3. 搜索你的应用名称（例如："舆情监测"）
4. 添加为协作者

---

## 🧪 部署后测试

访问部署的URL，测试以下功能：

1. **首页** - 检查配置状态是否全部显示为✅
2. **采集任务** - 尝试启动一次小规模采集（1-2篇）
3. **飞书表格** - 确认数据成功写入
4. **AI简报** - 尝试生成AI简报

---

## 📞 如果遇到问题

### 问题1: 部署失败，提示构建错误
**解决方案**: 检查 `requirements.txt` 是否完整，Vercel是否支持所有依赖

### 问题2: 飞书写入失败
**解决方案**: 
1. 检查环境变量是否正确
2. 检查飞书权限是否配置
3. 检查应用是否添加为表格协作者

### 问题3: AI简报生成失败
**解决方案**: 
1. 检查 LLM_API_KEY 是否有效
2. 检查硅基流动账户余额
3. 查看Vercel日志获取详细错误信息

### 问题4: Playwright相关错误
**解决方案**: Vercel的Serverless环境可能不支持Playwright。小红书采集功能需要在本地运行或使用其他部署方式（如Railway、Render、Fly.io）。

---

## 🔄 更新部署

代码推送到GitHub后，Vercel会自动重新部署。如果需要手动触发：
1. 访问 Vercel 项目页面
2. 点击 "Deployments" 标签
3. 点击右上角 "Redeploy"

---

## 📊 环境变量快速复制

```bash
# 复制以下内容，在Vercel中逐一添加
FEISHU_APP_ID=cli_a9d43b9265b81cda
FEISHU_APP_SECRET=ntA55CsYirxNvIYrk0Rcub8Ge8zJ6yIS
FEISHU_APP_TOKEN=Ef6AbW9CxaASWHsJXqLcezb5npO
FEISHU_TABLE_ID=tblo08seyidw9a3h
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/cd349857-1019-48b4-b596-281d71807e1f
LLM_PROVIDER=siliconflow
LLM_MODEL=deepseek-ai/DeepSeek-V3
LLM_API_KEY=sk-diiiwyikbclbjjxizcoexrzfxzbqcteuywwcedebinumkbld
LLM_BASE_URL=https://api.siliconflow.cn/v1
```

---

✅ 完成配置后，您的舆情监测系统就可以在Vercel上运行了！




