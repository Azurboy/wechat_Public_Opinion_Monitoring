// 舆情监测系统 - 前端交互
console.log('舆情监测系统已加载');

// 快速采集功能
async function quickCrawl() {
    const button = event.target;
    const originalText = button.textContent;
    
    try {
        button.disabled = true;
        button.textContent = '采集中...';
        
        const response = await fetch('/api/crawl/quick?platforms=wechat', {
            method: 'POST'
        });
        
        if (!response.ok) {
            throw new Error('采集失败');
        }
        
        const result = await response.json();
        alert(`采集成功！共获取 ${result.total} 篇文章`);
        
        // 刷新页面数据
        location.reload();
        
    } catch (error) {
        console.error('采集失败:', error);
        alert('采集失败，请查看控制台日志');
    } finally {
        button.disabled = false;
        button.textContent = originalText;
    }
}

// 生成AI简报
async function generateBriefing() {
    const button = event.target;
    const originalText = button.textContent;
    
    try {
        button.disabled = true;
        button.textContent = '生成中...';
        
        const response = await fetch('/api/reports/briefing', {
            method: 'POST'
        });
        
        if (!response.ok) {
            throw new Error('生成失败');
        }
        
        const result = await response.json();
        
        // 显示简报内容
        const modal = document.createElement('div');
        modal.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.8);display:flex;align-items:center;justify-content:center;z-index:9999;';
        modal.innerHTML = `
            <div style="background:#1a1a1a;padding:2rem;border-radius:12px;max-width:800px;max-height:80vh;overflow-y:auto;color:#fff;">
                <h2 style="margin-top:0;">🤖 AI舆情简报</h2>
                <pre style="white-space:pre-wrap;line-height:1.6;">${result.briefing || result.report}</pre>
                <button onclick="this.parentElement.parentElement.remove()" style="margin-top:1rem;padding:0.5rem 1rem;background:#6366f1;border:none;border-radius:6px;color:#fff;cursor:pointer;">关闭</button>
            </div>
        `;
        document.body.appendChild(modal);
        
    } catch (error) {
        console.error('生成失败:', error);
        alert('生成失败，请确保已配置LLM API Key');
    } finally {
        button.disabled = false;
        button.textContent = originalText;
    }
}

// 绑定事件（使用事件委托）
document.addEventListener('click', function(e) {
    // 快速采集按钮
    if (e.target.textContent.includes('快速采集') && e.target.tagName === 'BUTTON') {
        quickCrawl.call(null, e);
    }
    
    // AI简报按钮
    if (e.target.textContent.includes('生成AI智能简报') && e.target.tagName === 'BUTTON') {
        generateBriefing.call(null, e);
    }
});
