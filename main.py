#!/usr/bin/env python3
"""
舆情监测系统主入口
每日采集各平台关键词相关内容并存入飞书多维表格
"""
import argparse
import logging
from datetime import datetime
from typing import List

import yaml

from crawlers import SogouWechatCrawler, XHSCrawler, Article
from processors.dedup import DedupProcessor
from processors.sentiment import SentimentAnalyzer
from processors.filter import RelevanceFilter, TimeFilter
from storage.feishu_client import FeishuClient
from reporters.daily_report import DailyReporter

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_keywords(config_path: str = "config/keywords.yaml") -> dict:
    """加载关键词配置"""
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def crawl_wechat(keywords: List[str], max_pages: int = 3, delay: float = 3.0) -> List[Article]:
    """
    采集微信公众号文章
    
    Args:
        keywords: 关键词列表
        max_pages: 每个关键词最大搜索页数
        delay: 请求间隔
        
    Returns:
        文章列表
    """
    logger.info("开始采集微信公众号...")
    crawler = SogouWechatCrawler(request_delay=delay)
    articles = crawler.search_multiple(keywords, max_pages=max_pages)
    logger.info(f"微信公众号采集完成，共 {len(articles)} 篇文章")
    return articles


def crawl_xhs(keywords: List[str], max_pages: int = 2, delay: float = 3.0) -> List[Article]:
    """
    采集小红书笔记
    
    Args:
        keywords: 关键词列表
        max_pages: 每个关键词的滚动加载次数
        delay: 请求间隔
        
    Returns:
        文章列表
    """
    logger.info("开始采集小红书...")
    crawler = XHSCrawler(request_delay=delay, headless=True)
    articles = crawler.search_multiple(keywords, max_pages=max_pages)
    logger.info(f"小红书采集完成，共 {len(articles)} 条笔记")
    return articles


