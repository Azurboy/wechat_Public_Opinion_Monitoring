# Web API 路由
from .config import router as config_router
from .crawl import router as crawl_router
from .auth import router as auth_router
from .reports import router as reports_router

__all__ = ['config_router', 'crawl_router', 'auth_router', 'reports_router']


