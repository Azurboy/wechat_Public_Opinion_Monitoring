"""
平台登录 API
支持小红书、微信公众号平台的扫码登录
"""
import asyncio
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional
from threading import Thread
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import sys
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

router = APIRouter()
logger = logging.getLogger(__name__)

def _runtime_data_dir() -> Path:
    env_dir = os.environ.get("RUNTIME_DATA_DIR")
    if env_dir:
        p = Path(env_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p
    default = PROJECT_ROOT / "data"
    try:
        default.mkdir(parents=True, exist_ok=True)
        return default
    except Exception:
        tmp = Path("/tmp/monolith_data")
        tmp.mkdir(parents=True, exist_ok=True)
        return tmp

DATA_DIR = _runtime_data_dir()

# 登录状态存储
login_sessions: Dict[str, Dict] = {}


class LoginStatus(BaseModel):
    """登录状态"""
    platform: str
    status: str  # pending, waiting_scan, success, failed, timeout
    message: str = ""
    qrcode_url: Optional[str] = None
    session_id: Optional[str] = None


class PlatformStatus(BaseModel):
    """平台状态"""
    platform: str
    logged_in: bool
    cookie_file: Optional[str] = None
    last_login: Optional[str] = None


def get_cookie_file(platform: str) -> Path:
    """获取Cookie文件路径"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return DATA_DIR / f"{platform}_cookies.json"


def check_login_status(platform: str) -> bool:
    """检查平台登录状态"""
    cookie_file = get_cookie_file(platform)
    if cookie_file.exists():
        # 检查文件是否有效
        try:
            with open(cookie_file, 'r') as f:
                cookies = json.load(f)
            return len(cookies) > 0
        except Exception:
            return False
    return False


# ========== 小红书登录 ==========

def xhs_login_thread(session_id: str):
    """小红书登录线程"""
    global login_sessions
    
    try:
        from crawlers import XHSCrawler
        login_sessions[session_id]["status"] = "waiting_scan"
        login_sessions[session_id]["message"] = "请使用小红书APP扫描二维码"
        
        crawler = XHSCrawler(
            headless=False,
            cookie_file=str(get_cookie_file("xhs"))
        )
        
        def qr_callback(qr_url: str):
            login_sessions[session_id]["qrcode_url"] = qr_url
        
        success = crawler.login_by_qrcode(callback=qr_callback, timeout=120)
        
        if success:
            login_sessions[session_id]["status"] = "success"
            login_sessions[session_id]["message"] = "小红书登录成功"
        else:
            login_sessions[session_id]["status"] = "failed"
            login_sessions[session_id]["message"] = "登录失败或超时"
            
    except Exception as e:
        logger.error(f"小红书登录失败: {e}")
        login_sessions[session_id]["status"] = "failed"
        login_sessions[session_id]["message"] = str(e)


@router.post("/xhs/login", response_model=LoginStatus)
async def start_xhs_login():
    """启动小红书扫码登录"""
    session_id = f"xhs_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    login_sessions[session_id] = {
        "platform": "xiaohongshu",
        "status": "pending",
        "message": "正在初始化登录...",
        "qrcode_url": None,
        "session_id": session_id,
    }
    
    # 启动登录线程
    thread = Thread(target=xhs_login_thread, args=(session_id,))
    thread.start()
    
    return LoginStatus(**login_sessions[session_id])


@router.get("/xhs/status/{session_id}", response_model=LoginStatus)
async def get_xhs_login_status(session_id: str):
    """获取小红书登录状态"""
    if session_id not in login_sessions:
        raise HTTPException(status_code=404, detail="登录会话不存在")
    
    return LoginStatus(**login_sessions[session_id])


@router.get("/xhs/check", response_model=PlatformStatus)
async def check_xhs_status():
    """检查小红书登录状态"""
    cookie_file = get_cookie_file("xhs")
    logged_in = check_login_status("xhs")
    
    last_login = None
    if cookie_file.exists():
        mtime = os.path.getmtime(cookie_file)
        last_login = datetime.fromtimestamp(mtime).isoformat()
    
    return PlatformStatus(
        platform="xiaohongshu",
        logged_in=logged_in,
        cookie_file=str(cookie_file) if cookie_file.exists() else None,
        last_login=last_login,
    )


@router.delete("/xhs/logout")
async def xhs_logout():
    """清除小红书登录状态"""
    cookie_file = get_cookie_file("xhs")
    if cookie_file.exists():
        cookie_file.unlink()
    return {"status": "success", "message": "已退出登录"}


# ========== 微信公众号平台登录 ==========

def wechat_mp_login_thread(session_id: str):
    """微信公众号平台登录线程"""
    global login_sessions
    
    # #region agent log
    import json;open('/Users/zayn/ALL_Projects/Monolith_detective/.cursor/debug.log','a').write(json.dumps({"location":"auth.py:175","message":"wechat_mp_login_thread entry","data":{"session_id":session_id},"timestamp":int(time.time()*1000),"sessionId":"debug-session","runId":"initial","hypothesisId":"E"})+"\n")
    # #endregion
    
    try:
        from crawlers import WechatMPCrawler
        login_sessions[session_id]["status"] = "waiting_scan"
        login_sessions[session_id]["message"] = "请使用微信扫描二维码"
        
        cookie_file_path = str(get_cookie_file("wechat_mp"))
        
        # #region agent log
        open('/Users/zayn/ALL_Projects/Monolith_detective/.cursor/debug.log','a').write(json.dumps({"location":"auth.py:186","message":"before WechatMPCrawler init","data":{"cookie_file":cookie_file_path},"timestamp":int(time.time()*1000),"sessionId":"debug-session","runId":"initial","hypothesisId":"A,D,E"})+"\n")
        # #endregion
        
        crawler = WechatMPCrawler(
            headless=False,
            cookie_file=cookie_file_path
        )
        
        # #region agent log
        open('/Users/zayn/ALL_Projects/Monolith_detective/.cursor/debug.log','a').write(json.dumps({"location":"auth.py:192","message":"after WechatMPCrawler init","data":{"crawler_created":crawler is not None},"timestamp":int(time.time()*1000),"sessionId":"debug-session","runId":"initial","hypothesisId":"A,E"})+"\n")
        # #endregion
        
        def qr_callback(qr_url: str):
            login_sessions[session_id]["qrcode_url"] = qr_url
        
        success = crawler.login_by_qrcode(callback=qr_callback, timeout=120)
        
        if success:
            login_sessions[session_id]["status"] = "success"
            login_sessions[session_id]["message"] = "微信公众号平台登录成功"
        else:
            login_sessions[session_id]["status"] = "failed"
            login_sessions[session_id]["message"] = "登录失败或超时"
            
    except Exception as e:
        # #region agent log
        open('/Users/zayn/ALL_Projects/Monolith_detective/.cursor/debug.log','a').write(json.dumps({"location":"auth.py:202","message":"wechat_mp_login_thread exception","data":{"error":str(e),"error_type":type(e).__name__},"timestamp":int(time.time()*1000),"sessionId":"debug-session","runId":"initial","hypothesisId":"A,B,E"})+"\n")
        # #endregion
        logger.error(f"微信公众号平台登录失败: {e}")
        login_sessions[session_id]["status"] = "failed"
        login_sessions[session_id]["message"] = str(e)


@router.post("/wechat/login", response_model=LoginStatus)
async def start_wechat_login():
    """启动微信公众号平台扫码登录"""
    session_id = f"wechat_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    login_sessions[session_id] = {
        "platform": "wechat_mp",
        "status": "pending",
        "message": "正在初始化登录...",
        "qrcode_url": None,
        "session_id": session_id,
    }
    
    thread = Thread(target=wechat_mp_login_thread, args=(session_id,))
    thread.start()
    
    return LoginStatus(**login_sessions[session_id])


@router.get("/wechat/status/{session_id}", response_model=LoginStatus)
async def get_wechat_login_status(session_id: str):
    """获取微信公众号平台登录状态"""
    if session_id not in login_sessions:
        raise HTTPException(status_code=404, detail="登录会话不存在")
    
    return LoginStatus(**login_sessions[session_id])


@router.get("/wechat/check", response_model=PlatformStatus)
async def check_wechat_status():
    """检查微信公众号平台登录状态"""
    cookie_file = get_cookie_file("wechat_mp")
    logged_in = check_login_status("wechat_mp")
    
    last_login = None
    if cookie_file.exists():
        mtime = os.path.getmtime(cookie_file)
        last_login = datetime.fromtimestamp(mtime).isoformat()
    
    return PlatformStatus(
        platform="wechat_mp",
        logged_in=logged_in,
        cookie_file=str(cookie_file) if cookie_file.exists() else None,
        last_login=last_login,
    )


@router.delete("/wechat/logout")
async def wechat_logout():
    """清除微信公众号平台登录状态"""
    cookie_file = get_cookie_file("wechat_mp")
    if cookie_file.exists():
        cookie_file.unlink()
    return {"status": "success", "message": "已退出登录"}


# ========== 通用接口 ==========

@router.get("/platforms")
async def get_all_platforms_status():
    """获取所有平台登录状态"""
    platforms = ["xhs", "wechat_mp"]
    result = []
    
    for platform in platforms:
        cookie_file = get_cookie_file(platform)
        logged_in = check_login_status(platform)
        
        last_login = None
        if cookie_file.exists():
            mtime = os.path.getmtime(cookie_file)
            last_login = datetime.fromtimestamp(mtime).isoformat()
        
        result.append({
            "platform": platform,
            "logged_in": logged_in,
            "last_login": last_login,
        })
    
    return result

