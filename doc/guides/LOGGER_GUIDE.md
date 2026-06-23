# 日志系统使用指南

## 📋 概述

本系统提供企业级日志管理功能，支持：
- ✅ 多级别日志输出（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- ✅ 按天自动滚动日志文件
- ✅ 定期清理过期日志（默认30天）
- ✅ 彩色控制台输出
- ✅ JSON格式文件日志（便于ELK分析）
- ✅ 错误日志单独记录

---

## 🚀 快速开始

### 1. 基本用法

```python
from logger_config import get_app_logger, get_business_logger, get_error_logger

# 获取logger实例
logger = get_app_logger()

# 记录不同级别的日志
logger.debug("调试信息")
logger.info("普通信息")
logger.warning("警告信息")
logger.error("错误信息")
logger.critical("严重错误")
```

### 2. 带异常信息的日志

```python
try:
    result = 1 / 0
except Exception as e:
    logger.exception("发生异常")  # 自动包含堆栈追踪
```

### 3. 带额外字段的日志

```python
logger.info("任务完成", extra={
    'task_id': 'task-123',
    'user_id': 'user-456'
})
```

---

## 🎨 控制台输出格式

### 彩色输出

控制台日志采用彩色格式化，便于快速识别不同级别：

```
2026-05-19 19:28:15 [DEBUG] logger_config: 这是一条DEBUG日志      # 青色
2026-05-19 19:28:15 [INFO] logger_config: 这是一条INFO日志        # 绿色
2026-05-19 19:28:15 [WARNING] logger_config: 这是一条WARNING日志  # 黄色
2026-05-19 19:28:15 [ERROR] logger_config: 这是一条ERROR日志      # 红色
```

**颜色说明**:
- 🔵 **DEBUG**: 青色 - 调试信息
- 🟢 **INFO**: 绿色 - 普通信息
- 🟡 **WARNING**: 黄色 - 警告信息
- 🔴 **ERROR**: 红色 - 错误信息
- 🔴 **CRITICAL**: 粗体红色 - 严重错误

### 输出格式

```
%(asctime)s [%(levelname)s] %(module)s: %(message)s
```

**示例**:
```
2026-05-19 19:28:15 [INFO] batch_processor: 任务启动成功
```

---

## 📁 文件日志格式

### JSON格式（默认）

文件日志采用JSON格式，便于日志分析系统（如ELK）处理：

```json
{
  "timestamp": "2026-05-19T19:28:15.123456",
  "level": "INFO",
  "logger": "app",
  "module": "batch_processor",
  "function": "start_batch",
  "line": 61,
  "message": "任务启动: 批量任务_20260519, 共 10 个音频",
  "task_id": "task-123",
  "user_id": "user-456"
}
```

### 字段说明

| 字段 | 说明 | 示例 |
|------|------|------|
| timestamp | ISO格式时间戳 | 2026-05-19T19:28:15.123456 |
| level | 日志级别 | DEBUG/INFO/WARNING/ERROR/CRITICAL |
| logger | logger名称 | app/business/error |
| module | 模块名 | batch_processor |
| function | 函数名 | start_batch |
| line | 行号 | 61 |
| message | 日志消息 | 任务启动成功 |
| task_id | 任务ID（可选） | task-123 |
| user_id | 用户ID（可选） | user-456 |
| exception | 异常信息（可选） | Traceback... |

---

## 🗂️ 日志文件结构

```
logs/
├── app.log                  # 当前应用日志
├── app.2026-05-19.log      # 历史日志（按天滚动）
├── app.2026-05-18.log
├── app.error.log            # 错误日志（仅ERROR及以上）
├── business.log             # 业务日志
├── business.error.log
├── error.log                # 纯错误日志
└── performance.log          # 性能日志
```

**滚动策略**:
- 每天午夜自动滚动
- 文件名格式：`{name}.YYYY-MM-DD.log`
- 默认保留30天

---

## 🔧 配置选项

