"""
每日日报生成器
生成舆情监测日报并推送到飞书
支持LLM生成智能简报
"""
from datetime import datetime
from typing import List, Dict, Optional
from collections import defaultdict
import logging

from crawlers.base import Article

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DailyReporter:
    """每日日报生成器"""
    
    def __init__(self, use_llm: bool = True):
        """
        初始化日报生成器
        
        Args:
            use_llm: 是否使用LLM生成智能简报
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.use_llm = use_llm
        self._llm_client = None
    
    @property
    def llm_client(self):
        """延迟加载LLM客户端"""
        if self._llm_client is None and self.use_llm:
            try:
                from utils.llm_client import LLMClient
                self._llm_client = LLMClient()
            except Exception as e:
                self.logger.warning(f"LLM客户端加载失败: {e}")
        return self._llm_client
    
    def generate_report(self, articles: List[Article], date: datetime = None) -> str:
        """
        生成日报文本
        
        Args:
            articles: 文章列表
            date: 报告日期，默认为今天
            
        Returns:
            日报文本
        """
        if date is None:
            date = datetime.now()
        
        date_str = date.strftime("%Y年%m月%d日")
        
        # 统计数据
        stats = self._calculate_stats(articles)
        
        # 生成报告
        report_lines = [
            f"📊 舆情监测日报 - {date_str}",
            "=" * 40,
            "",
            f"📈 今日概览",
            f"• 采集文章总数: {stats['total']} 篇",
            "",
        ]
        
        # 平台分布
        if stats['by_platform']:
            report_lines.append("📱 平台分布:")
            for platform, count in stats['by_platform'].items():
                pct = count / stats['total'] * 100 if stats['total'] else 0
                report_lines.append(f"  • {platform}: {count} 篇 ({pct:.1f}%)")
            report_lines.append("")
        
        # 关键词分布
        if stats['by_keyword']:
            report_lines.append("🔑 关键词分布:")
            for keyword, count in stats['by_keyword'].items():
                pct = count / stats['total'] * 100 if stats['total'] else 0
                report_lines.append(f"  • {keyword}: {count} 篇 ({pct:.1f}%)")
            report_lines.append("")
        
        # 情感分析
        if stats['by_sentiment']:
            report_lines.append("💬 情感分析:")
            sentiment_emoji = {"积极": "😊", "消极": "😟", "中立": "😐"}
            for sentiment, count in stats['by_sentiment'].items():
                pct = count / stats['total'] * 100 if stats['total'] else 0
                emoji = sentiment_emoji.get(sentiment, "")
                report_lines.append(f"  • {emoji} {sentiment}: {count} 篇 ({pct:.1f}%)")
            report_lines.append("")
        
        # 重点内容
        report_lines.append("📌 重点内容摘要:")
        report_lines.append("-" * 40)
        
        # 按情感分组展示
        # 先展示消极内容（需要关注）
        negative_articles = [a for a in articles if a.sentiment == "消极"]
        if negative_articles:
            report_lines.append("")
            report_lines.append("⚠️ 需关注（消极内容）:")
            for i, article in enumerate(negative_articles[:3], 1):
                report_lines.append(f"  {i}. {article.title[:40]}...")
                report_lines.append(f"     来源: {article.author} | 关键词: {article.keyword}")
        
        # 展示积极内容
        positive_articles = [a for a in articles if a.sentiment == "积极"]
        if positive_articles:
            report_lines.append("")
            report_lines.append("✅ 正面报道:")
            for i, article in enumerate(positive_articles[:3], 1):
                report_lines.append(f"  {i}. {article.title[:40]}...")
                report_lines.append(f"     来源: {article.author} | 关键词: {article.keyword}")
        
        report_lines.append("")
        report_lines.append("=" * 40)
        report_lines.append(f"报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return "\n".join(report_lines)
    
    def _calculate_stats(self, articles: List[Article]) -> Dict:
        """计算统计数据"""
        stats = {
            "total": len(articles),
            "by_platform": defaultdict(int),
            "by_keyword": defaultdict(int),
            "by_sentiment": defaultdict(int),
        }
        
        for article in articles:
            stats["by_platform"][article.platform] += 1
            stats["by_keyword"][article.keyword] += 1
            if article.sentiment:
                stats["by_sentiment"][article.sentiment] += 1
        
        # 转换为普通字典并排序
        stats["by_platform"] = dict(sorted(stats["by_platform"].items(), key=lambda x: x[1], reverse=True))
        stats["by_keyword"] = dict(sorted(stats["by_keyword"].items(), key=lambda x: x[1], reverse=True))
        stats["by_sentiment"] = dict(sorted(stats["by_sentiment"].items(), key=lambda x: x[1], reverse=True))
        
        return stats
    
    def generate_markdown_report(self, articles: List[Article], date: datetime = None) -> str:
        """
        生成Markdown格式的日报
        
        Args:
            articles: 文章列表
            date: 报告日期
            
        Returns:
            Markdown格式的日报
        """
        if date is None:
            date = datetime.now()
        
        date_str = date.strftime("%Y年%m月%d日")
        stats = self._calculate_stats(articles)
        
        md_lines = [
            f"# 舆情监测日报 - {date_str}",
            "",
            "## 📈 今日概览",
            "",
            f"| 指标 | 数值 |",
            f"|------|------|",
            f"| 采集文章总数 | {stats['total']} 篇 |",
            "",
        ]
        
        # 平台分布表格
        if stats['by_platform']:
            md_lines.append("## 📱 平台分布")
            md_lines.append("")
            md_lines.append("| 平台 | 数量 | 占比 |")
            md_lines.append("|------|------|------|")
            for platform, count in stats['by_platform'].items():
                pct = count / stats['total'] * 100 if stats['total'] else 0
                md_lines.append(f"| {platform} | {count} | {pct:.1f}% |")
            md_lines.append("")
        
        # 关键词分布表格
        if stats['by_keyword']:
            md_lines.append("## 🔑 关键词分布")
            md_lines.append("")
            md_lines.append("| 关键词 | 数量 | 占比 |")
            md_lines.append("|--------|------|------|")
            for keyword, count in stats['by_keyword'].items():
                pct = count / stats['total'] * 100 if stats['total'] else 0
                md_lines.append(f"| {keyword} | {count} | {pct:.1f}% |")
            md_lines.append("")
        
        # 情感分析
        if stats['by_sentiment']:
            md_lines.append("## 💬 情感分析")
            md_lines.append("")
            md_lines.append("| 情感 | 数量 | 占比 |")
            md_lines.append("|------|------|------|")
            for sentiment, count in stats['by_sentiment'].items():
                pct = count / stats['total'] * 100 if stats['total'] else 0
                md_lines.append(f"| {sentiment} | {count} | {pct:.1f}% |")
            md_lines.append("")
        
        # 重点内容列表
        md_lines.append("## 📌 重点内容")
        md_lines.append("")
        
        negative_articles = [a for a in articles if a.sentiment == "消极"]
        if negative_articles:
            md_lines.append("### ⚠️ 需关注（消极内容）")
            md_lines.append("")
            for i, article in enumerate(negative_articles[:5], 1):
                md_lines.append(f"{i}. **{article.title}**")
                md_lines.append(f"   - 来源: {article.author}")
                md_lines.append(f"   - 关键词: {article.keyword}")
                md_lines.append(f"   - [查看原文]({article.url})")
                md_lines.append("")
        
        positive_articles = [a for a in articles if a.sentiment == "积极"]
        if positive_articles:
            md_lines.append("### ✅ 正面报道")
            md_lines.append("")
            for i, article in enumerate(positive_articles[:5], 1):
                md_lines.append(f"{i}. **{article.title}**")
                md_lines.append(f"   - 来源: {article.author}")
                md_lines.append(f"   - 关键词: {article.keyword}")
                md_lines.append(f"   - [查看原文]({article.url})")
                md_lines.append("")
        
        md_lines.append("---")
        md_lines.append(f"*报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
        
        return "\n".join(md_lines)
    
    def generate_llm_briefing(self, articles: List[Article]) -> Optional[str]:
        """
        使用LLM生成智能舆情简报
        
        Args:
            articles: 文章列表
            
        Returns:
            LLM生成的简报文本，失败返回None
        """
        if not self.use_llm:
            self.logger.info("LLM功能未启用")
            return None
        
        if not self.llm_client or not self.llm_client.is_configured():
            self.logger.warning("LLM客户端未配置")
            return None
        
        return self.llm_client.generate_briefing(articles, style="executive")
    
    def generate_full_report(self, articles: List[Article], date: datetime = None) -> str:
        """
        生成完整日报（基础报告 + LLM简报）
        
        Args:
            articles: 文章列表
            date: 报告日期
            
        Returns:
            完整的日报文本
        """
        # 基础报告
        base_report = self.generate_report(articles, date)
        
        # 尝试生成LLM简报
        llm_briefing = self.generate_llm_briefing(articles)
        
        if llm_briefing:
            # 将LLM简报放在开头
            full_report = f"""🤖 AI智能简报
{'='*40}
{llm_briefing}

