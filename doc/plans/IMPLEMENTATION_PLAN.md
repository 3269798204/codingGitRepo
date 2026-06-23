# 语音识别 Web UI 系统 - 实现计划

## ✅ 已完成模块

1. **config.py** - 配置管理
   - 数据库配置
   - ASR 配置
   - 批处理配置
   - 硬件自适应配置推荐

2. **init_db.sql** - 数据库初始化脚本
   - 5 个核心表
   - 索引优化
   - 外键约束

3. **requirements.txt** - Python 依赖
   - 40+ 依赖包
   - 版本锁定

4. **README.md** - 项目文档
   - 快速开始指南
   - 模块说明
   - 配置建议

---

## 🔄 待实现模块（按优先级）

### 优先级 P0（核心功能）

#### 1. hardware_detector.py - 硬件检测模块

**预计代码量**: 150 行  
**实现要点**:
```python
class HardwareDetector:
    def detect_cpu(self) -> dict:
        # CPU 核心数、频率
        
    def detect_gpu(self) -> dict:
        # GPU 类型（CUDA/MPS/None）
        # GPU 内存
        
    def get_recommended_config(self) -> dict:
        # 根据硬件返回推荐配置
        
    def get_hardware_summary(self) -> str:
        # 生成硬件信息摘要
```

**关键逻辑**:
- 使用 `torch.cuda` 检测 NVIDIA GPU
- 使用 `torch.backends.mps` 检测 Apple Silicon
- 使用 `multiprocessing.cpu_count()` 获取 CPU 核心数
- 根据显存大小推荐模型（large/medium/small/base/tiny）

---

#### 2. asr_engine.py - ASR 引擎

**预计代码量**: 300 行  
**实现要点**:
```python
class ASREngine:
    def __init__(self, config: ASRConfig):
        # 加载模型（单例模式）
        
    def transcribe(self, audio_path: str) -> dict:
        # 执行语音识别
        # 返回：文本、分段、置信度等
        
    def post_process(self, text: str) -> str:
        # 文本后处理（去重、纠错）
        
    def analyze_with_llm(self, text: str) -> dict:
        # LLM 情感分析
```

**关键逻辑**:
- 模型缓存（避免重复加载）
- 超时控制
- 进度回调
- v2.2 版本的文本后处理逻辑复用

---

#### 3. database.py - 数据库操作

**预计代码量**: 250 行  
**实现要点**:
```python
class DatabaseManager:
    def __init__(self, config: DatabaseConfig):
        # 创建 SQLAlchemy 引擎和会话
        
    def create_task(self, task_data: dict) -> str:
        # 创建批处理任务
        
    def update_task_progress(self, task_id: str, progress: float):
        # 更新任务进度
        
    def save_audio_result(self, result: dict):
        # 保存音频处理结果
        
    def log_business_action(self, log_data: dict):
        # 记录业务日志
        
    def get_task_status(self, task_id: str) -> dict:
        # 查询任务状态
```

**关键逻辑**:
- SQLAlchemy ORM 模型定义
- 连接池管理
- 事务处理
- 异常处理

---

#### 4. csv_parser.py - CSV/Excel 解析器

**预计代码量**: 200 行  
**实现要点**:
```python
class CSVParser:
    def parse_file(self, file_path: str) -> pd.DataFrame:
        # 自动识别文件格式（csv/xlsx/xls）
        
    def detect_url_column(self, df: pd.DataFrame) -> str:
        # 智能检测音频 URL 列
        
    def validate_urls(self, urls: list) -> list:
        # 验证 URL 有效性
        
    def extract_audio_list(self, file_path: str) -> list:
        # 提取音频 URL 列表
```

**关键逻辑**:
- 支持 .csv, .xlsx, .xls 格式
- 列名关键词匹配（url, audio, voice, file, path, 链接, 地址）
- URL 格式验证
- 空值过滤

---

