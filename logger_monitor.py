"""
语音识别分析系统 - 日志监控模块
提供结构化日志、实时监控和日志查询功能
"""

import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler


class ColoredFormatter(logging.Formatter):
    """彩色日志格式化器"""
    
    COLORS = {
        'DEBUG': '\033[36m',     # 青色
        'INFO': '\033[32m',      # 绿色
        'WARNING': '\033[33m',   # 黄色
        'ERROR': '\033[31m',     # 红色
        'CRITICAL': '\033[35m',  # 紫色
    }
    RESET = '\033[0m'
    
    def format(self, record):
        color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{color}{record.levelname}{self.RESET}"
        return super().format(record)


class JsonFormatter(logging.Formatter):
    """JSON 格式日志（用于机器读取）"""
    
    def format(self, record):
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        if hasattr(record, 'task_id'):
            log_data['task_id'] = record.task_id
        
        if hasattr(record, 'audio_id'):
            log_data['audio_id'] = record.audio_id
        
        if record.exc_info and record.exc_info[1]:
            log_data['exception'] = str(record.exc_info[1])
        
        return json.dumps(log_data, ensure_ascii=False)


class LoggerManager:
    """日志管理器 - 单例模式"""
    
    _instance = None
    _loggers = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self.log_dir = Path('./logs')
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建根日志器
        self.root_logger = self._create_logger(
            name='voice_analysis',
            log_file=self.log_dir / 'app.log',
            level=logging.INFO
        )
        
        # 创建错误日志器
        self.error_logger = self._create_logger(
            name='voice_analysis.error',
            log_file=self.log_dir / 'error.log',
            level=logging.ERROR
        )
        
        # 创建性能日志器
        self.perf_logger = self._create_logger(
            name='voice_analysis.performance',
            log_file=self.log_dir / 'performance.log',
            level=logging.INFO
        )
        
        # 创建业务日志器
        self.business_logger = self._create_logger(
            name='voice_analysis.business',
            log_file=self.log_dir / 'business.log',
            level=logging.INFO
        )
    
    def _create_logger(self, name: str, log_file: Path, level: int) -> logging.Logger:
        """创建日志器"""
        logger = logging.getLogger(name)
        logger.setLevel(level)
        
        # 避免重复添加 handler
        if logger.handlers:
            return logger
        
        # 控制台 Handler（彩色输出）
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_formatter = ColoredFormatter(
            '%(asctime)s [%(levelname)s] %(name)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
        
        # 文件 Handler（轮转）
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(level)
        file_formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
        
        # JSON 文件 Handler（用于日志分析）
        json_handler = RotatingFileHandler(
            log_file.with_suffix('.json.log'),
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding='utf-8'
        )
        json_handler.setLevel(level)
        json_formatter = JsonFormatter()
        json_handler.setFormatter(json_formatter)
        logger.addHandler(json_handler)
        
        return logger
    
    def get_logger(self, name: str = None) -> logging.Logger:
        """获取日志器"""
        if not name:
            return self.root_logger
        
        if name == 'error':
            return self.error_logger
        elif name == 'performance':
            return self.perf_logger
        elif name == 'business':
            return self.business_logger
        else:
            return self.root_logger.getChild(name)
    
    def log_task_start(self, task_id: str, task_name: str, total_count: int):
        """记录任务开始"""
        logger = self.business_logger
        extra = {'task_id': task_id}
        logger.info(
            f"任务启动 | ID: {task_id} | 名称: {task_name} | 总数: {total_count}",
            extra=extra
        )
    
    def log_task_progress(self, task_id: str, progress: float, message: str):
        """记录任务进度"""
        logger = self.business_logger
        extra = {'task_id': task_id}
        logger.info(
            f"任务进度 | ID: {task_id} | 进度: {progress:.1f}% | {message}",
            extra=extra
        )
    
    def log_task_complete(self, task_id: str, success_count: int, failed_count: int, elapsed: float):
        """记录任务完成"""
        logger = self.business_logger
        extra = {'task_id': task_id}
        logger.info(
            f"任务完成 | ID: {task_id} | 成功: {success_count} | 失败: {failed_count} | 耗时: {elapsed:.2f}s",
            extra=extra
        )
    
    def log_audio_process(self, audio_id: str, status: str, duration: float = None, error: str = None):
        """记录音频处理"""
        logger = self.business_logger
        extra = {'audio_id': audio_id}
        
        if status == 'success':
            logger.info(f"音频处理成功 | ID: {audio_id} | 时长: {duration:.2f}s", extra=extra)
        elif status == 'failed':
            logger.error(f"音频处理失败 | ID: {audio_id} | 错误: {error}", extra=extra)
    
    def log_performance(self, operation: str, elapsed: float, details: Dict = None):
        """记录性能数据"""
        logger = self.perf_logger
        msg = f"性能 | {operation} | 耗时: {elapsed:.3f}s"
        if details:
            msg += f" | {', '.join([f'{k}: {v}' for k, v in details.items()])}"
        logger.info(msg)


# 全局日志管理器实例
logger_manager = LoggerManager()


def get_logger(name: str = None) -> logging.Logger:
    """便捷函数：获取日志器"""
    return logger_manager.get_logger(name)


def setup_exception_logging():
    """设置全局异常日志"""
    def exception_hook(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        
        logger = get_logger('error')
        logger.critical(
            "未捕获的异常",
            exc_info=(exc_type, exc_value, exc_traceback)
        )
    
    sys.excepthook = exception_hook