{'='*40}

{base_report}"""
            return full_report
        
        return base_report


# 测试代码
if __name__ == "__main__":
    from crawlers.base import Article
    from datetime import datetime
    
    # 创建测试数据
    test_articles = [
        Article(
            title="砺思资本完成新一轮融资，布局AI赛道",
            author="投资界",
            content="砺思资本宣布完成新一轮融资...",
            url="https://example.com/1",
            platform="微信公众号",
            keyword="砺思资本",
            sentiment="积极",
            sentiment_score=0.85,
        ),
        Article(
            title="Monolith产品发布会圆满成功",
            author="科技日报",
            content="Monolith最新产品发布...",
            url="https://example.com/2",
            platform="微信公众号",
            keyword="Monolith",
            sentiment="积极",
            sentiment_score=0.92,
        ),
        Article(
            title="市场观察：投资行业面临挑战",
            author="财经观察",
            content="近期市场波动较大...",
            url="https://example.com/3",
            platform="微信公众号",
            keyword="砺思资本",
            sentiment="消极",
            sentiment_score=0.25,
        ),
        Article(
            title="曹曦出席行业论坛并发表演讲",
            author="经济观察",
            content="曹曦在论坛上分享了...",
            url="https://example.com/4",
            platform="微信公众号",
            keyword="曹曦",
            sentiment="中立",
            sentiment_score=0.55,
        ),
    ]
    
    # 生成日报
    reporter = DailyReporter()
    report = reporter.generate_report(test_articles)
    print(report)

