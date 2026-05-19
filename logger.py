"""
业务日志模块
结构化日志记录，支持 MySQL 持久化
"""

import sys
import traceback
from datetime import datetime
from typing import Optional
from loguru import logger

from database import db_manager


class BusinessLogger:
    """业务日志管理器"""
    
    def __init__(self):
        # 配置 loguru
        logger.remove()  # 移除默认处理器
        
        # 控制台输出
        logger.add(
            sys.stderr,
            level="INFO",
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
        )
        
        # 文件输出
        from config import config
        logger.add(
            f"{config.log.log_dir}/app_{{time:YYYY-MM-DD}}.log",
            rotation="10 MB",
            retention="5 days",
            level="DEBUG",
            encoding="utf-8"
        )
        
        self.logger = logger
    
    def log_info(self, module: str, action: str, message: str, 
                task_id: str = None, audio_id: str = None, **kwargs):
        """记录 INFO 日志"""
        self.logger.info(f"[{module}:{action}] {message}")
        
        # 异步写入数据库
        try:
            db_manager.log_business_action(
                level='INFO',
                module=module,
                action=action,
                message=message,
                task_id=task_id,
                audio_id=audio_id,
                **kwargs
            )
        except Exception as e:
            self.logger.error(f"日志写入数据库失败: {e}")
    
    def log_warning(self, module: str, action: str, message: str,
                   task_id: str = None, audio_id: str = None, **kwargs):
        """记录 WARNING 日志"""
        self.logger.warning(f"[{module}:{action}] {message}")
        
        try:
            db_manager.log_business_action(
                level='WARNING',
                module=module,
                action=action,
                message=message,
                task_id=task_id,
                audio_id=audio_id,
                **kwargs
            )
        except Exception as e:
            self.logger.error(f"日志写入数据库失败: {e}")
    
    def log_error(self, module: str, action: str, error: Exception,
                 task_id: str = None, audio_id: str = None, **kwargs):
        """记录 ERROR 日志"""
        error_msg = f"[{module}:{action}] {str(error)}"
        stack_trace = traceback.format_exc()
        
        self.logger.error(f"{error_msg}\n{stack_trace}")
        
        try:
            db_manager.log_business_action(
                level='ERROR',
                module=module,
                action=action,
                message=str(error),
                task_id=task_id,
                audio_id=audio_id,
                stack_trace=stack_trace,
                **kwargs
            )
        except Exception as e:
            self.logger.error(f"日志写入数据库失败: {e}")
    
    def log_debug(self, module: str, action: str, message: str,
                 task_id: str = None, audio_id: str = None, **kwargs):
        """记录 DEBUG 日志"""
        self.logger.debug(f"[{module}:{action}] {message}")
        
        try:
            db_manager.log_business_action(
                level='DEBUG',
                module=module,
                action=action,
                message=message,
                task_id=task_id,
                audio_id=audio_id,
                **kwargs
            )
        except Exception as e:
            self.logger.error(f"日志写入数据库失败: {e}")
    
    def query_logs(self, task_id: str = None, level: str = None, limit: int = 100):
        """查询日志"""
        return db_manager.query_logs(task_id=task_id, level=level, limit=limit)


# 全局单例
business_logger = BusinessLogger()


if __name__ == "__main__":
    # 测试
    business_logger.log_info("test", "startup", "系统启动")
    business_logger.log_warning("test", "config", "配置文件缺失")
    business_logger.log_error("test", "process", ValueError("测试错误"))
    print("业务日志模块初始化成功")