def run_crawl(args):
    """运行采集任务"""
    # 加载配置
    config = load_keywords()
    keywords = config.get("keywords", [])
    search_config = config.get("search", {})
    
    if not keywords:
        logger.error("关键词列表为空，请检查 config/keywords.yaml")
        return
    
    logger.info(f"开始采集，关键词: {keywords}")
    
    all_articles = []
    
    # 采集微信公众号
    if not args.platform or args.platform in ["wechat", "all"]:
        wechat_articles = crawl_wechat(
            keywords,
            max_pages=search_config.get("max_pages", 3),
            delay=search_config.get("request_delay", 3)
        )
        all_articles.extend(wechat_articles)
    
    # 采集小红书
    if args.platform in ["xhs", "all"]:
        xhs_articles = crawl_xhs(
            keywords,
            max_pages=2,
            delay=search_config.get("request_delay", 3)
        )
        all_articles.extend(xhs_articles)
    
    # 时间过滤（只保留48小时内的内容）
    time_filter = TimeFilter(hours=search_config.get("time_filter_hours", 48))
    all_articles = time_filter.filter_recent(all_articles)
    logger.info(f"时间过滤后剩余 {len(all_articles)} 篇文章")
    
    # 关键词组合过滤（排除不相关文章）
    if args.filter:
        relevance_filter = RelevanceFilter()
        filtered_articles = relevance_filter.filter_articles(all_articles)
        logger.info(f"过滤后剩余 {len(filtered_articles)} 篇相关文章（过滤掉 {len(all_articles) - len(filtered_articles)} 篇）")
        all_articles = filtered_articles
    
    # 去重
    dedup = DedupProcessor()
    unique_articles = dedup.deduplicate(all_articles)
    logger.info(f"去重后剩余 {len(unique_articles)} 篇文章")
    
    # 情感分析
    if args.analyze:
        analyzer = SentimentAnalyzer()
        unique_articles = analyzer.analyze_articles(unique_articles)
    
    # 存储到飞书
    feishu = FeishuClient()
    if args.save:
        if feishu.is_configured():
            result = feishu.add_new_articles(unique_articles)
            logger.info(f"飞书存储结果: 成功 {result['success']}, 失败 {result['failed']}, 跳过 {result['skipped']}")
        else:
            logger.warning("飞书未配置，跳过存储")
            logger.info("请配置 config/feishu.yaml 后重试")
    
    # 生成并发送LLM简报
    if args.briefing:
        reporter = DailyReporter(use_llm=True)
        full_report = reporter.generate_full_report(unique_articles)
        print("\n" + full_report)
        
        # 发送到飞书Webhook
        if feishu.webhook_url:
            feishu.send_webhook_message(full_report)
            logger.info("简报已发送到飞书群")
    
    # 输出结果摘要
    print(f"\n{'='*60}")
    print(f"采集完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"采集文章总数: {len(unique_articles)}")
    print(f"{'='*60}\n")
    
    # 按关键词统计
    keyword_stats = {}
    for article in unique_articles:
        keyword_stats[article.keyword] = keyword_stats.get(article.keyword, 0) + 1
    
    print("按关键词统计:")
    for kw, count in keyword_stats.items():
        print(f"  {kw}: {count} 篇")
    
    # 情感统计
    if args.analyze:
        sentiment_stats = {"积极": 0, "消极": 0, "中立": 0}
        for article in unique_articles:
            if article.sentiment:
                sentiment_stats[article.sentiment] = sentiment_stats.get(article.sentiment, 0) + 1
        
        print("\n情感分析统计:")
        for label, count in sentiment_stats.items():
            pct = count / len(unique_articles) * 100 if unique_articles else 0
            print(f"  {label}: {count} 篇 ({pct:.1f}%)")
    
    # 输出前10篇文章
    print(f"\n最新 {min(10, len(unique_articles))} 篇文章:")
    print("-" * 60)
    for i, article in enumerate(unique_articles[:10], 1):
        sentiment_info = f" [{article.sentiment}]" if article.sentiment else ""
        print(f"[{i}] {article.title}{sentiment_info}")
        print(f"    来源: {article.author} | 关键词: {article.keyword}")
        print(f"    链接: {article.url[:60]}...")
        print()
    
    return unique_articles


def main():
    parser = argparse.ArgumentParser(description="舆情监测系统")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # 采集命令
    crawl_parser = subparsers.add_parser("crawl", help="运行采集任务")
    crawl_parser.add_argument(
        "--platform", "-p",
        choices=["wechat", "xhs", "weibo", "all"],
        default="wechat",
        help="采集平台 (默认: wechat)"
    )
    crawl_parser.add_argument(
        "--save", "-s",
        action="store_true",
        help="保存到飞书多维表格"
    )
    crawl_parser.add_argument(
        "--analyze", "-a",
        action="store_true",
        help="进行情感分析"
    )
    crawl_parser.add_argument(
        "--filter", "-f",
        action="store_true",
        help="过滤不相关文章（Monolith需包含砺思/曹曦/投资等关联词）"
    )
    crawl_parser.add_argument(
        "--briefing", "-b",
        action="store_true",
        help="生成LLM智能简报并发送到飞书"
    )
    crawl_parser.set_defaults(func=run_crawl)
    
    # 测试命令
    test_parser = subparsers.add_parser("test", help="测试配置")
    test_parser.set_defaults(func=lambda args: test_config())
    
    args = parser.parse_args()
    
    if args.command:
        args.func(args)
    else:
        # 默认运行采集
        args.platform = "wechat"
        args.save = False
        args.analyze = True
        args.filter = True
        args.briefing = False
        run_crawl(args)


def test_config():
    """测试配置是否正确"""
    print("测试配置...")
    
    # 测试关键词配置
    try:
        config = load_keywords()
        keywords = config.get("keywords", [])
        print(f"✓ 关键词配置: {keywords}")
        
        # 检查过滤规则
        relevance = config.get("relevance_keywords", {})
        if relevance:
            print(f"✓ 过滤规则已配置: {list(relevance.keys())}")
    except Exception as e:
        print(f"✗ 关键词配置错误: {e}")
    
    # 测试飞书配置
    try:
        feishu = FeishuClient()
        if feishu.is_configured():
            print("✓ 飞书配置完整")
        else:
            print("✗ 飞书配置不完整，请填写 config/feishu.yaml")
        
        if feishu.webhook_url:
            print("✓ Webhook已配置")
    except Exception as e:
        print(f"✗ 飞书配置错误: {e}")
    
    # 测试LLM配置
    try:
        from utils.llm_client import LLMClient
        llm = LLMClient()
        if llm.is_configured():
            print(f"✓ LLM配置完整 (模型: {llm.model})")
        else:
            print("✗ LLM未配置，请在 config/feishu.yaml 添加 llm 配置")
    except Exception as e:
        print(f"✗ LLM配置错误: {e}")
    
    # 测试爬虫
    try:
        crawler = SogouWechatCrawler()
        articles = crawler.search("测试", max_pages=1)
        print(f"✓ 搜狗微信爬虫正常，测试获取 {len(articles)} 篇文章")
    except Exception as e:
        print(f"✗ 爬虫测试失败: {e}")


if __name__ == "__main__":
    main()

