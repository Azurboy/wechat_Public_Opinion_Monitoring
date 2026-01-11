"""
小红书爬虫
通过Playwright模拟浏览器获取小红书关键词搜索结果
支持：按时间排序、扫码登录、Cookie持久化
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

logging.basicConfig(level=logging.INFO)


class XHSCrawler(BaseCrawler):
    """小红书爬虫（支持扫码登录、按时间排序）"""
    
    BASE_URL = "https://www.xiaohongshu.com"
    SEARCH_URL = "https://www.xiaohongshu.com/search_result"
    
    # 排序方式
    SORT_GENERAL = "general"      # 综合排序（默认）
    SORT_TIME = "time_descending" # 最新排序
    SORT_POPULAR = "popularity_descending"  # 最热排序
    
    def __init__(
        self, 
        request_delay: float = 3.0, 
        headless: bool = True, 
        cookie_file: str = None,
        data_dir: str = None
    ):
        """
        初始化小红书爬虫
        
        Args:
            request_delay: 请求间隔（秒）
            headless: 是否无头模式运行浏览器
            cookie_file: cookie文件路径
            data_dir: 数据目录（存储cookies等）
        """
        super().__init__(request_delay)
        self.headless = headless
        
        # 数据目录
        self.data_dir = Path(data_dir or "data")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.cookie_file = cookie_file or str(self.data_dir / "xhs_cookies.json")
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self._playwright = None
        
        self._logged_in = False
    
    @property
    def platform_name(self) -> str:
        return "小红书"
    
    def _init_browser(self, headless: bool = None):
        """初始化浏览器"""
        if self.browser:
            return
        
        use_headless = headless if headless is not None else self.headless
        
        self._playwright = sync_playwright().start()
        self.browser = self._playwright.chromium.launch(
            headless=use_headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-dev-shm-usage',
            ]
        )
        
        # 创建带有用户代理的上下文
        self.context = self.browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
            locale="zh-CN",
        )
        
        # 尝试加载cookies
        self._load_cookies()
        
        self.page = self.context.new_page()
        
        # 设置额外的头信息
        self.page.set_extra_http_headers({
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        })
        
        # 注入反检测脚本
        self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
    
    def _close_browser(self):
        """关闭浏览器"""
        if self.page:
            self.page.close()
            self.page = None
        if self.context:
            self.context.close()
            self.context = None
        if self.browser:
            self.browser.close()
            self.browser = None
        if self._playwright:
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
                self.logger.info(f"已加载Cookies: {len(cookies)} 条")
                self._logged_in = True
                return True
        except Exception as e:
            self.logger.warning(f"加载Cookies失败: {e}")
        
        return False
    
    def save_cookies(self):
        """保存Cookies到文件"""
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
        return self._logged_in and os.path.exists(self.cookie_file)
    
    def login_by_qrcode(self, callback: Callable[[str], None] = None, timeout: int = 120) -> bool:
        """
        扫码登录
        
        Args:
            callback: 二维码URL回调函数（用于Web端展示）
            timeout: 超时时间（秒）
            
        Returns:
            是否登录成功
        """
        self._close_browser()  # 确保干净启动
        self._init_browser(headless=False)  # 非无头模式
        
        try:
            # 访问登录页面
            self.page.goto(f"{self.BASE_URL}/explore", wait_until="networkidle", timeout=30000)
            time.sleep(2)
            
            # 检查是否已经登录
            if self._check_login_status():
                self.logger.info("已处于登录状态")
                self.save_cookies()
                self._logged_in = True
                return True
            
            # 点击登录按钮
            login_btn = self.page.query_selector('div.login-btn, .login, [class*="login"]')
            if login_btn:
                login_btn.click()
                time.sleep(1)
            
            # 等待二维码出现
            self.logger.info("等待二维码出现...")
            qr_selector = 'img[class*="qrcode"], img[src*="qrcode"], canvas.qrcode, div.qrcode img'
            
            try:
                self.page.wait_for_selector(qr_selector, timeout=10000)
            except Exception:
                self.logger.warning("未找到二维码元素，可能需要手动操作")
            
            # 获取二维码图片URL（如果有callback的话）
            if callback:
                try:
                    qr_elem = self.page.query_selector(qr_selector)
                    if qr_elem:
                        qr_url = qr_elem.get_attribute('src')
                        if qr_url:
                            callback(qr_url)
                except Exception:
                    pass
            
            self.logger.info("="*50)
            self.logger.info("请使用小红书APP扫描二维码登录")
            self.logger.info(f"等待登录（超时: {timeout}秒）...")
            self.logger.info("="*50)
            
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
            self.logger.error(f"扫码登录失败: {e}")
            return False
        finally:
            if self._logged_in:
                self._close_browser()
    
    def _check_login_status(self) -> bool:
        """检查当前页面是否已登录"""
        try:
            # 检查是否有用户头像或个人中心入口
            user_selectors = [
                'div.user-avatar',
                'img.user-avatar',
                '[class*="avatar"]',
                '[class*="user-info"]',
                'a[href*="/user/profile"]',
            ]
            
            for selector in user_selectors:
                elem = self.page.query_selector(selector)
                if elem:
                    return True
            
            # 检查URL是否包含登录相关
            if "login" in self.page.url.lower():
                return False
            
            # 检查是否有登录按钮（如果有说明未登录）
            login_btn = self.page.query_selector('div.login-btn:visible, .login-container:visible')
            if login_btn:
                return False
            
            # 通过cookie判断
            cookies = self.context.cookies()
            login_cookies = [c for c in cookies if c.get('name') in ['user_id', 'customerClientId', 'xhsTrackerId']]
            return len(login_cookies) > 0
            
        except Exception:
            return False
    
    def search(
        self, 
        keyword: str, 
        max_pages: int = 3, 
        sort: str = None,
        filter_hours: int = None
    ) -> List[Article]:
        """
        搜索关键词
        
        Args:
            keyword: 搜索关键词
            max_pages: 最大滚动次数
            sort: 排序方式 (general/time_descending/popularity_descending)
            filter_hours: 只返回N小时内的内容（可选）
            
        Returns:
            文章列表
        """
        self._init_browser()
        articles = []
        sort = sort or self.SORT_TIME  # 默认按时间排序
        
        try:
            # 构建搜索URL
            search_url = f"{self.SEARCH_URL}?keyword={keyword}&source=web_search_result_notes"
            if sort and sort != self.SORT_GENERAL:
                search_url += f"&sort={sort}"
            
            self.logger.info(f"搜索: {keyword} (排序: {sort})")
            self.page.goto(search_url, wait_until="networkidle", timeout=30000)
            time.sleep(2)
            
            # 检查是否需要登录
            if "login" in self.page.url.lower():
                self.logger.warning("需要登录，请先运行扫码登录")
                return []
            
            # 如果有排序选项，尝试点击排序按钮
            if sort == self.SORT_TIME:
                self._click_sort_by_time()
            
            # 滚动加载
            for i in range(max_pages):
                self.logger.info(f"正在采集第 {i + 1}/{max_pages} 批数据...")
                
                # 解析当前页面
                page_articles = self._parse_notes(keyword)
                
                # 去重添加
                existing_urls = {a.url for a in articles}
                new_count = 0
                for article in page_articles:
                    if article.url not in existing_urls:
                        articles.append(article)
                        existing_urls.add(article.url)
                        new_count += 1
                
                self.logger.info(f"本批新增 {new_count} 条，共 {len(articles)} 条")
                
                # 如果没有新内容，可能已经到底
                if new_count == 0 and i > 0:
                    self.logger.info("没有更多新内容")
                    break
                
                # 滚动到底部
                self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(self.request_delay)
            
            # 时间过滤
            if filter_hours and filter_hours > 0:
                cutoff = datetime.now() - timedelta(hours=filter_hours)
                before_count = len(articles)
                articles = [a for a in articles if not a.published_at or a.published_at > cutoff]
                self.logger.info(f"时间过滤: {before_count} -> {len(articles)} 条 ({filter_hours}小时内)")
            
        except Exception as e:
            self.logger.error(f"搜索出错: {e}")
        
        return articles
    
    def _click_sort_by_time(self):
        """点击按时间排序"""
        try:
            # 小红书的排序按钮
            sort_selectors = [
                'div[class*="sort"] span:has-text("最新")',
                'span:has-text("最新")',
                'div.filter-item:has-text("最新")',
                '[data-sort="time"]',
            ]
            
            for selector in sort_selectors:
                try:
                    elem = self.page.query_selector(selector)
                    if elem:
                        elem.click()
                        self.logger.info("已切换到最新排序")
                        time.sleep(1)
                        return True
                except Exception:
                    continue
            
            self.logger.debug("未找到排序按钮，使用URL参数排序")
            return False
            
        except Exception as e:
            self.logger.debug(f"点击排序按钮失败: {e}")
            return False
    
    def _parse_notes(self, keyword: str) -> List[Article]:
        """解析页面中的笔记"""
        articles = []
        
        try:
            # 尝试多种选择器
            selectors = [
                'section.note-item',
                'div.note-item', 
                'a.cover.ld.mask',
                '[class*="note-item"]',
                'div[data-v-a264b01c]',
            ]
            
            note_items = []
            for selector in selectors:
                items = self.page.query_selector_all(selector)
                if items:
                    note_items = items
                    break
            
            self.logger.debug(f"找到 {len(note_items)} 个笔记元素")
            
            for item in note_items:
                try:
                    article = self._parse_note_item(item, keyword)
                    if article:
                        articles.append(article)
                except Exception as e:
                    self.logger.debug(f"解析笔记失败: {e}")
                    continue
            
            # 备用：从HTML解析
            if not articles:
                articles = self._parse_from_html(keyword)
            
        except Exception as e:
            self.logger.error(f"解析笔记列表失败: {e}")
        
        return articles
    
    def _parse_note_item(self, item, keyword: str) -> Optional[Article]:
        """解析单个笔记"""
        # 标题
        title_selectors = ['.title', '.note-title', 'span.title', '.desc']
        title = ""
        for sel in title_selectors:
            elem = item.query_selector(sel)
            if elem:
                title = elem.inner_text().strip()
                if title:
                    break
        
        # 链接
        href = item.get_attribute('href')
        if not href:
            link_elem = item.query_selector('a')
            href = link_elem.get_attribute('href') if link_elem else ""
        
        if href and not href.startswith('http'):
            href = f"{self.BASE_URL}{href}"
        
        # 作者
        author_selectors = ['.author', '.nickname', '.name', '.author-name']
        author = "小红书用户"
        for sel in author_selectors:
            elem = item.query_selector(sel)
            if elem:
                author = elem.inner_text().strip() or author
                break
        
        # 点赞数
        likes = 0
        likes_selectors = ['.like-count', '.count', '.like span', '[class*="like"] span']
        for sel in likes_selectors:
            elem = item.query_selector(sel)
            if elem:
                likes = self._parse_count(elem.inner_text())
                break
        
        if not title and not href:
            return None
        
        return Article(
            title=title or "无标题",
            author=author,
            content="",
            url=href,
            platform=self.platform_name,
            keyword=keyword,
            likes=likes,
        )
    
    def _parse_from_html(self, keyword: str) -> List[Article]:
        """从HTML解析（备用）"""
        articles = []
        
        try:
            html = self.page.content()
            
            # 尝试匹配JSON数据
            patterns = [
                r'"noteCard":\s*\{[^}]*?"title":\s*"([^"]+)"[^}]*?"noteId":\s*"([^"]+)"',
                r'"title":\s*"([^"]{5,})"[^}]*?"id":\s*"([a-z0-9]{24})"',
            ]
            
            seen_ids = set()
            for pattern in patterns:
                matches = re.findall(pattern, html)
                for title, note_id in matches:
                    if note_id not in seen_ids:
                        seen_ids.add(note_id)
                        articles.append(Article(
                            title=title,
                            author="小红书用户",
                            content="",
                            url=f"{self.BASE_URL}/explore/{note_id}",
                            platform=self.platform_name,
                            keyword=keyword,
                        ))
            
        except Exception as e:
            self.logger.debug(f"HTML解析失败: {e}")
        
        return articles
    
    def _parse_count(self, text: str) -> int:
        """解析数量（如 1.2万 -> 12000）"""
        if not text:
            return 0
        
        text = text.strip()
        try:
            if '万' in text:
                return int(float(text.replace('万', '')) * 10000)
            elif 'w' in text.lower():
                return int(float(text.lower().replace('w', '')) * 10000)
            else:
                # 移除非数字字符
                num = re.sub(r'[^\d.]', '', text)
                return int(float(num)) if num else 0
        except ValueError:
            return 0
    
    def __del__(self):
        """析构时关闭浏览器"""
        self._close_browser()


# 测试代码
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="小红书爬虫")
    parser.add_argument("--login", action="store_true", help="扫码登录")
    parser.add_argument("--keyword", "-k", default="Monolith", help="搜索关键词")
    parser.add_argument("--sort", "-s", choices=["general", "time", "popular"], default="time", help="排序方式")
    parser.add_argument("--pages", "-p", type=int, default=2, help="滚动次数")
    args = parser.parse_args()
    
    crawler = XHSCrawler(headless=False)
    
    if args.login:
        success = crawler.login_by_qrcode()
        print(f"登录{'成功' if success else '失败'}")
    else:
        sort_map = {
            "general": XHSCrawler.SORT_GENERAL,
            "time": XHSCrawler.SORT_TIME,
            "popular": XHSCrawler.SORT_POPULAR,
        }
        
        articles = crawler.search(
            args.keyword, 
            max_pages=args.pages,
            sort=sort_map.get(args.sort, XHSCrawler.SORT_TIME)
        )
        
        print(f"\n采集到 {len(articles)} 条笔记 (排序: {args.sort}):")
        for i, article in enumerate(articles[:10], 1):
            print(f"[{i}] {article.title}")
            print(f"    作者: {article.author} | 点赞: {article.likes}")
            print(f"    链接: {article.url}")
            print()
