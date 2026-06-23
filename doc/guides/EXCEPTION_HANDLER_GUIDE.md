# 全局异常处理使用指南

## 📋 概述

全局异常处理系统提供了统一的异常捕获、处理和日志记录机制，确保所有异常都能被妥善处理和记录。

---

## 🚀 快速开始

### 1. 安装全局异常处理器

在应用启动时调用：

```python
from exception_handler import install_global_exception_handler

# 在 app.py 或其他入口文件中
install_global_exception_handler()
```

### 2. 使用装饰器

```python
from exception_handler import exception_handler

@exception_handler
def my_function():
    # 你的代码
    result = 1 / 0  # 这会触发异常并被记录
    return result
```

### 3. 使用上下文管理器

```python
from exception_handler import ExceptionContext

try:
    with ExceptionContext("数据库操作"):
        db.execute(query)
except Exception as e:
    # 异常已被记录，可以在此处理
    pass
```

### 4. 安全执行函数

```python
from exception_handler import safe_execute

def risky_operation():
    return int("not_a_number")

# 如果出错，返回默认值而不是抛出异常
safe_func = safe_execute(risky_operation, default=0, error_message="转换失败")
result = safe_func()  # 返回 0
```

---

## 📚 API 参考

### 自定义异常类

#### AppException
应用自定义异常基类

```python
from exception_handler import AppException

raise AppException(
    message="错误消息",
    code=500,
    details={'field': 'email'}
)
```

#### BusinessException
业务逻辑异常（HTTP 400）

```python
from exception_handler import BusinessException

raise BusinessException("订单不存在", code=404)
```

#### ValidationException
验证异常（HTTP 422）

```python
from exception_handler import ValidationException

raise ValidationException("邮箱格式无效", field="email")
```

#### NotFoundException
资源未找到（HTTP 404）

```python
from exception_handler import NotFoundException

raise NotFoundException("用户", resource_id="123")
```

#### PermissionDeniedException
权限拒绝（HTTP 403）

```python
from exception_handler import PermissionDeniedException

raise PermissionDeniedException("需要管理员权限")
```

---

### 装饰器

#### @exception_handler

自动捕获和记录函数中的异常

**用法**:
```python
@exception_handler
def process_data(data):
    # 处理逻辑
    return result
```

**特性**:
- 自动记录异常到日志
- 保留原始异常堆栈
- 区分AppException和其他异常

---

### 工具函数

#### safe_execute(func, default=None, error_message="执行失败")

安全执行函数，异常时返回默认值

**参数**:
- `func`: 要执行的函数
- `default`: 异常时返回的默认值
- `error_message`: 错误消息前缀

**用法**:
```python
def parse_int(value):
    return int(value)

safe_parse = safe_execute(parse_int, default=0)
result = safe_parse("abc")  # 返回 0，不抛出异常
```

---

#### log_exception_details(exception, context=None)

记录异常详细信息

**参数**:
- `exception`: 异常对象
- `context`: 额外的上下文信息（dict）

**用法**:
```python
try:
    process_order(order_id)
except Exception as e:
    log_exception_details(e, {
        'user_id': user_id,
        'order_id': order_id
    })
    raise
```

---

### 上下文管理器

#### ExceptionContext(operation, reraise=True)

异常上下文管理器

**参数**:
- `operation`: 操作描述
- `reraise`: 是否重新抛出异常（默认True）

**用法**:
```python
# 重新抛出异常
try:
    with ExceptionContext("文件读取"):
        with open('file.txt') as f:
            data = f.read()
except FileNotFoundError:
    pass

# 不重新抛出异常
with ExceptionContext("可选操作", reraise=False):
    optional_cleanup()
```

---

## 🔧 集成示例

### 1. 在 Streamlit 应用中集成

```python
# app.py
import streamlit as st
from exception_handler import install_global_exception_handler, exception_handler

# 安装全局异常处理器
install_global_exception_handler()

@st.cache_resource
def initialize_app():
    # 初始化代码
    pass

# 使用装饰器保护关键函数
@exception_handler
def process_audio(audio_url):
    """处理音频"""
    # ASR 处理逻辑
    pass

@exception_handler
def analyze_text(text):
    """分析文本"""
    # LLM 分析逻辑
    pass
```

### 2. 在批处理器中集成

```python
# batch_processor.py
from exception_handler import exception_handler, BusinessException

class BatchProcessor:
    @exception_handler
    def start_batch(self, task_name, audio_urls):
        """启动批处理任务"""
        if not audio_urls:
            raise BusinessException("音频列表不能为空")
        
        # 批处理逻辑
        pass
    
    @exception_handler
    def _process_single(self, audio_url):
        """处理单个音频"""
        try:
            # 处理逻辑
            pass
        except Exception as e:
            # 记录并重新抛出
            raise
```

### 3. 在认证模块中集成

```python
# auth.py
from exception_handler import (
    exception_handler,
    ValidationException,
    PermissionDeniedException
)

class AuthManager:
    @exception_handler
    def login(self, username, password):
        """用户登录"""
        if not username or not password:
            raise ValidationException(
                "用户名和密码不能为空",
                field="credentials"
            )
        
        # 验证逻辑
        user = self.verify_user(username, password)
        
        if not user:
            raise PermissionDeniedException("用户名或密码错误")
        
        return self.generate_token(user)
    
    @exception_handler
    def verify_session(self, token):
        """验证会话"""
        if not token:
            raise PermissionDeniedException("缺少认证令牌")
        
        # 验证逻辑
        pass
```