#### 5. batch_processor.py - 批处理引擎

**预计代码量**: 350 行  
**实现要点**:
```python
class BatchProcessor:
    def __init__(self, config: BatchConfig):
        # 初始化线程池
        
    def start_batch(self, task_id: str, audio_urls: list):
        # 启动批处理任务
        
    def process_single(self, audio_url: str) -> dict:
        # 处理单个音频
        
    def pause_task(self, task_id: str):
        # 暂停任务
        
    def resume_task(self, task_id: str):
        # 恢复任务
        
    def get_progress(self, task_id: str) -> dict:
        # 获取进度信息
```

**关键逻辑**:
- ThreadPoolExecutor 多线程并行
- CPU/GPU 资源协调（CPU 模式最多 4 并发，GPU 模式 1 并发）
- 任务状态管理（pending/running/paused/completed/failed）
- 进度实时更新
- 异常处理和重试机制

---

#### 6. checkpoint.py - 断点续传

**预计代码量**: 150 行  
**实现要点**:
```python
class CheckpointManager:
    def save_checkpoint(self, task_id: str, processed_ids: list):
        # 保存检查点
        
    def load_checkpoint(self, task_id: str) -> list:
        # 加载检查点
        
    def clear_checkpoint(self, task_id: str):
        # 清除检查点
        
    def get_unprocessed(self, task_id: str, all_ids: list) -> list:
        # 获取未处理的音频 ID
```

**关键逻辑**:
- 检查点数据序列化（JSON）
- MySQL 持久化存储
- 原子性更新
- 过期清理

---

### 优先级 P1（重要功能）

#### 7. logger.py - 业务日志

**预计代码量**: 120 行  
**实现要点**:
```python
class BusinessLogger:
    def log_info(self, module: str, action: str, message: str):
        # 记录 INFO 日志
        
    def log_error(self, module: str, action: str, error: Exception):
        # 记录 ERROR 日志
        
    def query_logs(self, task_id: str = None, level: str = None) -> list:
        # 查询日志
```

**关键逻辑**:
- 结构化日志格式
- 异步写入数据库
- 日志级别过滤
- 日志轮转（文件大小限制）

---

#### 8. report_generator.py - 统计报表

**预计代码量**: 200 行  
**实现要点**:
```python
class ReportGenerator:
    def generate_task_summary(self, task_id: str) -> dict:
        # 任务汇总报表
        
    def generate_emotion_report(self, task_id: str) -> dict:
        # 情绪分布报表
        
    def generate_performance_report(self, task_id: str) -> dict:
        # 性能监控报表
        
    def export_to_excel(self, report_data: dict, output_path: str):
        # 导出为 Excel
```

**关键逻辑**:
- SQL 聚合查询
- 数据可视化（Plotly）
- 报表缓存
- Excel 导出

---

#### 9. api.py - FastAPI 后端

**预计代码量**: 300 行  
**实现要点**:
```python
# RESTful API 端点

POST /api/tasks          # 创建批处理任务
GET  /api/tasks/{id}     # 查询任务状态
POST /api/tasks/{id}/pause   # 暂停任务
POST /api/tasks/{id}/resume  # 恢复任务
DELETE /api/tasks/{id}   # 删除任务

POST /api/upload         # 上传 CSV/Excel
GET  /api/results/{id}   # 查询处理结果
GET  /api/reports/{type} # 获取统计报表
GET  /api/logs           # 查询业务日志

GET  /api/hardware       # 获取硬件信息
POST /api/config         # 更新配置
```

**关键逻辑**:
- Pydantic 数据验证
- 异步请求处理
- CORS 配置
- 错误处理中间件

---

### 优先级 P2（UI 界面）

#### 10. app.py - Streamlit 主应用

**预计代码量**: 500 行  
**实现要点**:

