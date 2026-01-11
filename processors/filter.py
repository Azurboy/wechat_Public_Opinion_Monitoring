"""
关键词组合过滤器和时间过滤器
用于过滤掉与目标主题无关的文章以及过期内容
"""
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Set, Optional

import yaml

from crawlers.base import Article

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RelevanceFilter:
    """关键词相关性过滤器"""
    
    # 默认的关联词规则
    # Monolith/MONOLITH 必须同时包含这些词之一才保留
    DEFAULT_RELEVANCE_RULES = {
        "Monolith": [
            "砺思资本", "砺思", "曹曦", "投资", "基金", "资本", 
            "融资", "创业", "实习", "VC", "PE", "管理"
        ],
        "MONOLITH": [
            "砺思资本", "砺思", "曹曦", "投资", "基金", "资本",
            "融资", "创业", "实习", "VC", "PE", "管理"
        ],
    }
    
    # 这些关键词的文章直接保留，不需要过滤
    WHITELIST_KEYWORDS = {"曹曦", "砺思资本"}
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化过滤器
        
        Args:
            config_path: 配置文件路径，默认为项目根目录下的 config/keywords.yaml
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # 如果未指定路径，自动查找项目根目录
        if config_path is None:
            from pathlib import Path
            # 尝试找到项目根目录
            current_file = Path(__file__).resolve()
            project_root = current_file.parent.parent
            config_path = str(project_root / "config" / "keywords.yaml")
        
        self.relevance_rules = self._load_rules(config_path)
        self.whitelist_keywords = self.WHITELIST_KEYWORDS.copy()
    
    def _load_rules(self, config_path: str) -> Dict[str, List[str]]:
        """从配置文件加载过滤规则"""
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}
            
            rules = config.get("relevance_keywords", {})
            if rules:
                self.logger.info(f"从配置文件加载了 {len(rules)} 条过滤规则")
                return rules
        except FileNotFoundError:
            self.logger.warning(f"配置文件不存在: {config_path}，使用默认规则")
        except Exception as e:
            self.logger.warning(f"加载配置文件失败 ({config_path}): {e}，使用默认规则")
        
        return self.DEFAULT_RELEVANCE_RULES.copy()
    
    def is_relevant(self, article: Article) -> bool:
        """
        判断文章是否相关
        
        Args:
            article: 文章对象
            
        Returns:
            是否相关
        """
        keyword = article.keyword
        
        # 白名单关键词直接通过
        if keyword in self.whitelist_keywords:
            return True
        
        # 检查是否需要过滤
        if keyword not in self.relevance_rules:
            # 没有定义规则的关键词，默认通过
            return True
        
        # 获取关联词列表
        related_keywords = self.relevance_rules[keyword]
        
        # 合并标题和内容进行检查
        text = f"{article.title} {article.content} {article.author}".lower()
        
        # 检查是否包含任一关联词
        for related in related_keywords:
            if related.lower() in text:
                return True
        
        return False
    
    def filter_articles(self, articles: List[Article]) -> List[Article]:
        """
        过滤文章列表
        
        Args:
            articles: 文章列表
            
        Returns:
            过滤后的文章列表
        """
        if not articles:
            return []
        
        original_count = len(articles)
        filtered = [a for a in articles if self.is_relevant(a)]
        removed_count = original_count - len(filtered)
        
        if removed_count > 0:
            self.logger.info(f"过滤掉 {removed_count} 篇不相关文章，保留 {len(filtered)} 篇")
        
        return filtered
    
    def get_removed_articles(self, articles: List[Article]) -> List[Article]:
        """
        获取被过滤掉的文章（用于调试）
        
        Args:
            articles: 文章列表
            
        Returns:
            被过滤掉的文章列表
        """
        return [a for a in articles if not self.is_relevant(a)]


