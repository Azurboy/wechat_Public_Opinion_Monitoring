"""
飞书多维表格客户端
用于将采集的数据写入飞书多维表格
"""
import hashlib
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging

import yaml
import lark_oapi as lark
from lark_oapi.api.bitable.v1 import *
from lark_oapi.api.auth.v3 import *

from crawlers.base import Article

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FeishuClient:
    """飞书多维表格客户端"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化飞书客户端
        
        Args:
            config_path: 飞书配置文件路径，默认为项目根目录下的 config/feishu.yaml
        """
        # 如果未指定路径，自动查找项目根目录
        if config_path is None:
            from pathlib import Path
            current_file = Path(__file__).resolve()
            project_root = current_file.parent.parent
            config_path = str(project_root / "config" / "feishu.yaml")
        
        self.config = self._load_config(config_path)
        self.app_id = self.config.get("app_id", "")
        self.app_secret = self.config.get("app_secret", "")
        
        bitable_config = self.config.get("bitable", {})
        self.app_token = bitable_config.get("app_token", "")
        self.table_id = bitable_config.get("table_id", "")
        
        self.webhook_url = self.config.get("webhook", {}).get("url", "")
        
        # 检查配置是否完整
        self._validate_config()
        
        # 初始化飞书客户端
        self.client = lark.Client.builder() \
            .app_id(self.app_id) \
            .app_secret(self.app_secret) \
            .log_level(lark.LogLevel.WARNING) \
            .build()
        
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def _load_config(self, config_path: str) -> dict:
        """加载配置文件"""
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except FileNotFoundError:
            logger.warning(f"配置文件不存在: {config_path}")
            return {}
        except Exception as e:
            logger.warning(f"加载配置文件失败 ({config_path}): {e}")
            return {}
    
    def _validate_config(self):
        """验证配置是否完整"""
        missing = []
        if not self.app_id:
            missing.append("app_id")
        if not self.app_secret:
            missing.append("app_secret")
        if not self.app_token:
            missing.append("bitable.app_token")
        if not self.table_id:
            missing.append("bitable.table_id")
        
        if missing:
            logger.warning(f"飞书配置缺失: {', '.join(missing)}")
            logger.warning("请在 config/feishu.yaml 中填写完整配置")
    
    def is_configured(self) -> bool:
        """检查是否已配置"""
        return all([self.app_id, self.app_secret, self.app_token, self.table_id])
    
    def _generate_record_id(self, article: Article) -> str:
        """
        生成文章的唯一标识，用于去重
        基于URL生成MD5哈希
        """
        return hashlib.md5(article.url.encode()).hexdigest()[:16]
    
    def _build_fields(self, article: Article) -> Dict[str, Any]:
        """
        构建飞书多维表格字段
        字段名必须与飞书表格中的字段名完全一致
        
        Args:
            article: 文章对象
            
        Returns:
            字段字典
        """
        fields = {
            "标题": article.title or "",
            "作者": article.author or "",
            "内容摘要": (article.content[:500] if article.content else ""),
            "平台": article.platform or "",
            "关键词": article.keyword or "",
            "情感标注": article.sentiment or "待分析",
            "记录ID": self._generate_record_id(article),
        }
        
        # URL字段（类型15需要特殊格式）
        if article.url:
            fields["原文链接"] = {
                "link": article.url,
                "text": article.title[:30] if article.title else "查看原文"
            }
        
        # 日期字段（类型5需要毫秒时间戳）
        if article.published_at:
            fields["发布日期"] = int(article.published_at.timestamp() * 1000)
        if article.crawled_at:
            fields["采集日期"] = int(article.crawled_at.timestamp() * 1000)
        
        # 情感分数
        if article.sentiment_score is not None:
            fields["情感分数"] = str(article.sentiment_score)
        
        # 过滤空值和None
        return {k: v for k, v in fields.items() if v is not None and v != ""}
    
    def add_record(self, article: Article) -> Optional[str]:
        """
        添加单条记录到多维表格
        
        Args:
            article: 文章对象
            
        Returns:
            记录ID，失败返回None
        """
        if not self.is_configured():
            self.logger.error("飞书配置不完整，无法写入数据")
            return None
        
        # 构建记录字段（简化版，全部文本类型）
        fields = self._build_fields(article)
        
        try:
            request = CreateAppTableRecordRequest.builder() \
                .app_token(self.app_token) \
                .table_id(self.table_id) \
                .request_body(AppTableRecord.builder()
                    .fields(fields)
                    .build()) \
                .build()
            
            response = self.client.bitable.v1.app_table_record.create(request)
            
            if not response.success():
                self.logger.error(f"添加记录失败: {response.code} - {response.msg}")
                return None
            
            record_id = response.data.record.record_id
            self.logger.info(f"成功添加记录: {article.title[:30]}...")
            return record_id
            
        except Exception as e:
            self.logger.error(f"添加记录异常: {e}")
            return None
    
    def add_records_batch(self, articles: List[Article]) -> Dict[str, Any]:
        """
        批量添加记录到多维表格
        
        Args:
            articles: 文章列表
            
        Returns:
            包含成功和失败数量的结果
        """
        if not self.is_configured():
            self.logger.error("飞书配置不完整，无法写入数据")
            return {"success": 0, "failed": len(articles), "records": []}
        
        success_count = 0
        failed_count = 0
        record_ids = []
        
        # 构建批量记录（简化版，全部文本类型）
        records = []
        for article in articles:
            fields = self._build_fields(article)
            records.append(AppTableRecord.builder().fields(fields).build())
        
        # 分批处理（飞书API单次最多500条）
        batch_size = 100
        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]
            
            try:
                request = BatchCreateAppTableRecordRequest.builder() \
                    .app_token(self.app_token) \
                    .table_id(self.table_id) \
                    .request_body(BatchCreateAppTableRecordRequestBody.builder()
                        .records(batch)
                        .build()) \
                    .build()
                
                response = self.client.bitable.v1.app_table_record.batch_create(request)
                
                if response.success():
                    batch_records = response.data.records
                    success_count += len(batch_records)
                    record_ids.extend([r.record_id for r in batch_records])
                    self.logger.info(f"批量添加成功: {len(batch_records)} 条")
                else:
                    failed_count += len(batch)
                    self.logger.error(f"批量添加失败: {response.code} - {response.msg}")
                
                # 批次间隔，避免触发频率限制
                if i + batch_size < len(records):
                    time.sleep(0.5)
                    
            except Exception as e:
                failed_count += len(batch)
                self.logger.error(f"批量添加异常: {e}")
        
        return {
            "success": success_count,
            "failed": failed_count,
            "records": record_ids
        }
    
    def get_existing_record_ids(self) -> set:
        """
        获取已存在的记录ID，用于去重
        
        Returns:
            已存在的记录ID集合
        """
        if not self.is_configured():
            return set()
        
        existing_ids = set()
        page_token = None
        
        try:
            while True:
                request_builder = ListAppTableRecordRequest.builder() \
                    .app_token(self.app_token) \
                    .table_id(self.table_id) \
                    .page_size(500) \
                    .field_names('["记录ID"]')
                
                if page_token:
                    request_builder.page_token(page_token)
                
                request = request_builder.build()
                response = self.client.bitable.v1.app_table_record.list(request)
                
                if not response.success():
                    self.logger.error(f"获取记录失败: {response.code} - {response.msg}")
                    break
                
                for record in response.data.items or []:
                    record_id = record.fields.get("记录ID")
                    if record_id:
                        existing_ids.add(record_id)
                
                if not response.data.has_more:
                    break
                    
                page_token = response.data.page_token
                
        except Exception as e:
            self.logger.error(f"获取记录异常: {e}")
        
        self.logger.info(f"已有 {len(existing_ids)} 条记录")
        return existing_ids
    
    def add_new_articles(self, articles: List[Article]) -> Dict[str, Any]:
        """
        添加新文章（自动去重）
        
        Args:
            articles: 文章列表
            
        Returns:
            结果统计
        """
        if not articles:
            return {"success": 0, "failed": 0, "skipped": 0}
        
        # 获取已存在的记录
        existing_ids = self.get_existing_record_ids()
        
        # 过滤出新文章
        new_articles = []
        skipped = 0
        for article in articles:
            record_id = self._generate_record_id(article)
            if record_id not in existing_ids:
                new_articles.append(article)
            else:
                skipped += 1
        
        self.logger.info(f"过滤后: {len(new_articles)} 条新文章, {skipped} 条已存在")
        
        if not new_articles:
            return {"success": 0, "failed": 0, "skipped": skipped}
        
        # 批量添加新文章
        result = self.add_records_batch(new_articles)
        result["skipped"] = skipped
        
        return result
    
    def send_webhook_message(self, message: str) -> bool:
        """
        通过Webhook发送消息到飞书群
        
        Args:
            message: 消息内容
            
        Returns:
            是否发送成功
        """
        if not self.webhook_url:
            self.logger.warning("Webhook URL未配置")
            return False
        
        import requests
        
        try:
            payload = {
                "msg_type": "text",
                "content": {
                    "text": message
                }
            }
            
            response = requests.post(self.webhook_url, json=payload, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                if result.get("code") == 0:
                    self.logger.info("Webhook消息发送成功")
                    return True
                else:
                    self.logger.error(f"Webhook发送失败: {result}")
                    return False
            else:
                self.logger.error(f"Webhook请求失败: {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"Webhook发送异常: {e}")
            return False


# 测试代码
if __name__ == "__main__":
    from crawlers.base import Article
    from datetime import datetime
    
    # 创建测试文章
    test_article = Article(
        title="测试文章标题",
        author="测试公众号",
        content="这是一篇测试文章的摘要内容。",
        url="https://mp.weixin.qq.com/test/123",
        platform="微信公众号",
        keyword="Monolith",
        published_at=datetime.now(),
    )
    
    # 测试飞书客户端
    client = FeishuClient()
    
    if client.is_configured():
        print("飞书配置完整，可以使用")
        # result = client.add_record(test_article)
        # print(f"添加结果: {result}")
    else:
        print("飞书配置不完整，请先配置 config/feishu.yaml")
        print("配置步骤:")
        print("1. 访问 https://open.feishu.cn/ 创建应用")
        print("2. 获取 App ID 和 App Secret")
        print("3. 添加「多维表格」权限")
        print("4. 创建多维表格，获取 app_token 和 table_id")
        print("5. 将配置填入 config/feishu.yaml")

