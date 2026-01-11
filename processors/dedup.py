"""
去重处理器
用于对采集的文章进行去重
"""
import hashlib
from typing import List, Set
from crawlers.base import Article

# 导入路径管理（缓存文件在未来可能需要持久化）
try:
    from path_manager import DEDUP_CACHE_FILE
except ImportError:
    DEDUP_CACHE_FILE = None


class DedupProcessor:
    """去重处理器"""
    
    def __init__(self, cache_file: str = None):
        """
        初始化去重处理器
        
        Args:
            cache_file: 缓存文件路径（未来功能）
        """
        self.seen_urls: Set[str] = set()
        self.seen_hashes: Set[str] = set()
        self.cache_file = cache_file or (str(DEDUP_CACHE_FILE) if DEDUP_CACHE_FILE else None)
    
    def _get_content_hash(self, article: Article) -> str:
        """基于内容生成哈希"""
        content = f"{article.title}|{article.author}|{article.platform}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _get_url_hash(self, url: str) -> str:
        """基于URL生成哈希"""
        return hashlib.md5(url.encode()).hexdigest()
    
    def deduplicate(self, articles: List[Article]) -> List[Article]:
        """
        对文章列表进行去重
        
        Args:
            articles: 文章列表
            
        Returns:
            去重后的文章列表
        """
        unique_articles = []
        
        for article in articles:
            # 基于URL去重
            url_hash = self._get_url_hash(article.url)
            if url_hash in self.seen_urls:
                continue
            
            # 基于内容去重（防止相同内容不同URL的情况）
            content_hash = self._get_content_hash(article)
            if content_hash in self.seen_hashes:
                continue
            
            self.seen_urls.add(url_hash)
            self.seen_hashes.add(content_hash)
            unique_articles.append(article)
        
        return unique_articles
    
    def reset(self):
        """重置去重状态"""
        self.seen_urls.clear()
        self.seen_hashes.clear()





