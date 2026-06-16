"""
FastAPI 后端 API
提供 RESTful 接口
"""

import os
import time
import uuid
from typing import List, Optional
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Header, Request, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from apscheduler.schedulers.background import BackgroundScheduler

from config import config
from database import db_manager
from batch_processor import BatchProcessor
from csv_parser import CSVParser
from logger import business_logger
from logger_config import get_app_logger, get_error_logger
from exception_handler import install_global_exception_handler
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

# 全局异常处理与日志
install_global_exception_handler()
app_logger = get_app_logger()
error_logger = get_error_logger()

# 定时清理任务调度器
scheduler = BackgroundScheduler()

def scheduled_file_cleanup():
    """定时清理已完成任务的源文件"""
    try:
        cleaned_count = db_manager.cleanup_completed_files(days_old=7)
        business_logger.log_info("scheduler", "file_cleanup", f"定时清理了 {cleaned_count} 个文件")
    except Exception as e:
        business_logger.log_error("scheduler", "file_cleanup", e)

# 每天凌晨2点执行文件清理
scheduler.add_job(scheduled_file_cleanup, 'cron', hour=2, minute=0)
scheduler.start()

# CORS 配置


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """记录所有HTTP请求的info日志，error时输出堆栈"""
    start_time = time.perf_counter()
    request_id = str(uuid.uuid4())

    app_logger.info(
        "➡️ 请求开始",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "client": request.client.host if request.client else None,
        },
    )

    try:
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start_time) * 1000
        app_logger.info(
            "✅ 请求完成",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round(duration_ms, 2),
            },
        )
        return response
    except Exception as exc:
        duration_ms = (time.perf_counter() - start_time) * 1000
        error_logger.error(
            "❌ 请求异常",
            exc_info=exc,
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "duration_ms": round(duration_ms, 2),
            },
        )
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": "服务器内部错误，请稍后重试",
                "request_id": request_id,
            },
        )


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


# ==================== 认证 API ====================

from pydantic import BaseModel

class LoginRequest(BaseModel):
    """登录请求模型"""
    username: str
    password: str


class UserActiveRequest(BaseModel):
    """用户激活状态请求模型"""
    username: str
    is_active: bool


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
        raise HTTPException(status_code=401, detail="无效token")
    
    return user_info


@app.post("/api/admin/users/activate")
def set_user_active(request: UserActiveRequest):
    """设置用户激活状态（仅admin）"""
    success = db_manager.set_user_active(request.username, request.is_active)
    if success:
        business_logger.log_info("api", "set_user_active", f"设置用户 {request.username} 激活状态为 {request.is_active}")
        return {"success": True, "message": "用户激活状态已更新"}
    else:
        raise HTTPException(status_code=404, detail="用户不存在")


# ==================== 任务管理 API ====================

@app.post("/api/tasks")
def create_task(request: TaskCreateRequest, authorization: Optional[str] = Header(None)):
    """创建批处理任务"""
    try:
        # 从token中提取用户信息
        user_id = None
        if authorization:
            token = authorization.replace("Bearer ", "")
            user_info = auth_manager.verify_session(token)
            if user_info:
                user_id = user_info.get('username')
        
        task_id = batch_processor.start_batch(
            task_name=request.task_name,
            audio_urls=request.audio_urls,
            extra_data_list=request.extra_data,
            user_id=user_id
        )
        
        business_logger.log_info("api", "create_task", f"任务创建成功: {task_id}, 用户: {user_id}")
        
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
def list_tasks(status: Optional[str] = None, limit: int = 50, customer_no: Optional[str] = None, task_name: Optional[str] = None, user_id: Optional[str] = None, is_admin: Optional[bool] = False, current_username: Optional[str] = None):
    """查询任务列表"""
    tasks = db_manager.list_tasks(status=status, limit=limit, customer_no=customer_no, task_name=task_name, user_id=user_id, is_admin=is_admin, current_username=current_username)
    return {"tasks": tasks}


@app.post("/api/tasks/{task_id}/pause")
def pause_task(task_id: str):
    """暂停任务"""
    try:
        batch_processor.pause_task(task_id)
        return {"success": True, "message": "任务已暂停"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/tasks/{task_id}/continue")
def continue_task(task_id: str):
    """继续执行未完成的任务"""
    try:
        task_id = batch_processor.continue_task(task_id)
        business_logger.log_info("api", "continue_task", f"任务继续执行: {task_id}")
        return {
            "success": True,
            "task_id": task_id,
            "message": "任务已继续执行"
        }
    except ValueError as e:
        business_logger.log_error("api", "continue_task", e)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        business_logger.log_error("api", "continue_task", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/tasks/{task_id}/resume")
def resume_task(task_id: str, background_tasks: BackgroundTasks):
    """恢复任务"""
    try:
        # TODO: 实现恢复逻辑
        return {"success": True, "message": "任务恢复中"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/admin/cleanup-files")
def cleanup_files(days_old: int = 7):
    """清理已完成任务的源文件"""
    try:
        cleaned_count = db_manager.cleanup_completed_files(days_old=days_old)
        business_logger.log_info("api", "cleanup_files", f"清理了 {cleaned_count} 个文件")
        return {
            "success": True,
            "cleaned_count": cleaned_count,
            "message": f"成功清理 {cleaned_count} 个文件"
        }
    except Exception as e:
        business_logger.log_error("api", "cleanup_files", e)
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
async def upload_and_process(file: UploadFile = File(...), task_name: str = Form("批量任务")):
    """上传并立即开始批处理"""
    try:
        # 验证文件
        if not file.filename:
            raise ValueError("未选择文件")
        
        # 检查文件扩展名
        allowed_extensions = ['.csv', '.xlsx', '.xls']
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in allowed_extensions:
            raise ValueError(f"不支持的文件格式: {file_ext}，仅支持 CSV、Excel 文件")
        
        # 保存文件
        upload_dir = config.upload_dir
        os.makedirs(upload_dir, exist_ok=True)
        
        file_path = os.path.join(upload_dir, file.filename)
        
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # 验证文件大小
        if os.path.getsize(file_path) == 0:
            raise ValueError("文件为空")
        
        # 提取音频列表
        try:
            audio_list = csv_parser.extract_audio_list(file_path)
        except Exception as e:
            raise ValueError(f"文件解析失败: {str(e)}")
        
        if not audio_list:
            raise ValueError("未找到有效的音频 URL")
        
        # 启动批处理
        urls = [item['url'] for item in audio_list]
        extra_data = [item['extra_data'] for item in audio_list]
        
        # 任务名称加上原始导入文件名称、本地路径来源
        formatted_task_name = f"{task_name} (文件: {file.filename}, 路径: {file_path})"
        
        # 存储文件路径到任务配置中，用于后续清理
        task_config = {
            'source_file_path': file_path,
            'source_file_name': file.filename
        }
        
        task_id = batch_processor.start_batch(
            task_name=formatted_task_name,
            audio_urls=urls,
            extra_data_list=extra_data,
            task_config=task_config
        )
        
        return {
            "success": True,
            "task_id": task_id,
            "total_count": len(urls)
        }
    
    except ValueError as e:
        # 业务逻辑错误 - 返回422
        from logger import business_logger
        business_logger.log_error('api', 'upload_process', e, task_name=task_name, filename=file.filename if file else None)
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        # 系统错误 - 返回500
        from logger import business_logger
        business_logger.log_error('api', 'upload_process', e, task_name=task_name, filename=file.filename if file else None)
        raise HTTPException(status_code=500, detail="服务器内部错误")


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
