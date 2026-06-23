"""
日志配置模块
实现多级别日志输出、按周期滚动和定期清理
"""

import os
import sys
import json
import logging
from logging.handlers import TimedRotatingFileHandler
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional


class ColoredFormatter(logging.Formatter):
    """彩色控制台日志 formatter"""
    
    # ANSI 颜色代码
    COLORS = {
        'DEBUG': '\033[36m',      # 青色
        'INFO': '\033[32m',       # 绿色
        'WARNING': '\033[33m',    # 黄色
        'ERROR': '\033[31m',      # 红色
        'CRITICAL': '\033[1;31m', # 粗体红色
    }
    RESET = '\033[0m'
    
    def format(self, record):
        # 获取颜色
        color = self.COLORS.get(record.levelname, '')
        
        # 格式化消息
        log_message = super().format(record)
        
        # 添加颜色
        if color:
            # 为级别添加颜色
            levelname_colored = f"{color}{record.levelname}{self.RESET}"
            log_message = log_message.replace(record.levelname, levelname_colored, 1)
        
        return log_message


class JSONFormatter(logging.Formatter):
    """JSON格式日志 formatter"""
    
    def format(self, record):
        log_record = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'message': record.getMessage(),
        }
        
        # 添加异常信息
        if record.exc_info and record.exc_info[0] is not None:
            log_record['exception'] = self.formatException(record.exc_info)
        
        # 添加额外字段
        if hasattr(record, 'task_id'):
            log_record['task_id'] = record.task_id
        if hasattr(record, 'user_id'):
            log_record['user_id'] = record.user_id
        if hasattr(record, 'audio_id'):
            log_record['audio_id'] = record.audio_id
        
        return json.dumps(log_record, ensure_ascii=False)


class LoggerConfig:
    """日志配置管理器"""
    
    # 日志级别映射
    LOG_LEVELS = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL
    }
    
    @staticmethod
    def setup_logger(
        name: str,
        log_dir: str = 'logs',
        rotation: str = 'midnight',
        backup_days: int = 30,
        level: str = 'DEBUG',
        enable_json: bool = False,  # 默认不使用JSON格式
        enable_console: bool = True
    ) -> logging.Logger:
        """
        配置并返回logger实例
        
        Args:
            name: logger名称
            log_dir: 日志目录
            rotation: 滚动策略 ('midnight', 'H', 'M'等)
            backup_days: 保留天数
            level: 日志级别
            enable_json: 是否启用JSON格式
            enable_console: 是否输出到控制台
        
        Returns:
            logging.Logger: 配置好的logger实例
        """
        logger = logging.getLogger(name)
        logger.setLevel(LoggerConfig.LOG_LEVELS.get(level, logging.DEBUG))
        
        # 避免重复添加handler
        if logger.handlers:
            return logger
        
        # 创建日志目录
        Path(log_dir).mkdir(parents=True, exist_ok=True)
        
        # 文件处理器 - 按时间滚动
        log_file = os.path.join(log_dir, f'{name}.log')
        file_handler = TimedRotatingFileHandler(
            log_file,
            when=rotation,
            interval=1,
            backupCount=backup_days,
            encoding='utf-8'
        )
        file_handler.suffix = "%Y-%m-%d.log"
        
        # 设置文件日志格式 - 使用原始格式而非JSON
        file_formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(name)s %(module)s.%(funcName)s:%(lineno)d - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
        
        # 控制台处理器
        if enable_console:
            console_handler = logging.StreamHandler(sys.stdout)
            # 使用彩色格式化器
            console_formatter = ColoredFormatter(
                '%(asctime)s [%(levelname)s] %(module)s: %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            console_handler.setFormatter(console_formatter)
            logger.addHandler(console_handler)
        
        # 错误日志单独输出
        error_log_file = os.path.join(log_dir, f'{name}.error.log')
        error_handler = TimedRotatingFileHandler(
            error_log_file,
            when=rotation,
            interval=1,
            backupCount=backup_days,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        # 错误日志使用原始格式，自动包含完整堆栈
        error_formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(name)s %(module)s.%(funcName)s:%(lineno)d - %(message)s'
        )
        error_handler.setFormatter(error_formatter)
        logger.addHandler(error_handler)
        
        return logger
    
    @staticmethod
    def cleanup_old_logs(log_dir: str = 'logs', retention_days: int = 30):
        """
        清理过期日志文件
        
        Args:
            log_dir: 日志目录
            retention_days: 保留天数
        """
        log_path = Path(log_dir)
        if not log_path.exists():
            return
        
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        deleted_count = 0
        
        for log_file in log_path.glob('*.log*'):
            # 获取文件修改时间
            mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
            
            if mtime < cutoff_date:
                try:
                    log_file.unlink()
                    deleted_count += 1
                    print(f"🗑️  删除过期日志: {log_file.name}")
                except Exception as e:
                    print(f"❌ 删除日志失败 {log_file.name}: {e}")
        
        if deleted_count > 0:
            print(f"✅ 已清理 {deleted_count} 个过期日志文件")
        else:
            print("✨ 无需清理的过期日志")


# 预定义的logger实例
def get_app_logger() -> logging.Logger:
    """获取应用主logger"""
    return LoggerConfig.setup_logger('app')


def get_business_logger() -> logging.Logger:
    """获取业务逻辑logger"""
    return LoggerConfig.setup_logger('business')


def get_error_logger() -> logging.Logger:
    """获取错误日志logger"""
    return LoggerConfig.setup_logger('error', level='ERROR')


def get_performance_logger() -> logging.Logger:
    """获取性能监控logger"""
    return LoggerConfig.setup_logger('performance')


if __name__ == "__main__":
    # 测试日志系统
    print("测试日志系统...")
    
    # 创建测试logger
    logger = LoggerConfig.setup_logger('test', level='DEBUG')
    
    # 测试不同级别日志
    logger.debug("这是一条DEBUG日志")
    logger.info("这是一条INFO日志")
    logger.warning("这是一条WARNING日志")
    logger.error("这是一条ERROR日志")
    
    try:
        # 测试异常日志
        result = 1 / 0
    except Exception as e:
        logger.exception("捕获到异常")
    
    # 测试带额外字段的日志
    extra_logger = LoggerConfig.setup_logger('test_extra')
    record = logging.LogRecord(
        name='test_extra',
        level=logging.INFO,
        pathname='',
        lineno=0,
        msg="带任务ID的日志",
        args=(),
        exc_info=None
    )
    record.task_id = "task-123"
    record.user_id = "user-456"
    extra_logger.handle(record)
    
    print("\n✅ 日志系统测试完成，请查看 logs/ 目录")