**页面布局**:
```python
# 侧边栏
st.sidebar.header("⚙️ 配置")
model_select = st.sidebar.selectbox("模型", [...])
beam_size_select = st.sidebar.slider("Beam Size", 1, 5, 3)

# 主页面
st.title("🎙️ 语音识别分析系统 v3.0")

# Tab 1: 单个音频
tab1, tab2, tab3 = st.tabs(["单个音频", "批量处理", "历史任务"])

with tab1:
    audio_url = st.text_input("音频 URL")
    if st.button("开始分析"):
        # 调用 API
        
with tab2:
    uploaded_file = st.file_uploader("上传 CSV/Excel")
    if uploaded_file:
        # 解析文件
        # 显示预览
        # 开始批处理
        
with tab3:
    # 显示历史任务列表
    # 支持继续、查看、删除
```

**关键组件**:
- 硬件信息显示
- 配置面板
- 文件上传组件
- 进度条
- 结果展示表格
- 图表可视化（Plotly）
- 实时刷新

---

## 📊 开发时间估算

| 模块 | 优先级 | 预计工时 | 依赖关系 |
|------|--------|---------|---------|
| hardware_detector.py | P0 | 2 小时 | 无 |
| asr_engine.py | P0 | 4 小时 | hardware_detector |
| database.py | P0 | 3 小时 | 无 |
| csv_parser.py | P0 | 2 小时 | 无 |
| batch_processor.py | P0 | 5 小时 | asr_engine, database |
| checkpoint.py | P0 | 2 小时 | database |
| logger.py | P1 | 2 小时 | database |
| report_generator.py | P1 | 3 小时 | database |
| api.py | P1 | 4 小时 | 所有 P0 模块 |
| app.py | P2 | 6 小时 | api, 所有模块 |
| **总计** | - | **33 小时** | - |

---

## 🎯 实施步骤

### 第一阶段：核心引擎（P0）

1. ✅ 配置管理（已完成）
2. ✅ 数据库初始化（已完成）
3. 🔲 硬件检测模块
4. 🔲 ASR 引擎
5. 🔲 数据库操作层
6. 🔲 CSV 解析器
7. 🔲 批处理引擎
8. 🔲 断点续传

**预期成果**：命令行版本可用，支持批量处理

---

### 第二阶段：API 和日志（P1）

9. 🔲 业务日志
10. 🔲 统计报表
11. 🔲 FastAPI 后端

**预期成果**：RESTful API 可用，支持远程调用

---

### 第三阶段：Web UI（P2）

12. 🔲 Streamlit 主应用

**预期成果**：完整的 Web UI 系统

---

## 💡 开发建议

### 1. 模块化开发

每个模块独立测试，确保接口清晰：

```python
# 测试 hardware_detector
python -c "from hardware_detector import HardwareDetector; print(HardwareDetector().get_hardware_info())"

# 测试 csv_parser
python -c "from csv_parser import CSVParser; print(CSVParser().parse_file('test.csv'))"
```

---

### 2. 增量式开发

先实现最小可用版本（MVP），再逐步增强：

```
MVP: 单个音频分析 → 批量处理 → 断点续传 → Web UI
```

---

### 3. 错误处理

每个模块都要有完善的异常处理：

```python
try:
    result = process_audio(url)
except TimeoutError:
    log_error("Timeout processing audio")
    save_failed_status(url)
except Exception as e:
    log_error(f"Unexpected error: {e}")
    raise
```

---

### 4. 日志记录

关键操作都要记录日志：

```python
logger.info(f"Task {task_id} started with {len(urls)} audios")
logger.debug(f"Processing audio: {url}")
logger.error(f"Failed to process {url}: {error}")
```

---

## 🚀 下一步行动

**建议立即开始实现**：

1. **hardware_detector.py** - 最简单，无依赖
2. **database.py** - 核心数据存储
3. **asr_engine.py** - 复用 v2.2 版本的逻辑

我可以立即开始实现这些模块，您希望我先实现哪一个？或者您有其他优先级调整？
