"""
舆情监测系统 Web 应用
基于 FastAPI 构建，提供配置管理、采集任务、扫码登录等功能
"""
import os
import sys
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional
import logging

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

from web.routes import config_router, crawl_router, auth_router, reports_router

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("舆情监测系统启动...")
    yield
    logger.info("舆情监测系统关闭...")


# 创建 FastAPI 应用
app = FastAPI(
    title="舆情监测系统",
    description="每日舆情监测、情感分析、自动推送",
    version="1.0.0",
    lifespan=lifespan
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件和模板
STATIC_DIR = Path(__file__).parent / "static"
TEMPLATES_DIR = Path(__file__).parent / "templates"

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# 注册路由
app.include_router(config_router, prefix="/api/config", tags=["配置管理"])
app.include_router(crawl_router, prefix="/api/crawl", tags=["采集任务"])
app.include_router(auth_router, prefix="/api/auth", tags=["平台登录"])
app.include_router(reports_router, prefix="/api/reports", tags=["舆情日报"])


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """首页"""
    return templates.TemplateResponse("index.html", {
        "request": request,
        "title": "舆情监测系统",
        "current_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })


@app.get("/config", response_class=HTMLResponse)
async def config_page(request: Request):
    """配置页面"""
    return templates.TemplateResponse("config.html", {
        "request": request,
        "title": "系统配置"
    })


@app.get("/platforms", response_class=HTMLResponse)
async def platforms_page(request: Request):
    """平台管理页面"""
    return templates.TemplateResponse("platforms.html", {
        "request": request,
        "title": "平台管理"
    })


@app.get("/keywords", response_class=HTMLResponse)
async def keywords_page(request: Request):
    """关键词管理页面"""
    return templates.TemplateResponse("keywords.html", {
        "request": request,
        "title": "关键词管理"
    })


@app.get("/tasks", response_class=HTMLResponse)
async def tasks_page(request: Request):
    """任务管理页面"""
    return templates.TemplateResponse("tasks.html", {
        "request": request,
        "title": "采集任务"
    })


@app.get("/reports", response_class=HTMLResponse)
async def reports_page(request: Request):
    """日报查看页面"""
    return templates.TemplateResponse("reports.html", {
        "request": request,
        "title": "舆情日报"
    })


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "ok", "time": datetime.now().isoformat()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )


