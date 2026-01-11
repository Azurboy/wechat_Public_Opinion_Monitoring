# 快速开始指南

## 🚀 5分钟快速打包

### 前提条件
- 已安装Python 3.8+
- 已clone项目到本地

### 步骤

```bash
# 1. 进入项目目录
cd /Users/zayn/ALL_Projects/Monolith_detective

# 2. 安装依赖并打包（一键完成）
python build.py
```

等待5-10分钟，打包完成！

### 查看结果

```bash
# Windows
cd dist
dir

# macOS/Linux
cd dist
ls -lh
```

您会看到：
- `舆情监测系统.exe` (Windows) 或 `舆情监测系统.app` (macOS)
- `README.txt`

### 测试运行

双击运行程序，应该看到：
1. 欢迎界面（首次运行）
2. 配置界面
3. 系统托盘图标

### 分发给他人

```bash
# 将 dist 目录打包
zip -r 舆情监测系统-v1.0.zip dist/
```

发送 zip 文件即可！

## 💡 提示

- 打包的程序约 350-400MB（包含浏览器）
- 首次启动需要5-10秒初始化
- 配置文件保存在用户目录，不影响程序本体
- 可以在不同电脑上使用相同的配置文件

## ❓ 遇到问题？

查看详细文档：
- `PACKAGING_GUIDE.md` - 完整打包指南
- `PACKAGING_PROGRESS.md` - 实现进度
- `README.md` - 项目说明

或查看日志：
- 开发环境: `scheduler.log`
- 打包后: `~/舆情监测系统/logs/scheduler.log`