### 4. 在数据库操作中集成

```python
# database.py
from exception_handler import (
    exception_handler,
    ExceptionContext,
    NotFoundException
)

class DatabaseManager:
    @exception_handler
    def get_task(self, task_id):
        """获取任务"""
        with ExceptionContext(f"查询任务: {task_id}"):
            task = self.query_task(task_id)
            
            if not task:
                raise NotFoundException("任务", task_id)
            
            return task
    
    @exception_handler
    def save_result(self, result_data):
        """保存结果"""
        with ExceptionContext("保存处理结果"):
            # 数据库操作
            session.add(result)
            session.commit()
```

---

## 📊 日志输出示例

### JSON 格式错误日志

```json
{
  "timestamp": "2026-05-19T19:23:03.234169",
  "level": "ERROR",
  "logger": "error",
  "module": "batch_processor",
  "function": "process_audio",
  "line": 123,
  "message": "未预期异常 in process_audio: FileNotFoundError: 文件不存在\nTraceback...",
  "exception_type": "FileNotFoundError",
  "exception_message": "文件不存在",
  "task_id": "task-123",
  "audio_id": "audio-456"
}
```

### 控制台输出

```
2026-05-19 19:23:03 [ERROR] batch_processor: 未预期异常 in process_audio: FileNotFoundError: 文件不存在
Traceback (most recent call last):
  File "/app/batch_processor.py", line 123, in process_audio
    with open(audio_path) as f:
FileNotFoundError: 文件不存在
```

---

## 🎯 最佳实践

### 1. 选择合适的异常处理方式

```python
# ✅ 好：关键操作使用装饰器
@exception_handler
def critical_operation():
    ...

# ✅ 好：可选操作使用安全执行
safe_func = safe_execute(optional_task, default=None)
result = safe_func()

# ✅ 好：需要上下文信息使用上下文管理器
with ExceptionContext("数据库事务"):
    db.commit()

# ❌ 坏：不要过度使用，影响性能
@exception_handler
def simple_addition(a, b):
    return a + b
```

### 2. 提供有意义的错误信息

```python
# ✅ 好：详细的错误信息
raise BusinessException(
    "订单创建失败：库存不足",
    code=400,
    details={
        'product_id': product_id,
        'requested': quantity,
        'available': stock
    }
)

# ❌ 坏：模糊的错误信息
raise Exception("出错了")
```

### 3. 添加上下文信息

```python
# ✅ 好：包含上下文
try:
    process_order(order_id)
except Exception as e:
    log_exception_details(e, {
        'user_id': current_user.id,
        'order_id': order_id,
        'action': 'checkout'
    })
    raise

# ❌ 坏：缺少上下文
try:
    process_order(order_id)
except Exception as e:
    logger.error(str(e))
    raise
```

### 4. 区分异常类型

```python
# ✅ 好：区分业务异常和系统异常
try:
    validate_input(data)
except ValidationException as e:
    # 用户输入错误，返回400
    return jsonify({'error': e.message}), 400
except Exception as e:
    # 系统错误，返回500
    log_exception_details(e)
    return jsonify({'error': '服务器内部错误'}), 500
```

---

## ⚠️ 注意事项

### 1. 不要在装饰器中吞掉异常

```python
# ❌ 坏：静默吞掉异常
@exception_handler
def my_function():
    ...
# 异常被记录但仍然抛出

# ✅ 好：如果需要吞掉异常，使用 safe_execute
safe_func = safe_execute(my_function, default=None)
```

### 2. 避免循环依赖

```python
# ❌ 坏：在异常处理器中导入可能引起异常的模块
from exception_handler import exception_handler

@exception_handler
def init_database():
    from database import db  # 可能导致循环导入
    ...

# ✅ 好：在函数内部延迟导入
@exception_handler
def init_database():
    # 正常逻辑
    ...
```

### 3. 生产环境配置

```python
# 开发环境：显示详细错误
install_global_exception_handler()

# 生产环境：隐藏敏感信息
import os
if os.getenv('ENV') == 'production':
    # 可以自定义错误响应
    pass
```

---

## 🧪 测试

运行测试脚本验证功能：

```bash
python3 exception_handler.py
```

检查日志文件：

```bash
# 查看错误日志
tail -f logs/error.log

# 查看JSON格式日志
cat logs/error.log | python3 -m json.tool
```

---

## 📈 性能考虑

- **装饰器开销**: 每次函数调用增加约 0.1ms
- **建议**: 只在关键函数上使用装饰器
- **日志级别**: 生产环境设置为 WARNING 或 ERROR
- **异步支持**: 当前版本不支持 async/await

---

## 🔗 相关文档

- [logger_config.py](logger_config.py) - 日志系统
- [OPTIMIZATION_RECOMMENDATIONS.md](OPTIMIZATION_RECOMMENDATIONS.md) - 优化建议
- [PHASE6_7_SUMMARY.md](PHASE6_7_SUMMARY.md) - 实施总结

---

**最后更新**: 2026-05-19  
**版本**: v1.0
