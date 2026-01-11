"""
采集任务 API
执行采集任务、查看任务状态、获取采集结果
"""
import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from threading import Thread
import logging

import yaml
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

# 导入核心模块
import sys
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from crawlers import SogouWechatCrawler, Article
from processors import DedupProcessor, SentimentAnalyzer, RelevanceFilter, TimeFilter
from storage.feishu_client import FeishuClient
from reporters.daily_report import DailyReporter

router = APIRouter()
logger = logging.getLogger(__name__)

# 配置路径
CONFIG_DIR = PROJECT_ROOT / "config"
def _runtime_data_dir() -> Path:
    env_dir = os.environ.get("RUNTIME_DATA_DIR")
    if env_dir:
        p = Path(env_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p
    default = PROJECT_ROOT / "data"
    try:
        default.mkdir(parents=True, exist_ok=True)
        return default
    except Exception:
        tmp = Path("/tmp/monolith_data")
        tmp.mkdir(parents=True, exist_ok=True)
        return tmp
DATA_DIR = _runtime_data_dir()

# 任务状态存储
tasks_status: Dict[str, Dict] = {}

# 全局采集结果存储（供各页面共享）
_latest_crawl_result: Dict[str, Any] = {
    "total": 0,
    "articles": [],
    "sentiment_stats": {},
    "keyword_stats": {},
    "crawled_at": None,
    "task_id": None,
}

def get_latest_articles() -> List[Article]:
    """获取最近采集的文章对象列表（供其他模块使用）"""
    return _latest_crawl_result.get("_article_objects", [])


class CrawlRequest(BaseModel):
    """采集请求"""
    platforms: List[str] = ["wechat"]  # wechat, xhs, all
    keywords: Optional[List[str]] = None  # 自定义关键词，空则使用配置
    filter_enabled: bool = True
    analyze_sentiment: bool = True
    save_to_feishu: bool = True
    generate_briefing: bool = False


class TaskStatus(BaseModel):
    """任务状态"""
    task_id: str
    status: str  # pending, running, completed, failed
    progress: int = 0
    message: str = ""
    result: Optional[Dict] = None
    created_at: str = ""
    completed_at: Optional[str] = None


def load_config() -> Dict:
    """加载配置"""
    keywords_path = CONFIG_DIR / "keywords.yaml"
    platforms_path = CONFIG_DIR / "platforms.yaml"
    
    config = {}
    
    if keywords_path.exists():
        with open(keywords_path, 'r', encoding='utf-8') as f:
            config["keywords"] = yaml.safe_load(f) or {}
    
    if platforms_path.exists():
        with open(platforms_path, 'r', encoding='utf-8') as f:
            config["platforms"] = yaml.safe_load(f) or {}
    
    return config


def run_crawl_task(task_id: str, request: CrawlRequest):
    """执行采集任务（后台线程）"""
    global tasks_status
    
    try:
        tasks_status[task_id]["status"] = "running"
        tasks_status[task_id]["message"] = "正在初始化..."
        
        config = load_config()
        keywords_config = config.get("keywords", {})
        platforms_config = config.get("platforms", {})
        
        # 获取关键词
        keywords = request.keywords or keywords_config.get("keywords", [])
        if not keywords:
            tasks_status[task_id]["status"] = "failed"
            tasks_status[task_id]["message"] = "未配置关键词"
            return
        
        search_config = keywords_config.get("search", {})
        max_pages = search_config.get("max_pages", 3)
        delay = search_config.get("request_delay", 3)
        
        all_articles: List[Article] = []
        
        # 采集微信公众号
        if "wechat" in request.platforms or "all" in request.platforms:
            tasks_status[task_id]["message"] = "正在采集微信公众号..."
            tasks_status[task_id]["progress"] = 10
            
            wechat_config = platforms_config.get("wechat", {})
            method = wechat_config.get("method", "sogou")
            
            if method == "mp":
                from crawlers import WechatMPCrawler
                crawler = WechatMPCrawler(
                    request_delay=delay,
                    data_dir=str(DATA_DIR)
                )
            else:
                crawler = SogouWechatCrawler(request_delay=delay)
            
            wechat_articles = crawler.search_multiple(keywords, max_pages=max_pages)
            all_articles.extend(wechat_articles)
            logger.info(f"微信公众号采集完成: {len(wechat_articles)} 篇")
        
        # 采集小红书
        if "xhs" in request.platforms or "all" in request.platforms:
            tasks_status[task_id]["message"] = "正在采集小红书..."
            tasks_status[task_id]["progress"] = 40
            
            xhs_config = platforms_config.get("xiaohongshu", {})
            if xhs_config.get("enabled", True):
                from crawlers import XHSCrawler
                crawler = XHSCrawler(
                    request_delay=delay,
                    headless=True
                )
                
                sort = xhs_config.get("sort", "time_descending")
                filter_hours = xhs_config.get("filter_hours", 48)
                
                xhs_articles = crawler.search_multiple(
                    keywords, 
                    max_pages=2,
                )
                all_articles.extend(xhs_articles)
                logger.info(f"小红书采集完成: {len(xhs_articles)} 条")
        
        tasks_status[task_id]["progress"] = 60
        
        # 时间过滤
        filter_hours = platforms_config.get("xiaohongshu", {}).get("filter_hours", 48)
        if filter_hours > 0:
            time_filter = TimeFilter(hours=filter_hours)
            all_articles = time_filter.filter_recent(all_articles)
        
        # 关键词过滤
        if request.filter_enabled:
            tasks_status[task_id]["message"] = "正在过滤不相关内容..."
            relevance_filter = RelevanceFilter()
            all_articles = relevance_filter.filter_articles(all_articles)
        
        # 去重
        dedup = DedupProcessor()
        unique_articles = dedup.deduplicate(all_articles)
        
        tasks_status[task_id]["progress"] = 70
        
        # 情感分析
        if request.analyze_sentiment:
            tasks_status[task_id]["message"] = "正在进行情感分析..."
            analyzer = SentimentAnalyzer()
            unique_articles = analyzer.analyze_articles(unique_articles)
        
        tasks_status[task_id]["progress"] = 80
        
        # 保存到飞书
        feishu_result = {"success": 0, "failed": 0, "skipped": 0}
        if request.save_to_feishu:
            tasks_status[task_id]["message"] = "正在保存到飞书..."
            feishu = FeishuClient()
            if feishu.is_configured():
                feishu_result = feishu.add_new_articles(unique_articles)
        
        tasks_status[task_id]["progress"] = 90
        
        # 生成简报
        briefing = None
        if request.generate_briefing:
            tasks_status[task_id]["message"] = "正在生成舆情简报..."
            reporter = DailyReporter(use_llm=True)
            briefing = reporter.generate_llm_briefing(unique_articles)
            
            # 发送到飞书
            feishu = FeishuClient()
            if feishu.webhook_url and briefing:
                full_report = reporter.generate_full_report(unique_articles)
                feishu.send_webhook_message(full_report)
        
        # 统计结果
        sentiment_stats = {"积极": 0, "消极": 0, "中立": 0}
        for article in unique_articles:
            if article.sentiment:
                sentiment_stats[article.sentiment] = sentiment_stats.get(article.sentiment, 0) + 1
        
        keyword_stats = {}
        for article in unique_articles:
            keyword_stats[article.keyword] = keyword_stats.get(article.keyword, 0) + 1
        
        # 完成
        tasks_status[task_id]["status"] = "completed"
        tasks_status[task_id]["progress"] = 100
        tasks_status[task_id]["message"] = "采集完成"
        tasks_status[task_id]["completed_at"] = datetime.now().isoformat()
        
        result_data = {
            "total_articles": len(unique_articles),
            "sentiment_stats": sentiment_stats,
            "keyword_stats": keyword_stats,
            "feishu_result": feishu_result,
            "briefing": briefing[:500] if briefing else None,
            "articles_preview": [
                {
                    "title": a.title,
                    "author": a.author,
                    "platform": a.platform,
                    "keyword": a.keyword,
                    "sentiment": a.sentiment,
                    "url": a.url,
                }
                for a in unique_articles[:20]
            ]
        }
        tasks_status[task_id]["result"] = result_data
        
        # 更新全局采集结果（供各页面共享）
        global _latest_crawl_result
        _latest_crawl_result = {
            "total": len(unique_articles),
            "articles": result_data["articles_preview"],
            "sentiment_stats": sentiment_stats,
            "keyword_stats": keyword_stats,
            "feishu_result": feishu_result,
            "crawled_at": datetime.now().isoformat(),
            "task_id": task_id,
            "_article_objects": unique_articles,  # 存储原始Article对象供日报生成使用
        }
        
    except Exception as e:
        logger.error(f"采集任务失败: {e}")
        tasks_status[task_id]["status"] = "failed"
        tasks_status[task_id]["message"] = str(e)


@router.post("/start", response_model=TaskStatus)
async def start_crawl(request: CrawlRequest, background_tasks: BackgroundTasks):
    """启动采集任务"""
    task_id = f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    tasks_status[task_id] = {
        "task_id": task_id,
        "status": "pending",
        "progress": 0,
        "message": "任务已创建，等待执行",
        "result": None,
        "created_at": datetime.now().isoformat(),
        "completed_at": None,
    }
    
    # 在后台线程执行
    thread = Thread(target=run_crawl_task, args=(task_id, request))
    thread.start()
    
    return TaskStatus(**tasks_status[task_id])


@router.get("/status/{task_id}", response_model=TaskStatus)
async def get_task_status(task_id: str):
    """获取任务状态"""
    if task_id not in tasks_status:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    return TaskStatus(**tasks_status[task_id])


@router.get("/tasks", response_model=List[TaskStatus])
async def list_tasks():
    """列出所有任务"""
    return [TaskStatus(**status) for status in tasks_status.values()]


@router.delete("/tasks/{task_id}")
async def delete_task(task_id: str):
    """删除任务记录"""
    if task_id not in tasks_status:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    del tasks_status[task_id]
    return {"status": "success", "message": "任务已删除"}


@router.post("/quick")
async def quick_crawl(platforms: List[str] = ["wechat"]):
    """
    快速采集（同步执行，适合少量数据）
    """
    global _latest_crawl_result
    
    config = load_config()
    keywords_config = config.get("keywords", {})
    keywords = keywords_config.get("keywords", [])[:2]  # 只用前2个关键词
    
    if not keywords:
        raise HTTPException(status_code=400, detail="未配置关键词")
    
    articles = []
    
    if "wechat" in platforms:
        crawler = SogouWechatCrawler(request_delay=2)
        for kw in keywords:
            articles.extend(crawler.search(kw, max_pages=1))
    
    # 去重
    dedup = DedupProcessor()
    unique = dedup.deduplicate(articles)
    
    # 情感分析
    analyzer = SentimentAnalyzer()
    unique = analyzer.analyze_articles(unique)
    
    # 统计
    sentiment_stats = {"积极": 0, "消极": 0, "中立": 0}
    for article in unique:
        if article.sentiment:
            sentiment_stats[article.sentiment] = sentiment_stats.get(article.sentiment, 0) + 1
    
    articles_data = [
        {
            "title": a.title,
            "author": a.author,
            "platform": a.platform,
            "keyword": a.keyword,
            "sentiment": a.sentiment,
            "url": a.url,
        }
        for a in unique[:20]
    ]
    
    # 更新全局结果
    _latest_crawl_result = {
        "total": len(unique),
        "articles": articles_data,
        "sentiment_stats": sentiment_stats,
        "keyword_stats": {},
        "crawled_at": datetime.now().isoformat(),
        "task_id": None,
        "_article_objects": unique,
    }
    
    return {
        "total": len(unique),
        "articles": articles_data[:10],
        "sentiment_stats": sentiment_stats,
    }


@router.get("/latest")
async def get_latest_crawl():
    """获取最近一次采集结果（供首页和日报页面使用）"""
    if _latest_crawl_result["total"] == 0:
        return {"total": 0, "articles": [], "sentiment_stats": {}, "crawled_at": None}
    
    return {
        "total": _latest_crawl_result["total"],
        "articles": _latest_crawl_result["articles"],
        "sentiment_stats": _latest_crawl_result["sentiment_stats"],
        "keyword_stats": _latest_crawl_result.get("keyword_stats", {}),
        "crawled_at": _latest_crawl_result["crawled_at"],
        "task_id": _latest_crawl_result.get("task_id"),
    }
