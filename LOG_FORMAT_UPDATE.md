# 日志系统优化说明

## 📋 优化内容

根据需求，已将日志系统优化为：
1. ✅ **取消JSON格式** - 使用原始文本格式
2. ✅ **完整异常堆栈** - 异常日志包含完整traceback
3. ✅ **保留彩色控制台** - 控制台输出仍保持彩色

---

## 🎨 日志格式对比

### 之前（JSON格式）

```json
{
  "timestamp": "2026-05-19T19:28:15.814642",
  "level": "ERROR",
  "logger": "test",
  "module": "logger_config",
  "function": "<module>",
  "line": 240,
  "message": "捕获到异常",
  "exception": "Traceback..."
}
```

### 现在（原始格式）

```
2026-05-19 19:32:34,212 [ERROR] app <string>.<module>:14 - 发生除零错误
Traceback (most recent call last):
  File "<string>", line 12, in <module>
ZeroDivisionError: division by zero
```

---

## 📁 文件日志格式

### 普通日志文件 (app.log)

**格式**:
```
%(asctime)s [%(levelname)s] %(name)s %(module)s.%(funcName)s:%(lineno)d - %(message)s
```

**示例**:
```
2026-05-19 19:32:34,211 [INFO] app <string>.<module>:8 - 普通信息
2026-05-19 19:32:34,212 [ERROR] app <string>.<module>:14 - 发生除零错误
Traceback (most recent call last):
  File "<string>", line 12, in <module>
ZeroDivisionError: division by zero
```

### 错误日志文件 (app.error.log)

**格式**: 与普通日志相同，但仅记录ERROR及以上级别

**示例**:
```
2026-05-19 19:32:34,212 [ERROR] app <string>.<module>:14 - 发生除零错误
Traceback (most recent call last):
  File "<string>", line 12, in <module>
ZeroDivisionError: division by zero
```

---

## 🎯 控制台输出格式

### 彩色格式化

控制台仍保持彩色输出，便于快速识别：

```
2026-05-19 19:32:34 [DEBUG] module: 调试信息      # 青色
2026-05-19 19:32:34 [INFO] module: 普通信息        # 绿色
2026-05-19 19:32:34 [WARNING] module: 警告信息     # 黄色
2026-05-19 19:32:34 [ERROR] module: 错误信息       # 红色
2026-05-19 19:32:34 [CRITICAL] module: 严重错误    # 粗体红色
```

**格式**:
```
%(asctime)s [%(levelname)s] %(module)s: %(message)s
```

---

## 🔧 配置说明

### LoggerConfig.setup_logger()

```python
LoggerConfig.setup_logger(
    name='app',
    log_dir='logs',
    rotation='midnight',
    backup_days=30,
    level='DEBUG',
    enable_json=False,      # 默认False，不使用JSON格式
    enable_console=True
)
```

---

## 💡 异常日志最佳实践

### 1. 使用 logger.exception()

```python
try:
    result = 1 / 0
except Exception as e:
    logger.exception("发生除零错误")  # 自动包含完整堆栈
```

**输出**:
```
2026-05-19 19:32:34,212 [ERROR] app module.func:14 - 发生除零错误
Traceback (most recent call last):
  File "module.py", line 12, in func
    result = 1 / 0
ZeroDivisionError: division by zero
```

### 2. 使用 logger.error() + exc_info

```python
try:
    raise ValueError("测试错误")
except Exception as e:
    logger.error(f"捕获到异常: {type(e).__name__}: {str(e)}", exc_info=True)
```

**输出**:
```
2026-05-19 19:32:34,214 [ERROR] app module.func:20 - 捕获到异常: ValueError: 测试错误
Traceback (most recent call last):
  File "module.py", line 18, in func
    raise ValueError("测试错误")
ValueError: 测试错误
```

### 3. 在装饰器中记录异常

```python
from exception_handler import exception_handler

@exception_handler
def process_data():
    result = 1 / 0  # 异常会被自动记录和抛出
```

---

## 📊 日志文件结构

```
logs/
├── app.log                  # 应用日志（原始格式）
├── app.2026-05-19.log      # 历史日志（按天滚动）
├── app.error.log            # 错误日志（仅ERROR+，含堆栈）
├── business.log             # 业务日志
├── business.error.log
└── error.log                # 纯错误日志
```

---

## 🔍 查看日志

### 实时跟踪

```bash
# 跟踪应用日志
tail -f logs/app.log

# 跟踪错误日志
tail -f logs/error.log

# 查看最近100行
tail -100 logs/app.log
```

### 搜索日志

```bash
# 搜索特定关键词
grep "task-123" logs/app.log

# 搜索错误
grep "ERROR" logs/app.log

# 搜索异常
grep "Traceback" logs/app.log

# 搜索特定时间
grep "2026-05-19 19:" logs/app.log
```

### 查看完整堆栈

```bash
# 查看异常上下文（前后10行）
grep -A 10 "Traceback" logs/app.log
```

---

## ⚙️ 修改说明

### 主要变更

1. **logger_config.py**
   - `enable_json` 默认值改为 `False`
   - 移除JSON格式化器条件判断
   - 统一使用原始格式Formatter
   - 错误日志也使用原始格式

2. **格式化器**
   ```python
   # 文件和错误日志
   file_formatter = logging.Formatter(
       '%(asctime)s [%(levelname)s] %(name)s %(module)s.%(funcName)s:%(lineno)d - %(message)s'
   )
   
   # 控制台（彩色）
   console_formatter = ColoredFormatter(
       '%(asctime)s [%(levelname)s] %(module)s: %(message)s',
       datefmt='%Y-%m-%d %H:%M:%S'
   )
   ```

---

## ✅ 优势

### 1. 可读性提升
- ✅ 人类可读的文本格式
- ✅ 无需工具即可直接查看
- ✅ 支持grep等命令行工具

### 2. 异常信息完整
- ✅ 完整的traceback堆栈
- ✅ 包含文件名、行号、异常类型
- ✅ 便于快速定位问题

### 3. 兼容性好
- ✅ 所有文本编辑器可查看
- ✅ 支持日志分析工具
- ✅ 便于日志聚合系统处理

### 4. 控制台友好
- ✅ 保持彩色输出
- ✅ 快速识别日志级别
- ✅ 开发调试更方便

---

## 📝 使用示例

### 基本用法

```python
from logger_config import get_app_logger

logger = get_app_logger()

# 普通日志
logger.info("任务启动")
logger.warning("配置文件缺失")

# 异常日志（自动包含堆栈）
try:
    process_data()
except Exception as e:
    logger.exception("数据处理失败")
```

### 带上下文信息

```python
logger.info("订单处理完成", extra={
    'order_id': '123',
    'user_id': '456'
})
```

---

## 🔗 相关文档

- [logger_config.py](logger_config.py) - 日志系统源码
- [LOGGER_GUIDE.md](LOGGER_GUIDE.md) - 完整使用指南
- [CONSOLE_LOG_FORMAT.md](CONSOLE_LOG_FORMAT.md) - 控制台格式说明

---

**最后更新**: 2026-05-19  
**版本**: v1.1  
**变更**: 从JSON格式改为原始文本格式
