"""
微信公众号平台爬虫
通过微信公众号平台网页版获取文章
需要用户登录获取cookie，支持按时间排序
"""
import json
import os
import re
import time
from datetime import datetime, timedelta
from typing import List, Optional, Callable
from pathlib import Path
import logging

from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext

from .base import BaseCrawler, Article

# 导入路径管理
try:
    from path_manager import WECHAT_MP_COOKIE
except ImportError:
    # 开发环境回退
    WECHAT_MP_COOKIE = None

logging.basicConfig(level=logging.INFO)


class WechatMPCrawler(BaseCrawler):
    """
    微信公众号平台爬虫
    
    特点：
    - 需要登录微信公众号平台
    - 支持按时间排序
    - 实时性高
    - 需要扫码登录
    """
    
    BASE_URL = "https://mp.weixin.qq.com"
    SEARCH_URL = "https://mp.weixin.qq.com/cgi-bin/searchbiz"
    
    def __init__(
        self,
        request_delay: float = 3.0,
        headless: bool = True,
        cookie_file: str = None,
        data_dir: str = None
    ):
        """
        初始化微信公众号平台爬虫
        
        Args:
            request_delay: 请求间隔（秒）
            headless: 是否无头模式
            cookie_file: cookie文件路径
            data_dir: 数据目录（已弃用，使用path_manager）
        """
        super().__init__(request_delay)
        self.headless = headless
        
        # 使用新的路径管理系统
        if cookie_file:
            self.cookie_file = cookie_file
        elif WECHAT_MP_COOKIE:
            self.cookie_file = str(WECHAT_MP_COOKIE)
        else:
            # 回退到旧的data_dir方式
            self.data_dir = Path(data_dir or "data")
            self.data_dir.mkdir(parents=True, exist_ok=True)
            self.cookie_file = str(self.data_dir / "wechat_mp_cookies.json")
        
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self._playwright = None
        
        self._logged_in = False
    
    @property
    def platform_name(self) -> str:
        return "微信公众号"
    
    def _init_browser(self, headless: bool = None):
        """初始化浏览器"""
        if self.browser:
            return
        
        use_headless = headless if headless is not None else self.headless
        
        try:
            self._playwright = sync_playwright().start()
            self.browser = self._playwright.chromium.launch(
                headless=use_headless,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                ]
            )
            
            self.context = self.browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 800},
                locale="zh-CN",
            )
            
            # 加载cookies
            self._load_cookies()
            
            self.page = self.context.new_page()
        except Exception as e:
            raise
    
    def _close_browser(self):
        """关闭浏览器"""
        if hasattr(self, 'page') and self.page:
            self.page.close()
            self.page = None
        if hasattr(self, 'context') and self.context:
            self.context.close()
            self.context = None
        if hasattr(self, 'browser') and self.browser:
            self.browser.close()
            self.browser = None
        if hasattr(self, '_playwright') and self._playwright:
            self._playwright.stop()
            self._playwright = None
    
    def _load_cookies(self) -> bool:
        """加载Cookies"""
        if not self.context:
            return False
        
        try:
            if os.path.exists(self.cookie_file):
                with open(self.cookie_file, 'r', encoding='utf-8') as f:
                    cookies = json.load(f)
                self.context.add_cookies(cookies)
                self.logger.info(f"已加载微信公众号Cookies")
                self._logged_in = True
                return True
        except Exception as e:
            self.logger.warning(f"加载Cookies失败: {e}")
        
        return False
    
    def save_cookies(self):
        """保存Cookies"""
        if not self.context:
            return
        
        try:
            cookies = self.context.cookies()
            with open(self.cookie_file, 'w', encoding='utf-8') as f:
                json.dump(cookies, f, ensure_ascii=False, indent=2)
            self.logger.info(f"Cookies已保存: {self.cookie_file}")
        except Exception as e:
            self.logger.error(f"保存Cookies失败: {e}")
    
    def is_logged_in(self) -> bool:
        """检查是否已登录"""
        # 如果已经标记为登录，直接返回
        if self._logged_in:
            return True
        
        # 否则检查cookie文件是否存在
        if os.path.exists(self.cookie_file):
            # 尝试加载cookies
            if not self.browser:
                self._init_browser()
            if self._load_cookies():
                return True
        
        return False
    
    def login_by_qrcode(self, callback: Callable[[str], None] = None, timeout: int = 120) -> bool:
        """
        扫码登录微信公众号平台
        
        Args:
            callback: 二维码图片回调（用于Web端展示）
            timeout: 超时时间（秒）
            
        Returns:
            是否登录成功
        """
        self._close_browser()
        
        try:
            self._init_browser(headless=False)
        except Exception as e:
            self.logger.error(f"微信公众号平台登录失败: {e}")
            return False
        
        try:
            # 访问公众号平台
            self.page.goto(self.BASE_URL, wait_until="networkidle", timeout=30000)
            time.sleep(2)
            
            # 检查是否已登录
            if self._check_login_status():
                self.logger.info("已处于登录状态")
                self.save_cookies()
                self._logged_in = True
                return True
            
            self.logger.info("="*50)
            self.logger.info("请使用微信扫描二维码登录公众号平台")
            self.logger.info(f"等待登录（超时: {timeout}秒）...")
            self.logger.info("="*50)
            
            # 等待二维码
            try:
                qr_selector = 'img.login__type__container__scan__qrcode, img[class*="qrcode"]'
                self.page.wait_for_selector(qr_selector, timeout=10000)
                
                if callback:
                    qr_elem = self.page.query_selector(qr_selector)
                    if qr_elem:
                        qr_url = qr_elem.get_attribute('src')
                        if qr_url:
                            callback(qr_url)
            except Exception:
                self.logger.info("等待用户扫码...")
            
            # 等待登录成功
            start_time = time.time()
            while time.time() - start_time < timeout:
                if self._check_login_status():
                    self.logger.info("登录成功！")
                    self.save_cookies()
                    self._logged_in = True
                    return True
                time.sleep(2)
            
            self.logger.error("登录超时")
            return False
            
        except Exception as e:
            self.logger.error(f"登录失败: {e}")
            return False
        finally:
            if self._logged_in:
                self._close_browser()
    
    def _check_login_status(self) -> bool:
        """检查登录状态"""
        try:
            # 检查URL是否包含首页特征
            if "/cgi-bin/home" in self.page.url:
                return True
            
            # 检查是否有用户头像
            user_selectors = [
                '.weui-desktop-account__nickname',
                '.account__header__info',
                '[class*="nickname"]',
            ]
            
            for selector in user_selectors:
                elem = self.page.query_selector(selector)
                if elem:
                    return True
            
            return False
            
        except Exception:
            return False
    
    def search(
        self,
        keyword: str,
        max_pages: int = 3,
        sort_by_time: bool = True,
        filter_hours: int = None
    ) -> List[Article]:
        """
        搜索公众号文章
        
        Args:
            keyword: 搜索关键词
            max_pages: 最大页数
            sort_by_time: 是否按时间排序
            filter_hours: 只获取N小时内的文章
            
        Returns:
            文章列表
        """
        if not self.is_logged_in():
            self.logger.warning("未登录，请先执行扫码登录")
            return []
        
        self._init_browser()
        articles = []
        
        try:
            # 访问素材搜索页面
            # 注意：微信公众号平台的搜索功能需要登录
            search_url = f"{self.BASE_URL}/cgi-bin/appmsg?action=list_ex&begin=0&count=5&fakeid=&type=9&query={keyword}&token="
            
            # 先访问首页获取token
            self.page.goto(f"{self.BASE_URL}/cgi-bin/home", wait_until="networkidle", timeout=30000)
            time.sleep(2)
            
            # 使用搜一搜功能搜索全网文章
            # 进入搜一搜
            search_entry = self.page.query_selector('a[href*="websearch"], .search-icon, [class*="search"]')
            if search_entry:
                search_entry.click()
                time.sleep(1)
            
            # 由于微信公众号后台的搜索主要是搜索自己的文章
            # 这里我们使用备用方案：通过搜狗微信搜索
            # 或者使用微信读书等渠道
            
            # 这是一个简化实现，实际使用时可能需要更复杂的逻辑
            self.logger.info(f"搜索关键词: {keyword}")
            
            # 尝试使用微信搜一搜
            # sort=1 表示按时间排序（最新优先）
            sort_param = "&sort=1" if sort_by_time else ""
            sogou_url = f"https://weixin.sogou.com/weixin?type=2&query={keyword}{sort_param}"
            self.logger.info(f"搜索URL: {sogou_url} (按时间排序: {sort_by_time})")
            self.page.goto(sogou_url, wait_until="networkidle", timeout=30000)
            time.sleep(2)
            
            for page_num in range(max_pages):
                self.logger.info(f"正在采集第 {page_num + 1} 页...")
                
                page_articles = self._parse_search_results(keyword)
                
                existing_urls = {a.url for a in articles}
                new_count = 0
                for article in page_articles:
                    if article.url not in existing_urls:
                        articles.append(article)
                        new_count += 1
                
                self.logger.info(f"本页新增 {new_count} 篇，共 {len(articles)} 篇")
                
                # 翻页
                next_btn = self.page.query_selector('a#sogou_next, .p-next, a:has-text("下一页")')
                if next_btn and page_num < max_pages - 1:
                    next_btn.click()
                    time.sleep(self.request_delay)
                else:
                    break
            
            # 时间过滤
            if filter_hours and filter_hours > 0:
                cutoff = datetime.now() - timedelta(hours=filter_hours)
                before = len(articles)
                articles = [a for a in articles if not a.published_at or a.published_at > cutoff]
                self.logger.info(f"时间过滤: {before} -> {len(articles)}")
            
        except Exception as e:
            self.logger.error(f"搜索失败: {e}")
        
        return articles
    
    def _parse_search_results(self, keyword: str) -> List[Article]:
        """解析搜索结果"""
        articles = []
        
        try:
            # 搜狗微信搜索结果
            items = self.page.query_selector_all('ul.news-list > li, div.txt-box')
            
            for item in items:
                try:
                    # 标题
                    title_elem = item.query_selector('h3 a, a.tit')
                    if not title_elem:
                        continue
                    
                    title = title_elem.inner_text().strip()
                    href = title_elem.get_attribute('href') or ""
                    
                    if href and not href.startswith('http'):
                        href = f"https://weixin.sogou.com{href}"
                    
                    # 作者 - 尝试多种选择器
                    author = "未知公众号"
                    author_selectors = [
                        'a.account',           # 公众号链接
                        'div.s-p a:first-of-type',  # s-p区域的第一个链接
                        'p.s-p a',            # 可能在p标签内
                        '.account',           # 任意标签的account类
                        'a[uigs*="account"]', # 带account属性的链接
                    ]
                    
                    for sel in author_selectors:
                        author_elem = item.query_selector(sel)
                        if author_elem:
                            author_text = author_elem.inner_text().strip()
                            if author_text and author_text != "" and len(author_text) < 50:
                                author = author_text
                                self.logger.debug(f"找到作者: {author} (选择器: {sel})")
                                break
                    
                    # 摘要
                    content_elem = item.query_selector('p.txt-info, p.content')
                    content = content_elem.inner_text().strip() if content_elem else ""
                    
                    # 时间 - 尝试多种选择器
                    time_elem = None
                    time_selectors = [
                        'span.s2',           # 搜狗旧版
                        'div.s-p span',      # 搜狗新版
                        'span.time',         # 通用
                        'span[class*="time"]',
                        '.s-p > span:last-child',  # 时间通常在最后
                    ]
                    for sel in time_selectors:
                        time_elem = item.query_selector(sel)
                        if time_elem:
                            break
                    
                    published_at = None
                    if time_elem:
                        time_text = time_elem.inner_text().strip()
                        published_at = self._parse_time(time_text)
                        if published_at:
                            self.logger.debug(f"解析时间: '{time_text}' -> {published_at}")
                    
                    if title:
                        articles.append(Article(
                            title=title,
                            author=author,
                            content=content,
                            url=href,
                            platform=self.platform_name,
                            keyword=keyword,
                            published_at=published_at,
                        ))
                        
                except Exception as e:
                    self.logger.debug(f"解析文章失败: {e}")
                    continue
            
        except Exception as e:
            self.logger.error(f"解析结果失败: {e}")
        
        return articles
    
    def _parse_time(self, time_str: str) -> Optional[datetime]:
        """
        解析时间字符串
        
        支持的格式：
        - "刚刚"
        - "X分钟前"
        - "X小时前"
        - "X天前"
        - "昨天"
        - "前天"
        - "YYYY-MM-DD"
        - "YYYY年MM月DD日"
        - "MM-DD"
        - "MM月DD日"
        """
        if not time_str:
            return None
        
        time_str = time_str.strip()
        now = datetime.now()
        
        try:
            # 刚刚
            if "刚刚" in time_str or "刚发布" in time_str:
                return now
            
            # X分钟前
            if "分钟前" in time_str:
                match = re.search(r'(\d+)', time_str)
                if match:
                    minutes = int(match.group(1))
                    return now - timedelta(minutes=minutes)
            
            # X小时前
            if "小时前" in time_str:
                match = re.search(r'(\d+)', time_str)
                if match:
                    hours = int(match.group(1))
                    return now - timedelta(hours=hours)
            
            # X天前
            if "天前" in time_str:
                match = re.search(r'(\d+)', time_str)
                if match:
                    days = int(match.group(1))
                    return now - timedelta(days=days)
            
            # 昨天
            if "昨天" in time_str:
                return now - timedelta(days=1)
            
            # 前天
            if "前天" in time_str:
                return now - timedelta(days=2)
            
            # 尝试解析日期格式
            date_formats = [
                "%Y-%m-%d",        # 2026-01-10
                "%Y年%m月%d日",     # 2026年01月10日
                "%Y/%m/%d",        # 2026/01/10
                "%m-%d",           # 01-10
                "%m月%d日",         # 01月10日
            ]
            
            for fmt in date_formats:
                try:
                    parsed = datetime.strptime(time_str, fmt)
                    # 如果只有月-日，添加当前年份
                    if fmt in ["%m-%d", "%m月%d日"]:
                        parsed = parsed.replace(year=now.year)
                        # 如果解析出的日期在未来，说明是去年的
                        if parsed > now:
                            parsed = parsed.replace(year=now.year - 1)
                    return parsed
                except ValueError:
                    continue
            
            # 尝试从字符串中提取日期
            date_match = re.search(r'(\d{4})[年/-](\d{1,2})[月/-](\d{1,2})', time_str)
            if date_match:
                year, month, day = int(date_match.group(1)), int(date_match.group(2)), int(date_match.group(3))
                return datetime(year, month, day)
            
            # 只有月日的情况
            date_match = re.search(r'(\d{1,2})[月/-](\d{1,2})', time_str)
            if date_match:
                month, day = int(date_match.group(1)), int(date_match.group(2))
                result = datetime(now.year, month, day)
                if result > now:
                    result = result.replace(year=now.year - 1)
                return result
                
        except Exception as e:
            self.logger.debug(f"时间解析失败: '{time_str}' - {e}")
        
        return None
        
        return None
    
    def __del__(self):
        """析构时关闭浏览器"""
        self._close_browser()


# 测试代码
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="微信公众号平台爬虫")
    parser.add_argument("--login", action="store_true", help="扫码登录")
    parser.add_argument("--keyword", "-k", default="Monolith", help="搜索关键词")
    parser.add_argument("--pages", "-p", type=int, default=2, help="搜索页数")
    args = parser.parse_args()
    
    crawler = WechatMPCrawler(headless=False)
    
    if args.login:
        success = crawler.login_by_qrcode()
        print(f"登录{'成功' if success else '失败'}")
    else:
        articles = crawler.search(args.keyword, max_pages=args.pages)
        print(f"\n采集到 {len(articles)} 篇文章:")
        for i, article in enumerate(articles[:10], 1):
            print(f"[{i}] {article.title}")
            print(f"    作者: {article.author}")
            print(f"    链接: {article.url}")
            print()


