#!/usr/bin/env python3
"""
定时任务调度器
每日自动运行舆情采集任务
"""
import argparse
import logging
import time
from datetime import datetime

import schedule
import yaml

from crawlers import SogouWechatCrawler, Article
from processors.dedup import DedupProcessor
from processors.sentiment import SentimentAnalyzer
from storage.feishu_client import FeishuClient
from reporters.daily_report import DailyReporter

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('scheduler.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


def load_config():
    """加载配置"""
    with open("config/keywords.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def run_daily_task():
    """运行每日采集任务"""
    logger.info("=" * 60)
    logger.info(f"开始执行每日采集任务 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)
    
    try:
        # 加载配置
        config = load_config()
        keywords = config.get("keywords", [])
        search_config = config.get("search", {})
        
        if not keywords:
            logger.error("关键词列表为空")
            return
        
        # 采集数据
        logger.info(f"采集关键词: {keywords}")
        crawler = SogouWechatCrawler(
            request_delay=search_config.get("request_delay", 3)
        )
        articles = crawler.search_multiple(
            keywords,
            max_pages=search_config.get("max_pages", 3)
        )
        
        if not articles:
            logger.warning("未采集到任何文章")
            return
        
        # 去重
        dedup = DedupProcessor()
        unique_articles = dedup.deduplicate(articles)
        logger.info(f"去重后剩余 {len(unique_articles)} 篇文章")
        
        # 情感分析
        analyzer = SentimentAnalyzer()
        unique_articles = analyzer.analyze_articles(unique_articles)
        
        # 存储到飞书
        feishu = FeishuClient()
        if feishu.is_configured():
            result = feishu.add_new_articles(unique_articles)
            logger.info(f"飞书存储: 成功 {result['success']}, 失败 {result['failed']}, 跳过 {result['skipped']}")
        else:
            logger.warning("飞书未配置，跳过存储")
        
        # 生成并发送日报
        reporter = DailyReporter()
        report = reporter.generate_report(unique_articles)
        
        if feishu.webhook_url:
            feishu.send_webhook_message(report)
            logger.info("日报已发送到飞书群")
        else:
            logger.info("Webhook未配置，日报仅输出到日志:")
            logger.info(f"\n{report}")
        
        logger.info(f"每日任务完成 - 共采集 {len(unique_articles)} 篇文章")
        
    except Exception as e:
        logger.error(f"每日任务执行失败: {e}", exc_info=True)


def main():
    parser = argparse.ArgumentParser(description="舆情监测定时调度器")
    parser.add_argument(
        "--time", "-t",
        default="09:00",
        help="每日执行时间 (默认: 09:00)"
    )
    parser.add_argument(
        "--run-now",
        action="store_true",
        help="立即执行一次任务"
    )
    parser.add_argument(
        "--daemon",
        action="store_true",
        help="以守护进程方式运行"
    )
    args = parser.parse_args()
    
    if args.run_now:
        logger.info("立即执行任务...")
        run_daily_task()
        return
    
    # 设置定时任务
    schedule.every().day.at(args.time).do(run_daily_task)
    logger.info(f"定时任务已设置，每天 {args.time} 执行")
    logger.info("按 Ctrl+C 停止调度器")
    
    # 运行调度器
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # 每分钟检查一次
    except KeyboardInterrupt:
        logger.info("调度器已停止")


if __name__ == "__main__":
    main()




