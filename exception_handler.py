"""
全局异常处理模块
统一捕获和处理应用中的异常，并记录详细日志
"""

import sys
import traceback
import functools
from typing import Callable, Optional
from logger_config import get_app_logger, get_error_logger

# 获取logger实例
app_logger = get_app_logger()
error_logger = get_error_logger()


class AppException(Exception):
    """应用自定义异常基类"""
    
    def __init__(self, message: str, code: int = 500, details: dict = None):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)


class BusinessException(AppException):
    """业务异常"""
    
    def __init__(self, message: str, code: int = 400, details: dict = None):
        super().__init__(message, code, details)


class ValidationException(AppException):
    """验证异常"""
    
    def __init__(self, message: str, field: str = None, details: dict = None):
        details = details or {}
        if field:
            details['field'] = field
        super().__init__(message, 422, details)


class NotFoundException(AppException):
    """资源未找到异常"""
    
    def __init__(self, resource: str, resource_id: str = None):
        message = f"资源 '{resource}' 未找到"
        if resource_id:
            message += f" (ID: {resource_id})"
        super().__init__(message, 404)


class PermissionDeniedException(AppException):
    """权限拒绝异常"""
    
    def __init__(self, message: str = "权限不足", details: dict = None):
        super().__init__(message, 403, details)


def handle_exception(exc_type, exc_value, exc_tb):
    """
    全局异常钩子 - 捕获未处理的异常
    
    Args:
        exc_type: 异常类型
        exc_value: 异常值
        exc_tb: 异常追踪信息
    """
    # 忽略 KeyboardInterrupt（Ctrl+C）
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_tb)
        return
    
    # 记录详细错误信息
    tb_str = ''.join(traceback.format_exception(exc_type, exc_value, exc_tb))
    
    error_logger.critical(
        f"未捕获的异常: {exc_type.__name__}: {exc_value}\n{tb_str}",
        extra={
            'exception_type': exc_type.__name__,
            'exception_message': str(exc_value)
        }
    )
    
    # 调用默认异常处理
    sys.__excepthook__(exc_type, exc_value, exc_tb)


def install_global_exception_handler():
    """安装全局异常处理器"""
    sys.excepthook = handle_exception
    app_logger.info("✅ 全局异常处理器已安装")


def exception_handler(func: Callable) -> Callable:
    """
    异常处理装饰器 - 用于包装函数，自动捕获和记录异常
    
    Usage:
        @exception_handler
        def my_function():
            ...
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except AppException as e:
            # 应用自定义异常 - 记录为warning
            app_logger.warning(
                f"应用异常 in {func.__name__}: {e.message}",
                extra={
                    'function': func.__name__,
                    'exception_type': type(e).__name__,
                    'exception_code': e.code,
                    'exception_details': e.details
                }
            )
            raise
        except Exception as e:
            # 其他异常 - 记录为error
            tb_str = traceback.format_exc()
            error_logger.error(
                f"未预期异常 in {func.__name__}: {type(e).__name__}: {str(e)}\n{tb_str}",
                extra={
                    'function': func.__name__,
                    'exception_type': type(e).__name__,
                    'exception_message': str(e)
                }
            )
            # 重新抛出异常
            raise
    
    return wrapper


def safe_execute(func: Callable, default=None, error_message: str = "执行失败"):
    """
    安全执行函数 - 捕获异常并返回默认值
    
    Args:
        func: 要执行的函数
        default: 异常时返回的默认值
        error_message: 错误消息前缀
    
    Returns:
        函数执行结果或默认值
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            tb_str = traceback.format_exc()
            error_logger.error(
                f"{error_message} in {func.__name__}: {type(e).__name__}: {str(e)}\n{tb_str}",
                extra={
                    'function': func.__name__,
                    'exception_type': type(e).__name__
                }
            )
            return default
    
    return wrapper


class ExceptionContext:
    """异常上下文管理器"""
    
    def __init__(self, operation: str, reraise: bool = True):
        self.operation = operation
        self.reraise = reraise
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            tb_str = ''.join(traceback.format_exception(exc_type, exc_val, exc_tb))
            
            error_logger.error(
                f"异常发生在 [{self.operation}]: {exc_type.__name__}: {exc_val}\n{tb_str}",
                extra={
                    'operation': self.operation,
                    'exception_type': exc_type.__name__,
                    'exception_message': str(exc_val)
                }
            )
            
            return not self.reraise  # False表示重新抛出异常
        
        return False


def log_exception_details(exception: Exception, context: dict = None):
    """
    记录异常详细信息
    
    Args:
        exception: 异常对象
        context: 额外的上下文信息
    """
    tb_str = traceback.format_exc()
    
    log_data = {
        'exception_type': type(exception).__name__,
        'exception_message': str(exception),
        'traceback': tb_str
    }
    
    if context:
        log_data.update(context)
    
    error_logger.error(
        f"异常详情: {type(exception).__name__}: {str(exception)}",
        extra=log_data
    )


if __name__ == "__main__":
    # 测试全局异常处理
    print("测试全局异常处理系统...")
    
    # 安装全局异常处理器
    install_global_exception_handler()
    
    # 测试1: 使用装饰器
    @exception_handler
    def test_function_with_error():
        result = 1 / 0
        return result
    
    try:
        test_function_with_error()
    except ZeroDivisionError:
        print("✅ 测试1通过: 装饰器捕获异常")
    
    # 测试2: 使用上下文管理器
    try:
        with ExceptionContext("测试操作"):
            raise ValueError("测试错误")
    except ValueError:
        print("✅ 测试2通过: 上下文管理器捕获异常")
    
    # 测试3: 自定义异常
    try:
        raise BusinessException("业务逻辑错误", code=400, details={'field': 'email'})
    except BusinessException as e:
        print(f"✅ 测试3通过: 自定义异常 - {e.message}")
    
    # 测试4: 安全执行
    def risky_operation():
        return int("not_a_number")
    
    safe_risky = safe_execute(risky_operation, default="默认值", error_message="安全执行失败")
    result = safe_risky()
    print(f"✅ 测试4通过: 安全执行返回默认值: {result}")
    
    # 测试5: 记录异常详情
    try:
        raise RuntimeError("运行时错误")
    except Exception as e:
        log_exception_details(e, {'user_id': 'test-123', 'action': 'test'})
        print("✅ 测试5通过: 异常详情记录")
    
    print("\n✨ 所有测试完成，请查看 logs/error.log")
