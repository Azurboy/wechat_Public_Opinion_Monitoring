# GitHub推送前检查清单

## ✅ 代码准备

- [ ] 删除或隐藏所有敏感配置
  - [ ] `config/feishu.yaml` 已备份到本地安全位置
  - [ ] `config/keywords.yaml` 已备份（如包含敏感关键词）
  - [ ] 确认 `.gitignore` 包含这些文件

- [ ] 确认示例配置文件完整
  - [ ] `config/feishu.yaml.example` 存在
  - [ ] `config/keywords.yaml.example` 存在
  - [ ] `.env.example` 存在

- [ ] 文档完整性
  - [ ] `README.md` - 项目说明
  - [ ] `DEPLOYMENT.md` - 部署指南
  - [ ] `PROJECT_SUMMARY.md` - 项目总结
  - [ ] `requirements.txt` - 依赖列表

## 🚀 Git操作步骤

### 1. 初始化Git仓库（如未初始化）
```bash
cd /Users/zayn/ALL_Projects/Monolith_detective
git init
```

### 2. 检查Git状态
```bash
git status
```

确认以下文件不在暂存区（应被`.gitignore`忽略）：
- `config/feishu.yaml`
- `config/platforms.yaml`
- `data/`目录
- `.env`文件

### 3. 添加文件到Git
```bash
# 添加所有文件（.gitignore会自动过滤）
git add .

# 或者分类添加
git add crawlers/
git add processors/
git add storage/
git add reporters/
git add utils/
git add web/
git add config/*.example
git add *.md
git add requirements.txt
git add vercel.json
git add .gitignore
git add .env.example
```

### 4. 提交代码
```bash
git commit -m "Initial commit: 舆情监测系统"
```

### 5. 关联远程仓库
```bash
git remote add origin https://github.com/Azurboy/wechat_Public_Opinion_Monitoring.git
```

### 6. 推送到GitHub
```bash
# 首次推送
git push -u origin main

# 如果默认分支是master
git branch -M main
git push -u origin main
```

## 🔒 安全检查

推送前务必确认：

```bash
# 检查是否包含敏感信息
git log --all --full-history --source -- config/feishu.yaml
git log --all --full-history --source -- .env

# 如果上述命令有输出，说明敏感文件被跟踪了，需要移除：
git rm --cached config/feishu.yaml
git rm --cached .env
git commit -m "Remove sensitive files"
```

## 📦 推送内容清单

应该推送的文件：
- ✅ 所有`.py`源代码文件
- ✅ `web/`目录（HTML/CSS/JS）
- ✅ `config/*.example`配置示例
- ✅ `.env.example`环境变量示例
- ✅ `requirements.txt`
- ✅ `vercel.json`
- ✅ `.gitignore`
- ✅ `README.md`
- ✅ `DEPLOYMENT.md`
- ✅ `PROJECT_SUMMARY.md`

不应该推送的文件（应在`.gitignore`中）：
- ❌ `config/feishu.yaml` - 包含真实密钥
- ❌ `config/platforms.yaml` - 可能包含登录状态
- ❌ `.env` - 环境变量
- ❌ `data/` - Cookie等临时数据
- ❌ `venv/` - 虚拟环境
- ❌ `__pycache__/` - Python缓存
- ❌ `.DS_Store` - Mac系统文件

## 🌐 Vercel部署步骤

推送到GitHub后：

1. **访问Vercel**
   - 登录 https://vercel.com
   - 点击 "Add New Project"

2. **导入项目**
   - 选择 "Import Git Repository"
   - 选择 `wechat_Public_Opinion_Monitoring`
   - 点击 "Import"

3. **配置环境变量**
   参考 `DEPLOYMENT.md` 中的环境变量清单

4. **部署**
   - 点击 "Deploy"
   - 等待部署完成
   - 访问生成的URL测试

## 🔄 后续更新

更新代码后：
```bash
git add .
git commit -m "Update: 描述你的更改"
git push
```

Vercel会自动重新部署。

## 🐛 常见问题

### Q: 推送失败，提示"non-fast-forward"
```bash
git pull --rebase origin main
git push
```

### Q: 敏感文件已被提交，如何删除历史记录？
```bash
# 使用BFG Repo-Cleaner或git filter-branch
# 参考：https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository
```

### Q: 需要修改最后一次提交
```bash
git commit --amend -m "新的提交信息"
git push --force  # 注意：只在自己的分支使用
```

## ✅ 完成确认

推送完成后，确认：
- [ ] GitHub仓库可以正常访问
- [ ] README.md显示正确
- [ ] 敏感配置未泄露
- [ ] Vercel部署成功
- [ ] 在Vercel环境下测试基本功能

🎉 恭喜！项目已成功部署到GitHub和Vercel！




