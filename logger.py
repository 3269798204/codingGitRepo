"""
业务日志模块
结构化日志记录，支持 MySQL 持久化和新式日志系统
"""

import sys
import traceback
from datetime import datetime
from typing import Optional
from loguru import logger

from database import db_manager
from logger_config import LoggerConfig, get_app_logger, get_business_logger, get_error_logger


class BusinessLogger:
    """业务日志管理器（兼容旧版API，内部使用新日志系统）"""
    
    def __init__(self):
        # 配置 loguru（保持向后兼容）
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
        
        # 初始化新的日志系统
        self.app_logger = get_app_logger()
        self.business_logger = get_business_logger()
        self.error_logger = get_error_logger()
        
        # 定期清理过期日志
        try:
            LoggerConfig.cleanup_old_logs(retention_days=30)
        except Exception as e:
            self.logger.warning(f"日志清理失败: {e}")
    
    def log_info(self, module: str, action: str, message: str, 
                task_id: str = None, audio_id: str = None, **kwargs):
        """记录 INFO 日志"""
        # 使用新日志系统
        self.business_logger.info(f"[{module}:{action}] {message}", 
                                  extra={'task_id': task_id, 'audio_id': audio_id})
        
        # 异步写入数据库（保持向后兼容）
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
        
        # 使用新日志系统
        self.error_logger.error(f"{error_msg}\n{stack_trace}",
                               extra={'task_id': task_id, 'audio_id': audio_id})
        
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