### LoggerConfig.setup_logger()

```python
LoggerConfig.setup_logger(
    name='app',              # logger名称
    log_dir='logs',          # 日志目录
    rotation='midnight',     # 滚动策略
    backup_days=30,          # 保留天数
    level='DEBUG',           # 日志级别
    enable_json=True,        # 是否启用JSON格式
    enable_console=True      # 是否输出到控制台
)
```

**滚动策略选项**:
- `'midnight'` - 每天午夜
- `'H'` - 每小时
- `'M'` - 每分钟
- `'S'` - 每秒
- `'W0'-'W6'` - 每周（周一到周日）

**日志级别**:
- `'DEBUG'` - 调试信息
- `'INFO'` - 普通信息
- `'WARNING'` - 警告信息
- `'ERROR'` - 错误信息
- `'CRITICAL'` - 严重错误

---

## 📊 预定义Logger

系统提供了几个预定义的logger实例：

### 1. get_app_logger()
应用主logger，用于一般应用日志

```python
logger = get_app_logger()
logger.info("应用启动")
```

### 2. get_business_logger()
业务逻辑logger，用于业务操作日志

```python
logger = get_business_logger()
logger.info("订单创建成功", extra={'order_id': '123'})
```

### 3. get_error_logger()
错误日志logger，仅记录ERROR及以上级别

```python
logger = get_error_logger()
logger.error("数据库连接失败")
```

### 4. get_performance_logger()
性能监控logger，用于性能指标记录

```python
logger = get_performance_logger()
logger.info("请求耗时: 123ms", extra={'duration': 123})
```

---

## 🧹 日志清理

### 自动清理

在logger初始化时会自动清理过期日志：

```python
from logger_config import LoggerConfig

# 清理30天前的日志
LoggerConfig.cleanup_old_logs(log_dir='logs', retention_days=30)
```

### 定时清理

使用crontab定时清理：

```bash
# 每天凌晨2点清理过期日志
0 2 * * * cd /path/to/project && python3 cleanup_logs.py >> logs/cron.log 2>&1
```

或使用提供的脚本：

```bash
python3 cleanup_logs.py
```

---

## 💡 最佳实践

### 1. 选择合适的日志级别

```python
# DEBUG: 详细的调试信息
logger.debug(f"变量值: x={x}, y={y}")

# INFO: 一般信息
logger.info("用户登录成功", extra={'user_id': user_id})

# WARNING: 警告信息（不影响正常运行）
logger.warning("配置文件缺失，使用默认值")

# ERROR: 错误信息（影响功能）
logger.error("数据库连接失败", exc_info=True)

# CRITICAL: 严重错误（系统无法运行）
logger.critical("内存不足，系统即将崩溃")
```

### 2. 添加上下文信息

```python
# ✅ 好：包含上下文
logger.info("订单处理完成", extra={
    'order_id': order_id,
    'user_id': user_id,
    'amount': amount
})

# ❌ 坏：缺少上下文
logger.info("订单处理完成")
```

### 3. 使用结构化日志

```python
# ✅ 好：结构化数据
logger.info("API调用", extra={
    'endpoint': '/api/users',
    'method': 'GET',
    'status_code': 200,
    'duration_ms': 45
})

# ❌ 坏：字符串拼接
logger.info(f"API调用 /api/users GET 200 45ms")
```

### 4. 异常日志

```python
# ✅ 好：使用exception方法
try:
    process_data()
except Exception as e:
    logger.exception("数据处理失败")

# ❌ 坏：手动记录异常
try:
    process_data()
except Exception as e:
    logger.error(f"数据处理失败: {e}")
```

---

## 🔍 日志查询和分析

### 查看实时日志

```bash
# 跟踪应用日志
tail -f logs/app.log

# 跟踪错误日志
tail -f logs/error.log
```

### 搜索特定日志

