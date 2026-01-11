#!/bin/bash

# 舆情监测系统 - GitHub推送脚本

echo "🚀 开始推送到GitHub..."
echo ""

# 检查Git状态
echo "📋 检查Git状态..."
git status

echo ""
echo "⚠️  请确认以上文件列表不包含敏感信息！"
echo ""
read -p "是否继续推送？(y/n) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]
then
    echo "❌ 已取消推送"
    exit 1
fi

# 尝试推送（HTTPS方式）
echo ""
echo "🌐 尝试使用HTTPS推送..."
git push -u origin main

# 如果HTTPS失败，尝试SSH
if [ $? -ne 0 ]; then
    echo ""
    echo "⚠️  HTTPS推送失败，尝试使用SSH..."
    git remote set-url origin git@github.com:Azurboy/wechat_Public_Opinion_Monitoring.git
    git push -u origin main
fi

# 检查推送结果
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ 推送成功！"
    echo ""
    echo "📝 下一步："
    echo "1. 访问 https://github.com/Azurboy/wechat_Public_Opinion_Monitoring"
    echo "2. 确认代码已成功上传"
    echo "3. 前往 Vercel 部署项目"
    echo "4. 参考 VERCEL_CONFIG.md 配置环境变量"
    echo ""
else
    echo ""
    echo "❌ 推送失败！"
    echo ""
    echo "🔧 可能的解决方案："
    echo "1. 检查网络连接"
    echo "2. 检查GitHub访问权限"
    echo "3. 配置SSH密钥: https://docs.github.com/cn/authentication/connecting-to-github-with-ssh"
    echo "4. 或使用GitHub Desktop进行推送"
    echo ""
fi

