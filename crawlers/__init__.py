# 爬虫模块
from .base import BaseCrawler, Article
from .sogou_wechat import SogouWechatCrawler
from .xhs_crawler import XHSCrawler
from .wechat_mp import WechatMPCrawler

__all__ = ['BaseCrawler', 'Article', 'SogouWechatCrawler', 'XHSCrawler', 'WechatMPCrawler']

