"""
配置管理 API
管理飞书配置、关键词配置、平台配置等
"""
import os
from pathlib import Path
from typing import Dict, List, Any, Optional

import yaml
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

# 配置文件路径
CONFIG_DIR = Path(__file__).parent.parent.parent / "config"


class FeishuConfig(BaseModel):
    """飞书配置"""
    app_id: str = ""
    app_secret: str = ""
    bitable_app_token: str = ""
    bitable_table_id: str = ""
    webhook_url: str = ""


class LLMConfig(BaseModel):
    """LLM配置"""
    provider: str = "siliconflow"
    model: str = "deepseek-ai/DeepSeek-V3"
    api_key: str = ""
    base_url: str = "https://api.siliconflow.cn/v1"


class KeywordsConfig(BaseModel):
    """关键词配置"""
    keywords: List[str] = []
    relevance_keywords: Dict[str, List[str]] = {}
    max_pages: int = 3
    request_delay: int = 3


class PlatformConfig(BaseModel):
    """平台配置"""
    wechat_method: str = "sogou"  # sogou / mp
    xhs_enabled: bool = True
    xhs_sort: str = "time_descending"
    filter_hours: int = 48


def load_yaml(file_path: Path) -> dict:
    """加载YAML文件"""
    if not file_path.exists():
        return {}
    with open(file_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f) or {}


def save_yaml(file_path: Path, data: dict):
    """保存YAML文件"""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False)


# ========== 飞书配置 ==========

@router.get("/feishu", response_model=FeishuConfig)
async def get_feishu_config():
    """获取飞书配置"""
    config = load_yaml(CONFIG_DIR / "feishu.yaml")
    bitable = config.get("bitable", {})
    webhook = config.get("webhook", {})
    
    return FeishuConfig(
        app_id=config.get("app_id", ""),
        app_secret=config.get("app_secret", ""),
        bitable_app_token=bitable.get("app_token", ""),
        bitable_table_id=bitable.get("table_id", ""),
        webhook_url=webhook.get("url", ""),
    )


@router.post("/feishu")
async def save_feishu_config(config: FeishuConfig):
    """保存飞书配置"""
    data = load_yaml(CONFIG_DIR / "feishu.yaml")
    
    data["app_id"] = config.app_id
    data["app_secret"] = config.app_secret
    data.setdefault("bitable", {})
    data["bitable"]["app_token"] = config.bitable_app_token
    data["bitable"]["table_id"] = config.bitable_table_id
    data.setdefault("webhook", {})
    data["webhook"]["url"] = config.webhook_url
    
    save_yaml(CONFIG_DIR / "feishu.yaml", data)
    return {"status": "success", "message": "飞书配置已保存"}


# ========== LLM配置 ==========

@router.get("/llm", response_model=LLMConfig)
async def get_llm_config():
    """获取LLM配置"""
    config = load_yaml(CONFIG_DIR / "feishu.yaml")
    llm = config.get("llm", {})
    
    return LLMConfig(
        provider=llm.get("provider", "siliconflow"),
        model=llm.get("model", "deepseek-ai/DeepSeek-V3"),
        api_key=llm.get("api_key", ""),
        base_url=llm.get("base_url", "https://api.siliconflow.cn/v1"),
    )


@router.post("/llm")
async def save_llm_config(config: LLMConfig):
    """保存LLM配置"""
    data = load_yaml(CONFIG_DIR / "feishu.yaml")
    
    data.setdefault("llm", {})
    data["llm"]["provider"] = config.provider
    data["llm"]["model"] = config.model
    data["llm"]["api_key"] = config.api_key
    data["llm"]["base_url"] = config.base_url
    
    save_yaml(CONFIG_DIR / "feishu.yaml", data)
    return {"status": "success", "message": "LLM配置已保存"}


# ========== 关键词配置 ==========

@router.get("/keywords", response_model=KeywordsConfig)
async def get_keywords_config():
    """获取关键词配置"""
    config = load_yaml(CONFIG_DIR / "keywords.yaml")
    search = config.get("search", {})
    
    return KeywordsConfig(
        keywords=config.get("keywords", []),
        relevance_keywords=config.get("relevance_keywords", {}),
        max_pages=search.get("max_pages", 3),
        request_delay=search.get("request_delay", 3),
    )


