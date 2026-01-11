"""
搜狗微信搜索爬虫
通过搜狗微信搜索获取公众号文章
"""
import re
import time
import random
from datetime import datetime
from typing import List, Optional
from urllib.parse import quote, urljoin

import requests
from bs4 import BeautifulSoup

from .base import BaseCrawler, Article


class SogouWechatCrawler(BaseCrawler):
    """搜狗微信搜索爬虫"""
    
    BASE_URL = "https://weixin.sogou.com"
    SEARCH_URL = "https://weixin.sogou.com/weixin"
    
    # 请求头，模拟浏览器
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Referer": "https://weixin.sogou.com/",
    }
    
    def __init__(self, request_delay: float = 3.0):
        """
        初始化搜狗微信爬虫
        
        Args:
            request_delay: 请求间隔（秒）
        """
        super().__init__(request_delay)
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)
        # 访问首页获取cookies
        self._init_session()
    
    def _init_session(self):
        """初始化session，获取必要的cookies"""
        try:
            self.session.get(self.BASE_URL, timeout=10)
            self.logger.info("Session初始化成功")
        except Exception as e:
            self.logger.warning(f"Session初始化失败: {e}")
    
    @property
    def platform_name(self) -> str:
        return "微信公众号"
    
    def search(self, keyword: str, max_pages: int = 3) -> List[Article]:
        """
        搜索关键词
        
        Args:
            keyword: 搜索关键词
            max_pages: 最大搜索页数
            
        Returns:
            文章列表
        """
        articles = []
        
        for page in range(1, max_pages + 1):
            self.logger.info(f"正在搜索 '{keyword}' 第 {page} 页")
            
            try:
                page_articles = self._search_page(keyword, page)
                if not page_articles:
                    self.logger.info(f"第 {page} 页没有更多结果")
                    break
                    
                articles.extend(page_articles)
                self.logger.info(f"第 {page} 页获取到 {len(page_articles)} 篇文章")
                
                # 页面之间的间隔，添加随机因子避免被封
                if page < max_pages:
                    delay = self.request_delay + random.uniform(0.5, 1.5)
                    time.sleep(delay)
                    
            except Exception as e:
                self.logger.error(f"搜索第 {page} 页时出错: {e}")
                break
        
        return articles
    
    def _search_page(self, keyword: str, page: int = 1) -> List[Article]:
        """搜索单页"""
        params = {
            "type": "2",      # 2表示搜索文章
            "query": keyword,
            "page": page,
            # 注意：搜狗微信搜索不支持按时间排序，需要在爬取后使用时间过滤器
        }
        
        try:
            response = self.session.get(
                self.SEARCH_URL,
                params=params,
                timeout=15
            )
            response.raise_for_status()
            
            # 检查是否需要验证码
            if "antispider" in response.url or "验证" in response.text:
                self.logger.warning("触发反爬机制，需要手动输入验证码")
                self.logger.warning(f"请访问: {response.url}")
                return []
            
            return self._parse_search_results(response.text, keyword)
            
        except requests.RequestException as e:
            self.logger.error(f"请求失败: {e}")
            return []
    
    def _parse_search_results(self, html: str, keyword: str) -> List[Article]:
        """解析搜索结果页面"""
        articles = []
        soup = BeautifulSoup(html, 'lxml')
        
        # 搜狗微信搜索结果的文章列表
        news_list = soup.select('ul.news-list > li')
        
        if not news_list:
            # 尝试其他选择器
            news_list = soup.select('div.txt-box')
        
        for item in news_list:
            try:
                article = self._parse_article_item(item, keyword)
                if article:
                    articles.append(article)
            except Exception as e:
                self.logger.debug(f"解析文章失败: {e}")
                continue
        
        return articles
    
    def _parse_article_item(self, item, keyword: str) -> Optional[Article]:
        """解析单个文章项"""
        # 标题和链接
        title_elem = item.select_one('h3 a') or item.select_one('a.tit')
        if not title_elem:
            return None
        
        title = title_elem.get_text(strip=True)
        # 搜狗返回的是加密链接，需要访问后重定向到真实微信文章
        href = title_elem.get('href', '')
        if href and not href.startswith('http'):
            href = urljoin(self.BASE_URL, href)
        
        # 公众号名称（尝试多种选择器）
        author = self._extract_author(item)
        
        # 摘要内容
        content_elem = item.select_one('p.txt-info') or item.select_one('p.content')
        content = content_elem.get_text(strip=True) if content_elem else ""
        
        # 发布时间（尝试多种选择器）
        published_at = self._extract_publish_time(item)
        
        # 只有标题存在时才返回
        if not title:
            return None
        
        return Article(
            title=title,
            author=author,
            content=content,
            url=href,
            platform=self.platform_name,
            keyword=keyword,
            published_at=published_at,
        )
    
    def _extract_author(self, item) -> str:
        """提取公众号名称，尝试多种CSS选择器"""
        # 按优先级尝试不同的选择器
        selectors = [
            'a.account',              # 最常见的公众号链接
            'div.s-p a:first-of-type',   # s-p区域的第一个链接（更精确）
            'p.s-p a:first-of-type',     # 可能在p标签内
            '.account',               # 任意account类
            'a[uigs*="account"]',     # 带account属性的链接
            'div.s-p a',              # s-p区域的任意链接
            'span.all-time-y2',       # 时间旁边可能有公众号名
            'a[data-z]',              # 带data-z属性的链接
        ]
        
        for selector in selectors:
            elem = item.select_one(selector)
            if elem:
                text = elem.get_text(strip=True)
                # 过滤掉明显不是公众号名称的内容
                if text and not self._is_time_string(text) and len(text) < 50:
                    self.logger.debug(f"找到作者: {text} (选择器: {selector})")
                    return text
        
        return "未知公众号"
    
    def _is_time_string(self, text: str) -> bool:
        """判断字符串是否为时间格式"""
        time_patterns = ['小时前', '天前', '分钟前', '秒前', '年', '月', '日', '-']
        return any(p in text for p in time_patterns)
    
    def _extract_publish_time(self, item) -> Optional[datetime]:
        """提取发布时间，尝试多种CSS选择器"""
        selectors = [
            'span.s2',             # 常见的时间选择器
            'div.s-p span:last-child',  # s-p区域最后一个span
            'span.time',           # 时间类
            'span[data-lastmodified]',  # 带时间戳属性
        ]
        
        for selector in selectors:
            elem = item.select_one(selector)
            if elem:
                time_str = elem.get_text(strip=True)
                parsed = self._parse_time(time_str)
                if parsed:
                    return parsed
        
        return None
    
    def _parse_time(self, time_str: str) -> Optional[datetime]:
        """解析时间字符串，支持多种格式"""
        if not time_str:
            return None
        
        from datetime import timedelta
        now = datetime.now()
        
        try:
            # 相对时间格式
            if "秒前" in time_str:
                match = re.search(r'(\d+)', time_str)
                if match:
                    seconds = int(match.group(1))
                    return now - timedelta(seconds=seconds)
            elif "分钟前" in time_str:
                match = re.search(r'(\d+)', time_str)
                if match:
                    minutes = int(match.group(1))
                    return now - timedelta(minutes=minutes)
            elif "小时前" in time_str:
                match = re.search(r'(\d+)', time_str)
                if match:
                    hours = int(match.group(1))
                    return now - timedelta(hours=hours)
            elif "天前" in time_str:
                match = re.search(r'(\d+)', time_str)
                if match:
                    days = int(match.group(1))
                    return now - timedelta(days=days)
            elif "昨天" in time_str:
                return now - timedelta(days=1)
            elif "前天" in time_str:
                return now - timedelta(days=2)
            else:
                # 绝对日期格式
                formats = [
                    "%Y-%m-%d",
                    "%Y年%m月%d日",
                    "%Y/%m/%d",
                    "%m-%d",
                    "%m月%d日",
                ]
                for fmt in formats:
                    try:
                        parsed = datetime.strptime(time_str.strip(), fmt)
                        # 对于只有月日的格式，补上当前年份
                        if fmt in ["%m-%d", "%m月%d日"]:
                            parsed = parsed.replace(year=now.year)
                        return parsed
                    except ValueError:
                        continue
        except Exception as e:
            self.logger.debug(f"时间解析失败: {time_str}, 错误: {e}")
        
        return None
    
    def get_real_url(self, sogou_url: str) -> Optional[str]:
        """
        获取真实的微信文章URL
        搜狗返回的是加密链接，需要通过重定向获取真实URL
        
        Args:
            sogou_url: 搜狗返回的加密链接
            
        Returns:
            真实的微信文章URL
        """
        try:
            response = self.session.get(sogou_url, allow_redirects=False, timeout=10)
            if response.status_code in [301, 302]:
                return response.headers.get('Location')
            return sogou_url
        except Exception as e:
            self.logger.error(f"获取真实URL失败: {e}")
            return sogou_url


# 测试代码
if __name__ == "__main__":
    import yaml
    
    # 加载关键词配置
    with open("config/keywords.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    
    keywords = config.get("keywords", [])
    search_config = config.get("search", {})
    
    # 创建爬虫实例
    crawler = SogouWechatCrawler(
        request_delay=search_config.get("request_delay", 3)
    )
    
    # 搜索所有关键词
    articles = crawler.search_multiple(
        keywords,
        max_pages=search_config.get("max_pages", 3)
    )
    
    # 输出结果
    print(f"\n{'='*60}")
    print(f"共采集到 {len(articles)} 篇文章")
    print(f"{'='*60}\n")
    
    for i, article in enumerate(articles, 1):
        print(f"[{i}] {article.title}")
        print(f"    公众号: {article.author}")
        print(f"    关键词: {article.keyword}")
        print(f"    时间: {article.published_at}")
        print(f"    链接: {article.url[:80]}...")
        print()