# 测试代码
if __name__ == "__main__":
    from crawlers.base import Article
    
    # 创建测试数据
    test_articles = [
        Article(
            title="Monolith砺思资本完成新一轮融资",
            author="投资界",
            content="砺思资本宣布完成融资",
            url="https://example.com/1",
            platform="微信公众号",
            keyword="Monolith",
        ),
        Article(
            title="MonolithSoft开发新游戏",  # 应该被过滤
            author="游戏日报",
            content="任天堂旗下游戏工作室",
            url="https://example.com/2",
            platform="微信公众号",
            keyword="Monolith",
        ),
        Article(
            title="Monolith Audio发布新音箱",  # 应该被过滤
            author="音响爱好者",
            content="高端音响设备",
            url="https://example.com/3",
            platform="微信公众号",
            keyword="Monolith",
        ),
        Article(
            title="曹曦出席投资论坛",  # 白名单关键词，直接通过
            author="财经观察",
            content="曹曦发表演讲",
            url="https://example.com/4",
            platform="微信公众号",
            keyword="曹曦",
        ),
        Article(
            title="Monolith Management招聘实习生",  # 包含"实习"，通过
            author="求职平台",
            content="投资实习机会",
            url="https://example.com/5",
            platform="微信公众号",
            keyword="Monolith",
        ),
    ]
    
    # 测试过滤
    filter = RelevanceFilter()
    
    print("过滤测试:")
    print("-" * 50)
    
    for article in test_articles:
        relevant = filter.is_relevant(article)
        status = "✓ 保留" if relevant else "✗ 过滤"
        print(f"{status}: {article.title}")
        print(f"        关键词: {article.keyword}")
        print()
    
    # 批量过滤
    filtered = filter.filter_articles(test_articles)
    print(f"\n过滤结果: {len(test_articles)} -> {len(filtered)} 篇")


class TimeFilter:
    """时间过滤器，只保留最近N小时内发布的文章"""
    
    def __init__(self, hours: int = 48):
        """
        初始化时间过滤器
        
        Args:
            hours: 保留多少小时内的文章，默认48小时
        """
        self.hours = hours
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def filter_recent(self, articles: List[Article], hours: Optional[int] = None) -> List[Article]:
        """
        只保留最近N小时内发布的文章
        
        Args:
            articles: 文章列表
            hours: 可选，覆盖默认的小时数
            
        Returns:
            过滤后的文章列表
        """
        if not articles:
            return []
        
        filter_hours = hours if hours is not None else self.hours
        cutoff = datetime.now() - timedelta(hours=filter_hours)
        
        filtered = []
        skipped_no_time = 0
        skipped_too_old = 0
        
        for article in articles:
            if article.published_at is None:
                # 没有发布时间的文章，保守处理，保留
                filtered.append(article)
                skipped_no_time += 1
            elif article.published_at > cutoff:
                # 在时间范围内，保留
                filtered.append(article)
            else:
                # 太旧，过滤掉
                skipped_too_old += 1
        
        self.logger.info(
            f"时间过滤: 保留 {len(filtered)} 篇 "
            f"(过滤掉 {skipped_too_old} 篇过期内容, "
            f"{skipped_no_time} 篇无时间戳)"
        )
        
        return filtered
    
    def filter_by_date(self, articles: List[Article], target_date: datetime) -> List[Article]:
        """
        只保留特定日期的文章
        
        Args:
            articles: 文章列表
            target_date: 目标日期
            
        Returns:
            过滤后的文章列表
        """
        if not articles:
            return []
        
        target_day = target_date.date()
        filtered = [
            a for a in articles 
            if a.published_at and a.published_at.date() == target_day
        ]
        
        self.logger.info(
            f"日期过滤 ({target_day}): {len(articles)} -> {len(filtered)} 篇"
        )
        
        return filtered


# 时间过滤测试
if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("时间过滤器测试")
    print("=" * 50)
    
    # 创建测试数据
    now = datetime.now()
    test_articles_time = [
        Article(
            title="刚刚发布的文章",
            author="测试",
            content="内容",
            url="https://example.com/1",
            platform="微信公众号",
            keyword="Monolith",
            published_at=now - timedelta(hours=1),
        ),
        Article(
            title="昨天发布的文章",
            author="测试",
            content="内容",
            url="https://example.com/2",
            platform="微信公众号",
            keyword="Monolith",
            published_at=now - timedelta(hours=25),
        ),
        Article(
            title="3天前发布的文章",
            author="测试",
            content="内容",
            url="https://example.com/3",
            platform="微信公众号",
            keyword="Monolith",
            published_at=now - timedelta(days=3),
        ),
        Article(
            title="没有时间戳的文章",
            author="测试",
            content="内容",
            url="https://example.com/4",
            platform="微信公众号",
            keyword="Monolith",
            published_at=None,
        ),
    ]
    
    time_filter = TimeFilter(hours=48)
    filtered = time_filter.filter_recent(test_articles_time)
    
    print("\n48小时内的文章:")
    for a in filtered:
        time_str = a.published_at.strftime("%Y-%m-%d %H:%M") if a.published_at else "无时间"
        print(f"  - {a.title} ({time_str})")