@router.post("/keywords")
async def save_keywords_config(config: KeywordsConfig):
    """保存关键词配置"""
    data = load_yaml(CONFIG_DIR / "keywords.yaml")
    
    data["keywords"] = config.keywords
    data["relevance_keywords"] = config.relevance_keywords
    data.setdefault("search", {})
    data["search"]["max_pages"] = config.max_pages
    data["search"]["request_delay"] = config.request_delay
    
    save_yaml(CONFIG_DIR / "keywords.yaml", data)
    return {"status": "success", "message": "关键词配置已保存"}


@router.post("/keywords/add")
async def add_keyword(keyword: str):
    """添加关键词"""
    config = load_yaml(CONFIG_DIR / "keywords.yaml")
    keywords = config.get("keywords", [])
    
    if keyword not in keywords:
        keywords.append(keyword)
        config["keywords"] = keywords
        save_yaml(CONFIG_DIR / "keywords.yaml", config)
        return {"status": "success", "message": f"关键词 '{keyword}' 已添加"}
    
    return {"status": "exists", "message": f"关键词 '{keyword}' 已存在"}


@router.delete("/keywords/{keyword}")
async def delete_keyword(keyword: str):
    """删除关键词"""
    config = load_yaml(CONFIG_DIR / "keywords.yaml")
    keywords = config.get("keywords", [])
    
    if keyword in keywords:
        keywords.remove(keyword)
        config["keywords"] = keywords
        save_yaml(CONFIG_DIR / "keywords.yaml", config)
        return {"status": "success", "message": f"关键词 '{keyword}' 已删除"}
    
    raise HTTPException(status_code=404, detail=f"关键词 '{keyword}' 不存在")


# ========== 平台配置 ==========

@router.get("/platforms", response_model=PlatformConfig)
async def get_platforms_config():
    """获取平台配置"""
    config = load_yaml(CONFIG_DIR / "platforms.yaml")
    wechat = config.get("wechat", {})
    xhs = config.get("xiaohongshu", {})
    
    return PlatformConfig(
        wechat_method=wechat.get("method", "sogou"),
        xhs_enabled=xhs.get("enabled", True),
        xhs_sort=xhs.get("sort", "time_descending"),
        filter_hours=xhs.get("filter_hours", 48),
    )


@router.post("/platforms")
async def save_platforms_config(config: PlatformConfig):
    """保存平台配置"""
    data = load_yaml(CONFIG_DIR / "platforms.yaml")
    
    data.setdefault("wechat", {})
    data["wechat"]["method"] = config.wechat_method
    
    data.setdefault("xiaohongshu", {})
    data["xiaohongshu"]["enabled"] = config.xhs_enabled
    data["xiaohongshu"]["sort"] = config.xhs_sort
    data["xiaohongshu"]["filter_hours"] = config.filter_hours
    
    save_yaml(CONFIG_DIR / "platforms.yaml", data)
    return {"status": "success", "message": "平台配置已保存"}


# ========== 配置验证 ==========

@router.get("/validate")
async def validate_config():
    """验证所有配置"""
    results = {
        "feishu": False,
        "llm": False,
        "keywords": False,
        "details": {}
    }
    
    # 检查飞书配置
    feishu = load_yaml(CONFIG_DIR / "feishu.yaml")
    if feishu.get("app_id") and feishu.get("app_secret"):
        results["feishu"] = True
        results["details"]["feishu"] = "配置完整"
    else:
        results["details"]["feishu"] = "缺少 app_id 或 app_secret"
    
    # 检查LLM配置
    llm = feishu.get("llm", {})
    if llm.get("api_key"):
        results["llm"] = True
        results["details"]["llm"] = f"使用模型: {llm.get('model', 'unknown')}"
    else:
        results["details"]["llm"] = "缺少 API Key"
    
    # 检查关键词配置
    keywords = load_yaml(CONFIG_DIR / "keywords.yaml")
    if keywords.get("keywords"):
        results["keywords"] = True
        results["details"]["keywords"] = f"已配置 {len(keywords['keywords'])} 个关键词"
    else:
        results["details"]["keywords"] = "未配置关键词"
    
    return results



