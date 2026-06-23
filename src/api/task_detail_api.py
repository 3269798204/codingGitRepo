"""
FastAPI 路由 - 提供任务详情HTML页面访问
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import os
from pathlib import Path

import os, sys
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from src.web.task_detail_page import page_generator
from src.core.config import config

app = FastAPI(
    title="语音识别分析系统 - 任务详情服务",
    description="提供任务详情HTML页面访问",
    version="1.0.0"
)

# 挂载静态文件目录
results_dir = config.base_dir / "results"
if results_dir.exists():
    app.mount("/static", StaticFiles(directory=str(results_dir)), name="static")


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "语音识别分析系统 - 任务详情服务",
        "version": "1.0.0",
        "endpoints": {
            "task_detail": "/task/{task_id}",
            "health": "/health"
        }
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}


@app.get("/task/{task_id}", response_class=HTMLResponse)
async def get_task_detail(task_id: str):
    """
    获取任务详情HTML页面
    
    Args:
        task_id: 任务ID
        
    Returns:
        HTML页面内容
    """
    try:
        # 生成HTML页面
        html_filepath = page_generator.generate_task_detail_html(task_id)
        
        # 检查文件是否存在
        if not os.path.exists(html_filepath):
            raise HTTPException(status_code=404, detail="任务详情页面生成失败")
        
        # 返回HTML文件
        return FileResponse(
            path=html_filepath,
            media_type="text/html",
            filename=f"{task_id}.html"
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"服务器错误: {str(e)}")


@app.get("/api/task/{task_id}")
async def get_task_detail_api(task_id: str):
    """
    获取任务详情JSON数据（API接口）
    
    Args:
        task_id: 任务ID
        
    Returns:
        JSON格式的任务详情
    """
    from src.db.database import db_manager
    
    task_data = db_manager.get_task_with_results(task_id)
    
    if not task_data:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    return task_data


if __name__ == "__main__":
    import uvicorn
    
    print("=" * 60)
    print("🚀 启动任务详情服务...")
    print("=" * 60)
    print(f"📍 服务地址: http://localhost:8001")
    print(f"📄 任务详情: http://localhost:8001/task/<task_id>")
    print(f"💚 健康检查: http://localhost:8001/health")
    print("=" * 60)
    
    uvicorn.run(app, host="0.0.0.0", port=8001)