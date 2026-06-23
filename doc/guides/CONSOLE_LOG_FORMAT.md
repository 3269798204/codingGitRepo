# 日志系统 - 控制台输出格式说明

## 🎨 控制台输出特性

### 1. 彩色格式化

控制台日志采用ANSI颜色代码，不同级别使用不同颜色：

| 级别 | 颜色 | ANSI代码 | 说明 |
|------|------|----------|------|
| DEBUG | 🔵 青色 | `\033[36m` | 调试信息 |
| INFO | 🟢 绿色 | `\033[32m` | 普通信息 |
| WARNING | 🟡 黄色 | `\033[33m` | 警告信息 |
| ERROR | 🔴 红色 | `\033[31m` | 错误信息 |
| CRITICAL | 🔴 粗体红 | `\033[1;31m` | 严重错误 |

### 2. 输出格式

```
%(asctime)s [%(levelname)s] %(module)s: %(message)s
```

**时间格式**: `YYYY-MM-DD HH:MM:SS`

### 3. 示例输出

```bash
# 正常终端显示（带颜色）
2026-05-19 19:29:42 [DEBUG] logger_config: 这是一条DEBUG日志
2026-05-19 19:29:42 [INFO] logger_config: 这是一条INFO日志
2026-05-19 19:29:42 [WARNING] logger_config: 这是一条WARNING日志
2026-05-19 19:29:42 [ERROR] logger_config: 这是一条ERROR日志
2026-05-19 19:29:42 [CRITICAL] logger_config: 这是一条CRITICAL日志
```

---

## 🔧 实现细节

### ColoredFormatter 类

```python
class ColoredFormatter(logging.Formatter):
    """彩色控制台日志 formatter"""
    
    COLORS = {
        'DEBUG': '\033[36m',      # 青色
        'INFO': '\033[32m',       # 绿色
        'WARNING': '\033[33m',    # 黄色
        'ERROR': '\033[31m',      # 红色
        'CRITICAL': '\033[1;31m', # 粗体红色
    }
    RESET = '\033[0m'
    
    def format(self, record):
        color = self.COLORS.get(record.levelname, '')
        log_message = super().format(record)
        
        if color:
            levelname_colored = f"{color}{record.levelname}{self.RESET}"
            log_message = log_message.replace(record.levelname, levelname_colored, 1)
        
        return log_message
```

### 配置方式

```python
# 控制台处理器
console_handler = logging.StreamHandler(sys.stdout)
console_formatter = ColoredFormatter(
    '%(asctime)s [%(levelname)s] %(module)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
console_handler.setFormatter(console_formatter)
logger.addHandler(console_handler)
```

---

## 💡 优势

### 1. 快速识别
- ✅ 通过颜色快速区分日志级别
- ✅ 红色错误一目了然
- ✅ 绿色正常信息不刺眼

### 2. 可读性
- ✅ 时间戳清晰
- ✅ 模块名明确
- ✅ 消息简洁

### 3. 兼容性
- ✅ 支持所有现代终端
- ✅ Windows Terminal支持
- ✅ macOS Terminal支持
- ✅ Linux Terminal支持

---

## ⚙️ 自定义颜色

如果需要修改颜色，可以编辑 `ColoredFormatter` 类：

```python
COLORS = {
    'DEBUG': '\033[34m',      # 改为蓝色
    'INFO': '\033[37m',       # 改为白色
    'WARNING': '\033[35m',    # 改为紫色
    'ERROR': '\033[91m',      # 改为亮红色
    'CRITICAL': '\033[1;91m', # 改为亮粗体红色
}
```

**常用ANSI颜色代码**:
- `\033[30m` - 黑色
- `\033[31m` - 红色
- `\033[32m` - 绿色
- `\033[33m` - 黄色
- `\033[34m` - 蓝色
- `\033[35m` - 紫色
- `\033[36m` - 青色
- `\033[37m` - 白色
- `\033[90m` - 灰色

---

## 🔍 查看效果

### 测试脚本

```bash
cd /Users/ylm/IdeaProjects/voice-analysis-web
python3 logger_config.py
```

### 实时查看

```bash
# 跟踪应用日志
tail -f logs/app.log

# 跟踪错误日志
tail -f logs/error.log
```

---

## 📝 注意事项

### 1. 终端支持

大多数现代终端都支持ANSI颜色代码：
- ✅ macOS Terminal
- ✅ iTerm2
- ✅ Windows Terminal
- ✅ GNOME Terminal
- ✅ VS Code Terminal

### 2. 重定向到文件

当日志重定向到文件时，颜色代码会被保留。如果不需要颜色，可以使用：

```bash
# 去除颜色代码
python3 app.py 2>&1 | sed 's/\x1b\[[0-9;]*m//g' > output.log
```

### 3. 性能影响

彩色格式化对性能影响极小（< 0.01ms/条），可以忽略不计。

---

## 🎯 最佳实践

### 1. 开发环境

使用彩色输出，便于快速定位问题：

```python
logger = LoggerConfig.setup_logger('app', enable_console=True)
```

### 2. 生产环境

可以选择禁用控制台输出，仅记录文件日志：

```python
logger = LoggerConfig.setup_logger('app', enable_console=False)
```

### 3. CI/CD环境

某些CI系统可能不支持颜色，可以检测环境变量：

```python
import os
enable_color = not os.getenv('CI', False)
logger = LoggerConfig.setup_logger('app', enable_console=enable_color)
```

---

## 📊 对比

### 彩色 vs 黑白

**彩色输出**:
```
2026-05-19 19:29:42 [INFO] app: 任务启动
2026-05-19 19:29:42 [ERROR] app: 处理失败
```

**黑白输出**:
```
2026-05-19 19:29:42 [INFO] app: 任务启动
2026-05-19 19:29:42 [ERROR] app: 处理失败
```

彩色输出在大量日志中能更快定位错误和警告。

---

## 🔗 相关文档

- [logger_config.py](logger_config.py) - 日志系统源码
- [LOGGER_GUIDE.md](LOGGER_GUIDE.md) - 完整使用指南
- [exception_handler.py](exception_handler.py) - 异常处理系统

---

**最后更新**: 2026-05-19  
**版本**: v1.0
