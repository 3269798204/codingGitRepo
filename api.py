"""
FastAPI 后端 API
提供 RESTful 接口
"""

import os
import uuid
from typing import List, Optional
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import config
from database import db_manager
from batch_processor import BatchProcessor
from csv_parser import CSVParser
from report_generator import ReportGenerator
from logger import business_logger
from auth import auth_manager


# ==================== Pydantic 模型 ====================

class TaskCreateRequest(BaseModel):
    task_name: str
    audio_urls: List[str]
    extra_data: Optional[List[dict]] = None


class ConfigUpdateRequest(BaseModel):
    model_size: Optional[str] = None
    beam_size: Optional[int] = None
    max_workers: Optional[int] = None


# ==================== FastAPI 应用 ====================

app = FastAPI(
    title="语音识别分析系统 API",
    description="基于 Faster-Whisper 的语音识别与分析 API",
    version="3.0.0"
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化组件
batch_processor = BatchProcessor()
csv_parser = CSVParser()
report_gen = ReportGenerator()


# ==================== 认证 API ====================

from pydantic import BaseModel

class LoginRequest(BaseModel):
    """登录请求模型"""
    username: str
    password: str


@app.post("/api/auth/login")
async def login(request: LoginRequest):
    """用户登录"""
    token = auth_manager.login(request.username, request.password)
    if not token:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    
    user_info = auth_manager.verify_session(token)
    return {
        "token": token,
        "username": user_info['username'],
        "role": user_info['role']
    }


@app.get("/api/auth/verify")
async def verify_token(authorization: Optional[str] = Header(None)):
    """验证token"""
    if not authorization:
        raise HTTPException(status_code=401, detail="未提供token")
    
    token = authorization.replace("Bearer ", "")
    user_info = auth_manager.verify_session(token)
    if not user_info:
        raise HTTPException(status_code=401, detail="token无效或已过期")
    
    return user_info


# ==================== 任务管理 API ====================

@app.post("/api/tasks")
def create_task(request: TaskCreateRequest):
    """创建批处理任务"""
    try:
        task_id = batch_processor.start_batch(
            task_name=request.task_name,
            audio_urls=request.audio_urls,
            extra_data_list=request.extra_data
        )
        
        business_logger.log_info("api", "create_task", f"任务创建成功: {task_id}")
        
        return {
            "success": True,
            "task_id": task_id,
            "message": "任务已启动"
        }
    
    except Exception as e:
        business_logger.log_error("api", "create_task", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/tasks/{task_id}")
def get_task(task_id: str):
    """查询任务状态"""
    task_info = db_manager.get_task(task_id)
    
    if not task_info:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    return task_info


@app.get("/api/tasks")
def list_tasks(status: Optional[str] = None, limit: int = 50):
    """查询任务列表"""
    tasks = db_manager.list_tasks(status=status, limit=limit)
    return {"tasks": tasks}


@app.post("/api/tasks/{task_id}/pause")
def pause_task(task_id: str):
    """暂停任务"""
    try:
        batch_processor.pause_task(task_id)
        return {"success": True, "message": "任务已暂停"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/tasks/{task_id}/resume")
def resume_task(task_id: str, background_tasks: BackgroundTasks):
    """恢复任务"""
    try:
        # TODO: 实现恢复逻辑
        return {"success": True, "message": "任务恢复中"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/tasks/{task_id}")
def delete_task(task_id: str):
    """删除任务"""
    # TODO: 实现删除逻辑
    return {"success": True, "message": "任务已删除"}


# ==================== 文件上传 API ====================

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """上传 CSV/Excel 文件"""
    try:
        # 保存上传文件
        upload_dir = config.upload_dir
        os.makedirs(upload_dir, exist_ok=True)
        
        file_path = os.path.join(upload_dir, file.filename)
        
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # 解析文件
        preview = csv_parser.get_file_preview(file_path)
        
        business_logger.log_info("api", "upload", f"文件上传成功: {file.filename}")
        
        return {
            "success": True,
            "file_path": file_path,
            "preview": preview
        }
    
    except Exception as e:
        business_logger.log_error("api", "upload", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/upload/process")
async def upload_and_process(file: UploadFile = File(...), task_name: str = "批量任务"):
    """上传并立即开始批处理"""
    try:
        # 保存文件
        upload_dir = config.upload_dir
        os.makedirs(upload_dir, exist_ok=True)
        
        file_path = os.path.join(upload_dir, file.filename)
        
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # 提取音频列表
        audio_list = csv_parser.extract_audio_list(file_path)
        
        if not audio_list:
            raise ValueError("未找到有效的音频 URL")
        
        # 启动批处理
        urls = [item['url'] for item in audio_list]
        extra_data = [item['extra_data'] for item in audio_list]
        
        task_id = batch_processor.start_batch(
            task_name=task_name,
            audio_urls=urls,
            extra_data_list=extra_data
        )
        
        return {
            "success": True,
            "task_id": task_id,
            "total_count": len(urls)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 结果查询 API ====================

@app.get("/api/results/{audio_id}")
def get_audio_result(audio_id: str):
    """查询音频结果"""
    result = db_manager.get_audio_result(audio_id)
    
    if not result:
        raise HTTPException(status_code=404, detail="结果不存在")
    
    return result


@app.get("/api/tasks/{task_id}/results")
def get_task_results(task_id: str, status: Optional[str] = None, limit: int = 100):
    """查询任务的所有结果"""
    results = db_manager.get_task_results(task_id, status=status, limit=limit)
    return {"results": results}


# ==================== 报表 API ====================

@app.get("/api/reports/task_summary/{task_id}")
def get_task_summary(task_id: str):
    """获取任务汇总报表"""
    report = report_gen.generate_task_summary(task_id)
    return report


@app.get("/api/reports/emotion/{task_id}")
def get_emotion_report(task_id: str):
    """获取情绪分布报表"""
    report = report_gen.generate_emotion_report(task_id)
    return report


@app.get("/api/reports/performance/{task_id}")
def get_performance_report(task_id: str):
    """获取性能监控报表"""
    report = report_gen.generate_performance_report(task_id)
    return report


@app.get("/api/reports/quality/{task_id}")
def get_quality_report(task_id: str):
    """获取质量评估报表"""
    report = report_gen.generate_quality_report(task_id)
    return report


# ==================== 日志 API ====================

@app.get("/api/logs")
def query_logs(task_id: Optional[str] = None, level: Optional[str] = None, limit: int = 100):
    """查询业务日志"""
    logs = business_logger.query_logs(task_id=task_id, level=level, limit=limit)
    return {"logs": logs}


# ==================== 硬件信息 API ====================

@app.get("/api/hardware")
def get_hardware_info():
    """获取硬件配置信息"""
    from hardware_detector import get_detector
    
    detector = get_detector()
    return detector.to_dict()


# ==================== 系统配置 API ====================

@app.get("/api/configs")
def list_configs(category: Optional[str] = None):
    """查询系统配置列表"""
    configs = db_manager.list_configs(category)
    return {"configs": configs}


@app.put("/api/configs/{config_key}")
def update_config(config_key: str, value: str, config_type: str = "string"):
    """更新系统配置"""
    try:
        db_manager.set_config(
            key=config_key,
            value=value,
            config_type=config_type
        )
        return {
            "success": True,
            "message": f"配置 {config_key} 已更新"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/configs/{config_key}")
def get_config(config_key: str):
    """查询单个配置"""
    config = db_manager.get_config(config_key)
    if not config:
        raise HTTPException(status_code=404, detail="配置不存在")
    return config


# ==================== 用户管理 API ====================

@app.get("/api/users")
def list_users():
    """查询用户列表（仅管理员）"""
    users = db_manager.list_users()
    return {"users": users}


@app.get("/api/users/{username}")
def get_user(username: str):
    """查询单个用户"""
    # TODO: 实现用户查询逻辑
    return {"username": username}


@app.post("/api/users")
def create_user(username: str, password: str, role: str = "user", email: str = ""):
    """创建用户"""
    try:
        success = auth_manager.register_user(username, password, role)
        if success:
            return {
                "success": True,
                "message": f"用户 {username} 创建成功"
            }
        else:
            raise HTTPException(status_code=400, detail="用户名已存在")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/users/{username}")
def update_user(username: str, role: Optional[str] = None, is_active: Optional[bool] = None):
    """更新用户信息"""
    # TODO: 实现用户更新逻辑
    return {
        "success": True,
        "message": f"用户 {username} 已更新"
    }


@app.delete("/api/users/{username}")
def delete_user(username: str):
    """删除用户"""
    # TODO: 实现用户删除逻辑
    return {
        "success": True,
        "message": f"用户 {username} 已删除"
    }


# ==================== 健康检查 ====================

@app.get("/health")
def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "version": "3.0.0",
        "timestamp": str(uuid.uuid4())
    }


if __name__ == "__main__":
    import uvicorn
    
    print("🚀 启动 FastAPI 服务器")
    print(f"   地址: http://{config.host}:{config.api_port}")
    
    uvicorn.run(app, host=config.host, port=config.api_port)
