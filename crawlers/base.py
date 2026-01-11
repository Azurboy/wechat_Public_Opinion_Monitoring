"""
爬虫基类
定义所有爬虫的通用接口和方法
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class Article:
    """文章/帖子数据模型"""
    title: str                          # 标题
    author: str                         # 作者/公众号名称
    content: str                        # 内容摘要
    url: str                            # 原文链接
    platform: str                       # 平台来源
    keyword: str                        # 匹配的关键词
    published_at: Optional[datetime] = None  # 发布时间
    crawled_at: datetime = field(default_factory=datetime.now)  # 采集时间
    sentiment: Optional[str] = None     # 情感标注（积极/消极/中立）
    sentiment_score: Optional[float] = None  # 情感分数
    likes: int = 0                      # 点赞数
    comments: int = 0                   # 评论数
    shares: int = 0                     # 转发/分享数
    
    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "title": self.title,
            "author": self.author,
            "content": self.content,
            "url": self.url,
            "platform": self.platform,
            "keyword": self.keyword,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "crawled_at": self.crawled_at.isoformat(),
            "sentiment": self.sentiment,
            "sentiment_score": self.sentiment_score,
            "likes": self.likes,
            "comments": self.comments,
            "shares": self.shares,
        }


class BaseCrawler(ABC):
    """爬虫基类"""
    
    def __init__(self, request_delay: float = 3.0):
        """
        初始化爬虫
        
        Args:
            request_delay: 请求间隔（秒），用于控制爬取速度
        """
        self.request_delay = request_delay
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @property
    @abstractmethod
    def platform_name(self) -> str:
        """平台名称"""
        pass
    
    @abstractmethod
    def search(self, keyword: str, max_pages: int = 3) -> List[Article]:
        """
        搜索关键词
        
        Args:
            keyword: 搜索关键词
            max_pages: 最大搜索页数
            
        Returns:
            文章列表
        """
        pass
    
    def search_multiple(self, keywords: List[str], max_pages: int = 3) -> List[Article]:
        """
        搜索多个关键词
        
        Args:
            keywords: 关键词列表
            max_pages: 每个关键词的最大搜索页数
            
        Returns:
            所有文章列表（已去重）
        """
        all_articles = []
        seen_urls = set()
        
        for keyword in keywords:
            self.logger.info(f"正在搜索关键词: {keyword}")
            try:
                articles = self.search(keyword, max_pages)
                for article in articles:
                    if article.url not in seen_urls:
                        seen_urls.add(article.url)
                        all_articles.append(article)
                        
                # 关键词之间的间隔
                time.sleep(self.request_delay)
                
            except Exception as e:
                self.logger.error(f"搜索关键词 '{keyword}' 时出错: {e}")
                continue
        
        self.logger.info(f"共采集到 {len(all_articles)} 条不重复内容")
        return all_articles
    
    def _sleep(self):
        """请求间隔"""
        time.sleep(self.request_delay)




