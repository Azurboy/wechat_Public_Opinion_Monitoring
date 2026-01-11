"""
情感分析处理器
使用SnowNLP对文本进行情感分析
"""
from typing import List, Tuple
import logging

from snownlp import SnowNLP

from crawlers.base import Article

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SentimentAnalyzer:
    """情感分析器"""
    
    # 情感阈值
    POSITIVE_THRESHOLD = 0.6   # 大于此值为积极
    NEGATIVE_THRESHOLD = 0.4   # 小于此值为消极
    
    def __init__(self, positive_threshold: float = 0.6, negative_threshold: float = 0.4):
        """
        初始化情感分析器
        
        Args:
            positive_threshold: 积极情感阈值
            negative_threshold: 消极情感阈值
        """
        self.positive_threshold = positive_threshold
        self.negative_threshold = negative_threshold
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def analyze_text(self, text: str) -> Tuple[str, float]:
        """
        分析文本情感
        
        Args:
            text: 待分析文本
            
        Returns:
            (情感标签, 情感分数) - 情感分数范围 0-1，越接近1越积极
        """
        if not text or not text.strip():
            return "中立", 0.5
        
        try:
            s = SnowNLP(text)
            score = s.sentiments  # 返回0-1之间的值
            
            if score >= self.positive_threshold:
                label = "积极"
            elif score <= self.negative_threshold:
                label = "消极"
            else:
                label = "中立"
            
            return label, round(score, 4)
            
        except Exception as e:
            self.logger.error(f"情感分析失败: {e}")
            return "中立", 0.5
    
    def analyze_article(self, article: Article) -> Article:
        """
        分析文章情感
        
        Args:
            article: 文章对象
            
        Returns:
            更新情感标注后的文章对象
        """
        # 合并标题和内容进行分析
        text = f"{article.title} {article.content}"
        label, score = self.analyze_text(text)
        
        article.sentiment = label
        article.sentiment_score = score
        
        return article
    
    def analyze_articles(self, articles: List[Article]) -> List[Article]:
        """
        批量分析文章情感
        
        Args:
            articles: 文章列表
            
        Returns:
            更新情感标注后的文章列表
        """
        self.logger.info(f"开始情感分析，共 {len(articles)} 篇文章")
        
        for i, article in enumerate(articles):
            self.analyze_article(article)
            
            if (i + 1) % 20 == 0:
                self.logger.info(f"已分析 {i + 1}/{len(articles)} 篇")
        
        # 统计结果
        stats = self.get_statistics(articles)
        self.logger.info(f"情感分析完成: 积极 {stats['positive']}, 消极 {stats['negative']}, 中立 {stats['neutral']}")
        
        return articles
    
    def get_statistics(self, articles: List[Article]) -> dict:
        """
        获取情感统计
        
        Args:
            articles: 文章列表
            
        Returns:
            统计结果
        """
        stats = {
            "positive": 0,
            "negative": 0,
            "neutral": 0,
            "total": len(articles),
            "avg_score": 0.0
        }
        
        total_score = 0.0
        
        for article in articles:
            if article.sentiment == "积极":
                stats["positive"] += 1
            elif article.sentiment == "消极":
                stats["negative"] += 1
            else:
                stats["neutral"] += 1
            
            if article.sentiment_score is not None:
                total_score += article.sentiment_score
        
        if articles:
            stats["avg_score"] = round(total_score / len(articles), 4)
        
        return stats


# 测试代码
if __name__ == "__main__":
    analyzer = SentimentAnalyzer()
    
    # 测试文本
    test_texts = [
        "这个产品真的太棒了，非常推荐！",
        "服务态度很差，非常失望",
        "今天天气不错",
        "这次投资收益很好，砺思资本表现出色",
        "市场行情一般，没有太大波动",
    ]
    
    print("情感分析测试:")
    print("-" * 50)
    for text in test_texts:
        label, score = analyzer.analyze_text(text)
        print(f"文本: {text}")
        print(f"结果: {label} (分数: {score})")
        print()