```bash
# 搜索包含特定关键词的日志
grep "task-123" logs/app.log

# 搜索错误日志
grep "ERROR" logs/app.log

# 搜索特定时间的日志
grep "2026-05-19 19:" logs/app.log
```

### JSON日志分析

```bash
# 格式化JSON日志
cat logs/app.log | python3 -m json.tool

# 使用jq分析
cat logs/app.log | jq 'select(.level == "ERROR")'
```

---

## 🎯 集成示例

### 在 Streamlit 应用中

```python
# app.py
from logger_config import get_app_logger

logger = get_app_logger()

@st.cache_resource
def initialize_app():
    logger.info("应用启动")
    # 初始化逻辑
```

### 在批处理器中

```python
# batch_processor.py
from logger_config import get_business_logger

logger = get_business_logger()

class BatchProcessor:
    def start_batch(self, task_name, audio_urls):
        logger.info("批处理启动", extra={
            'task_name': task_name,
            'count': len(audio_urls)
        })
        # 处理逻辑
```

### 在认证模块中

```python
# auth.py
from logger_config import get_app_logger

logger = get_app_logger()

class AuthManager:
    def login(self, username, password):
        try:
            # 验证逻辑
            logger.info("用户登录成功", extra={'username': username})
        except Exception as e:
            logger.error("登录失败", extra={'username': username}, exc_info=True)
```

---

## ⚙️ 高级配置

### 自定义Formatter

```python
from logger_config import LoggerConfig
import logging

class CustomFormatter(logging.Formatter):
    def format(self, record):
        # 自定义格式
        return f"[CUSTOM] {record.getMessage()}"

logger = LoggerConfig.setup_logger('custom')
# 替换formatter
for handler in logger.handlers:
    if isinstance(handler, logging.StreamHandler):
        handler.setFormatter(CustomFormatter())
```

### 添加FileHandler

```python
from logger_config import LoggerConfig
import logging
from logging.handlers import RotatingFileHandler

logger = LoggerConfig.setup_logger('custom')

# 添加按大小滚动的handler
handler = RotatingFileHandler(
    'logs/custom.log',
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5
)
handler.setFormatter(logging.Formatter('%(message)s'))
logger.addHandler(handler)
```

---

## 📈 性能考虑

### 日志级别影响

- **DEBUG**: 最详细，性能开销最大
- **INFO**: 适中，推荐生产环境使用
- **WARNING**: 较少，适合高负载环境
- **ERROR/CRITICAL**: 最少，性能开销最小

### 优化建议

1. **生产环境**: 设置日志级别为 `INFO` 或 `WARNING`
2. **开发环境**: 设置日志级别为 `DEBUG`
3. **异步日志**: 大量日志时考虑使用异步handler
4. **采样日志**: 高频日志可以使用采样策略

```python
# 采样日志示例
import random

def sampled_log(logger, message, sample_rate=0.1):
    if random.random() < sample_rate:
        logger.info(message)
```

---

## 🔗 相关文档

- [logger_config.py](logger_config.py) - 日志系统源码
- [cleanup_logs.py](cleanup_logs.py) - 日志清理脚本
- [crontab.example](crontab.example) - Crontab配置示例
- [exception_handler.py](exception_handler.py) - 异常处理系统

---

## ❓ 常见问题

### Q: 如何禁用控制台输出？

A: 设置 `enable_console=False`

```python
logger = LoggerConfig.setup_logger('app', enable_console=False)
```

### Q: 如何修改日志保留天数？

A: 设置 `backup_days` 参数

```python
logger = LoggerConfig.setup_logger('app', backup_days=7)  # 保留7天
```

### Q: 如何查看JSON日志？

A: 使用 `python3 -m json.tool` 或 `jq`

```bash
cat logs/app.log | python3 -m json.tool
```

### Q: 日志文件太大怎么办？

A: 
1. 减少保留天数
2. 提高日志级别
3. 使用日志压缩

---

**最后更新**: 2026-05-19  
**版本**: v1.0
