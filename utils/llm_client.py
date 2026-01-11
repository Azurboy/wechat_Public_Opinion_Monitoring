"""
LLM客户端
封装DeepSeek API调用，用于生成舆情简报
"""
import logging
from pathlib import Path
from typing import List, Optional

import requests

from crawlers.base import Article

# 导入配置管理
try:
    from config_manager import get_config_manager
except ImportError:
    get_config_manager = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LLMClient:
    """LLM客户端（支持DeepSeek/硅基流动）"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化LLM客户端
        
        Args:
            config_path: 配置文件路径（已弃用，使用config_manager）
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # 使用配置管理器加载配置
        if get_config_manager:
            try:
                config_manager = get_config_manager()
                llm_config = config_manager.get_llm_config()
                
                self.api_key = llm_config.get("api_key", "")
                self.base_url = llm_config.get("base_url", "https://api.siliconflow.cn/v1")
                self.model = llm_config.get("model", "deepseek-ai/DeepSeek-V3")
            except Exception as e:
                self.logger.warning(f"从配置管理器加载失败: {e}")
                self.api_key = ""
                self.base_url = "https://api.siliconflow.cn/v1"
                self.model = "deepseek-ai/DeepSeek-V3"
        else:
            # Fallback：没有config_manager
            self.api_key = ""
            self.base_url = "https://api.siliconflow.cn/v1"
            self.model = "deepseek-ai/DeepSeek-V3"
        
        self._validate_config()
    
    def _load_config(self, config_path: str) -> dict:
        """已弃用：加载配置文件（保留用于兼容性）"""
        return {}
    
    def _validate_config(self):
        """验证配置"""
        if not self.api_key:
            self.logger.warning("LLM API Key未配置")
    
    def is_configured(self) -> bool:
        """检查是否已配置"""
        return bool(self.api_key)
    
    def chat(self, prompt: str, system_prompt: str = None, max_tokens: int = 1000) -> Optional[str]:
        """
        调用LLM进行对话
        
        Args:
            prompt: 用户提示
            system_prompt: 系统提示
            max_tokens: 最大返回token数
            
        Returns:
            LLM回复内容
        """
        if not self.is_configured():
            self.logger.error("LLM未配置，无法调用")
            return None
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": 0.7,
                },
                timeout=60
            )
            
            response.raise_for_status()
            result = response.json()
            
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            return content.strip()
            
        except requests.RequestException as e:
            self.logger.error(f"LLM API调用失败: {e}")
            return None
        except Exception as e:
            self.logger.error(f"LLM调用异常: {e}")
            return None
    
    def generate_briefing(self, articles: List[Article], style: str = "executive") -> Optional[str]:
        """
        生成舆情简报
        
        Args:
            articles: 文章列表
            style: 简报风格（executive=高管版, detailed=详细版, concise=简洁版）
            
        Returns:
            舆情简报文本
        """
        if not articles:
            return "今日暂无相关舆情内容。"
        
        # 构建文章摘要
        article_summaries = []
        for i, article in enumerate(articles[:20], 1):  # 最多20篇，避免超过token限制
            sentiment_tag = f"[{article.sentiment}]" if article.sentiment else ""
            summary = f"{i}. {article.title} {sentiment_tag}\n   来源: {article.author} | 关键词: {article.keyword}"
            article_summaries.append(summary)
        
        articles_text = "\n".join(article_summaries)
        
        # 统计数据
        total = len(articles)
        positive = sum(1 for a in articles if a.sentiment == "积极")
        negative = sum(1 for a in articles if a.sentiment == "消极")
        neutral = sum(1 for a in articles if a.sentiment == "中立")
        
        # 按关键词统计
        keyword_stats = {}
        for a in articles:
            keyword_stats[a.keyword] = keyword_stats.get(a.keyword, 0) + 1
        keyword_text = ", ".join([f"{k}: {v}篇" for k, v in keyword_stats.items()])
        
        # 构建prompt - 第一版本：详细高管风格
        system_prompt = """你是一位资深的舆情分析专家，为公司高管团队撰写每日舆情监测报告。

你的职责是：
1. 全面分析今日与公司相关的舆情动态
2. 识别潜在风险和机会
3. 提供有价值的洞察和建议
4. 使用专业、清晰的语言

报告格式应当：
- 结构清晰，层次分明
- 重点突出，便于快速阅读
- 数据支撑，有理有据
- 语言精炼，避免冗余"""

        prompt = f"""请根据以下今日舆情监测数据，生成一份详细的高管舆情简报：

═══════════════════════════════════════════
📊 今日数据概览
═══════════════════════════════════════════
• 监测文章总数: {total} 篇
• 情感分布:
  - 积极: {positive} 篇 ({positive/total*100 if total > 0 else 0:.1f}%)
  - 消极: {negative} 篇 ({negative/total*100 if total > 0 else 0:.1f}%)
  - 中立: {neutral} 篇 ({neutral/total*100 if total > 0 else 0:.1f}%)
• 关键词热度: {keyword_text}

═══════════════════════════════════════════
📰 文章详情
═══════════════════════════════════════════
{articles_text}

═══════════════════════════════════════════

请生成舆情简报，包含以下部分：

【一、今日要点】
用2-3句话概括今日舆情的核心态势和关键发现。

【二、重点关注】
列出需要管理层特别关注的事项，包括：
- 消极内容分析（如有）
- 潜在风险预警
- 值得关注的新动态

【三、内容分析】
对各关键词相关内容进行简要分析，包括：
- 传播渠道特点
- 关键话题走向
- 舆论情绪变化

【四、建议与行动】
基于今日舆情给出具体、可执行的建议。

【五、明日关注】
预判明日可能的舆情走向和需关注的风险点。

请确保报告专业、详尽，为管理层决策提供有力支撑。"""

        self.logger.info("正在调用LLM生成舆情简报...")
        return self.chat(prompt, system_prompt, max_tokens=2000)


# 测试代码
if __name__ == "__main__":
    from crawlers.base import Article
    
    # 创建测试数据
    test_articles = [
        Article(
            title="砺思资本完成新一轮融资",
            author="投资界",
            content="砺思资本宣布完成融资",
            url="https://example.com/1",
            platform="微信公众号",
            keyword="砺思资本",
            sentiment="积极",
            sentiment_score=0.85,
        ),
        Article(
            title="Monolith Management招聘实习生",
            author="求职平台",
            content="投资实习机会",
            url="https://example.com/2",
            platform="微信公众号",
            keyword="Monolith",
            sentiment="积极",
            sentiment_score=0.75,
        ),
        Article(
            title="市场观察：投资行业面临挑战",
            author="财经观察",
            content="近期市场波动较大",
            url="https://example.com/3",
            platform="微信公众号",
            keyword="砺思资本",
            sentiment="消极",
            sentiment_score=0.25,
        ),
    ]
    
    # 测试LLM
    client = LLMClient()
    
    if client.is_configured():
        print("LLM配置完整，正在生成简报...")
        briefing = client.generate_briefing(test_articles)
        print("\n" + "="*50)
        print("舆情简报:")
        print("="*50)
        print(briefing)
    else:
        print("LLM未配置，请在 config/feishu.yaml 中添加 llm 配置")

