"""
舆情日报 API
生成基础报告和AI智能简报
"""
import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# 导入核心模块
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from crawlers import Article
from reporters.daily_report import DailyReporter
from utils.llm_client import LLMClient
from storage.feishu_client import FeishuClient
from web.routes.crawl import get_latest_articles, _latest_crawl_result

router = APIRouter()
logger = logging.getLogger(__name__)


class ReportResponse(BaseModel):
    """报告响应"""
    report: str
    briefing: str = ""
    stats: Dict[str, Any] = {}


def _get_articles_and_stats() -> tuple:
    """获取最近采集的文章和统计数据"""
    articles = get_latest_articles()
    crawl_result = _latest_crawl_result
    
    stats = {
        "total": crawl_result.get("total", 0),
        "sentiment_stats": crawl_result.get("sentiment_stats", {}),
        "keyword_stats": crawl_result.get("keyword_stats", {}),
        "crawled_at": crawl_result.get("crawled_at"),
    }
    
    return articles, stats


@router.get("/data")
async def get_report_data():
    """获取用于生成报告的数据（供前端展示）"""
    articles, stats = _get_articles_and_stats()
    
    if not articles:
        return {
            "has_data": False,
            "message": "暂无采集数据，请先在采集任务页面执行采集。",
            "stats": {"total": 0},
            "articles": [],
        }
    
    return {
        "has_data": True,
        "stats": stats,
        "articles": [
            {
                "title": a.title,
                "author": a.author,
                "platform": a.platform,
                "keyword": a.keyword,
                "sentiment": a.sentiment,
                "url": a.url,
            }
            for a in articles[:20]
        ],
    }


@router.post("/generate")
async def generate_report(use_llm: bool = False):
    """
    生成舆情报告
    
    Args:
        use_llm: 是否使用LLM生成智能简报
    """
    articles, stats = _get_articles_and_stats()
    
    if not articles:
        return {
            "status": "warning",
            "message": "暂无采集数据，请先执行采集任务",
            "report": "今日暂无舆情数据。",
            "stats": {"total": 0, "positive": 0, "negative": 0, "neutral": 0}
        }
    
    try:
        # 生成基础报告
        reporter = DailyReporter()
        report = reporter.generate_report(articles, generate_briefing=use_llm)
        
        return {
            "status": "success",
            "report": report,
            "stats": {
                "total": len(articles),
                "positive": stats["sentiment_stats"].get("积极", 0),
                "negative": stats["sentiment_stats"].get("消极", 0),
                "neutral": stats["sentiment_stats"].get("中立", 0),
            }
        }
        
    except Exception as e:
        logger.error(f"生成报告失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/briefing")
async def generate_briefing():
    """
    生成AI智能简报（基于最近采集的数据）
    """
    articles, stats = _get_articles_and_stats()
    
    if not articles:
        return {
            "status": "warning",
            "message": "暂无采集数据，请先执行采集任务",
            "briefing": "今日暂无舆情数据，无法生成简报。\n\n请先在采集任务页面执行采集任务。"
        }
    
    try:
        llm = LLMClient()
        
        if not llm.is_configured():
            raise HTTPException(
                status_code=400,
                detail="LLM未配置，请在系统配置中填写API Key"
            )
        
        # 生成简报
        briefing = llm.generate_briefing(articles)
        
        if not briefing:
            raise HTTPException(status_code=500, detail="简报生成失败，请稍后重试")
        
        return {
            "status": "success",
            "briefing": briefing,
            "stats": {
                "total": len(articles),
                "positive": stats["sentiment_stats"].get("积极", 0),
                "negative": stats["sentiment_stats"].get("消极", 0),
                "neutral": stats["sentiment_stats"].get("中立", 0),
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"生成简报失败: {e}")
        raise HTTPException(status_code=500, detail=f"生成失败: {str(e)}")


@router.post("/send")
async def send_report_to_feishu(report_content: str = None):
    """将报告发送到飞书群"""
    articles, stats = _get_articles_and_stats()
    
    try:
        feishu = FeishuClient()
        
        if not feishu.webhook_url:
            raise HTTPException(
                status_code=400,
                detail="飞书Webhook未配置，请在系统配置中填写"
            )
        
        # 如果没有提供内容，生成默认报告
        if not report_content:
            if not articles:
                raise HTTPException(
                    status_code=400,
                    detail="暂无采集数据，无法发送报告"
                )
            reporter = DailyReporter()
            report_content = reporter.generate_report(articles)
        
        # 发送到飞书
        success = feishu.send_webhook_message(report_content)
        
        if success:
            return {
                "status": "success",
                "message": "报告已发送到飞书群"
            }
        else:
            raise HTTPException(status_code=500, detail="发送失败，请检查Webhook配置")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"发送报告失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
