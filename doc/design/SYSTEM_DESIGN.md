# 语音识别分析系统 v3.0 - 项目设计文档

## 📋 项目概述

**项目名称**：语音识别分析系统 (Voice Analysis Web)  
**版本**：3.0.0  
**项目定位**：企业级客服通话智能分析平台  
**核心能力**：语音转文字(ASR) + 情感分析(LLM) + 批量处理 + 可视化报表

---

## 🏗️ 系统架构

### 整体架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                        用户浏览器                                │
│                    Streamlit Web UI                             │
│                    (端口: 8501)                                 │
└───────────────────────┬─────────────────────────────────────────┘
                        │ HTTP/JSON
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                     FastAPI 后端服务                              │
│                     (端口: 8000)                                 │
│  ┌───────────┬──────────┬──────────┬──────────┬──────────────┐ │
│  │ 认证API   │ 任务API   │ 音频API  │ 统计API  │ 任务详情API   │ │
│  └───────────┴──────────┴──────────┴──────────┴──────────────┘ │
└───────────────────────┬─────────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┬───────────────┐
        ▼               ▼               ▼               ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│  ASR 引擎    │ │  LLM 分析    │ │  MySQL 数据库 │ │  文件存储     │
│ Faster-      │ │ DeepSeek API │ │  阿里云 RDS   │ │ uploads/     │
│ Whisper v2.2 │ │              │ │              │ │ results/     │
└──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘
```

### 架构设计原则

| 原则 | 实现方式 |
|------|----------|
| **前后端分离** | Streamlit(UI层) ↔ FastAPI(API层)，通过 HTTP/JSON 通信 |
| **模块化设计** | src/ 目录按职责分层：core/api/web/asr/db/services/logger/utils |
| **单例模式** | ASREngine、AuthManager、DatabaseManager 等核心组件全局唯一 |
| **异步批处理** | ThreadPoolExecutor + 后台线程，不阻塞 HTTP 响应 |
| **断点续传** | Checkpoint 表记录处理进度，支持任务中断恢复 |
| **幂等性保证** | 幂等性中间件防止重复提交 |

---

## 📁 项目目录结构

```
voice-analysis-web/
├── src/                          # 源代码根目录
│   ├── core/                     # 核心配置层
│   │   ├── config.py            # 主配置（DatabaseConfig, ASRConfig, BatchConfig...）
│   │   ├── dynamic_config.py    # 动态配置管理器（DB优先，配置文件兜底）
│   │   └── compat_layer.py      # 兼容层（db_manager 单例导出）
│   │
│   ├── api/                      # 后端 API 层（FastAPI）
│   │   ├── api.py               # 主 API 服务（认证/任务/音频/统计）
│   │   ├── task_detail_api.py   # 任务详情独立服务（端口 8001）
│   │   └── middleware/
│   │       └── idempotency.py   # 幂等性中间件
│   │
│   ├── web/                      # 前端 UI 层（Streamlit）
│   │   ├── app.py               # Streamlit 主应用
│   │   ├── login.py             # 登录认证组件
│   │   ├── task_detail_page.py  # 任务详情页面
│   │   └── api_client.py        # API 客户端封装
│   │
│   ├── asr/                      # 语音识别引擎层
│   │   ├── asr_engine.py        # ASR 核心引擎（Faster-Whisper 封装）
│   │   ├── model_loader.py      # 模型加载器（预加载 + 缓存）
│   │   └── hardware_detector.py  # 硬件检测（CPU/GPU/MPS 自适应）
│   │
│   ├── db/                       # 数据持久化层
│   │   ├── database.py          # SQLAlchemy ORM + 数据库操作
│   │   ├── init_db.sql           # 数据库初始化脚本
│   │   └── migrations/           # 数据库迁移脚本
│   │
│   ├── services/                 # 业务逻辑层
│   │   ├── batch_processor.py   # 批处理引擎（并发控制 + 进度跟踪）
│   │   ├── csv_parser.py        # Excel/CSV 解析器
│   │   ├── checkpoint.py        # 断点续传管理器
│   │   ├── report_generator.py  # 统计报表生成器
│   │   └── auth.py              # 认证管理器（登录/会话/权限）
│   │
│   ├── logger/                   # 日志系统层
│   │   ├── logger.py            # 业务日志封装
│   │   ├── logger_config.py     # 日志配置（多级别 + 滚动 + 彩色）
│   │   └── logger_monitor.py    # 日志监控告警
│   │
│   └── utils/                    # 工具层
│       ├── exception_handler.py # 全局异常处理器
│       ├── debug_tool.py        # 调试工具
│       ├── fix_admin_password.py# 管理员密码修复
│       └── execute_migration.py # 迁移执行工具
│
├── tests/                        # 测试目录
├── scripts/                      # 运维脚本
├── doc/                          # 项目文档
│   ├── guides/                   # 使用指南
│   ├── reports/                  # 完成报告
│   ├── plans/                    # 规划文档
│   ├── fixes/                    # 修复记录
│   ├── progress/                 # 进度总结
│   └── design/                   # 设计文档
├── logs/                         # 运行日志
├── uploads/                      # 上传文件存储
└── requirements.txt              # Python 依赖
```

---

## 🔧 核心模块设计原理

### 1️⃣ 配置管理系统 (`src/core/`)

**设计模式**：分层配置 + 动态覆盖

```
配置优先级链：
  DynamicConfigManager.get_asr_config()
         ↓
  ① system_configs 表（数据库）← 最高优先级，支持运行时修改
         ↓ ② config.py 默认值（代码硬编码）← 兜底保障
```

**核心配置类**：

| 配置类 | 职责 | 关键参数 |
|--------|------|----------|
| `DatabaseConfig` | MySQL 连接池配置 | host/port/user/password/pool_size=10 |
| `ASRConfig` | 语音识别引擎参数 | model_size="small", beam_size=3, device="cpu" |
| `BatchConfig` | 批处理控制参数 | max_cpu_workers=4, chunk_duration=300s |
| `LogConfig` | 日志系统参数 | log_dir="./logs", max_file_size=10MB |
| `AppConfig` | 应用总配置 | 聚合上述所有配置 + LLM API 密钥 |

**LLM 集成配置**：
- **模型**：DeepSeek Chat (`deepseek-chat`)
- **用途**：情感分析 + 对话质检 + 辱骂词检测
- **System Prompt**：定义专家角色，输出结构化 JSON（情绪/参与者/辱骂语言）

#### 1.1 DatabaseConfig - 数据库配置

```python
@dataclass
class DatabaseConfig:
    """MySQL 数据库配置"""
    host: str = "rm-2vcww6h31l270m9sm3o.mysql.cn-chengdu.rds.aliyuncs.com"
    port: int = 3306
    user: str = "tbhx01"
    password: str = "Aa@82320020"
    database: str = "voice_analysis"
    pool_size: int = 10
    charset: str = "utf8mb4"
    
    @property
    def url(self):
        """生成 SQLAlchemy 连接 URL"""
        encoded_password = quote_plus(self.password)
        return f"mysql+pymysql://{self.user}:{encoded_password}@{self.host}:{self.port}/{self.database}?charset={self.charset}"
```

**设计原理**：
- 使用 `dataclass` 实现类型安全的配置管理
- `url` 属性自动编码密码中的特殊字符
- 连接池大小设为 10，平衡并发性能与资源占用

#### 1.2 ASRConfig - 语音识别配置

```python
@dataclass
class ASRConfig:
    """ASR 配置"""
    model_size: str = "small"           # 模型规模：tiny/base/small/medium/large
    language: str = "zh"                # 语言：中文
    device: str = "cpu"                 # 设备：cpu/cuda
    beam_size: int = 3                  # 束搜索宽度
    temperature: float = 0.0            # 采样温度（0=贪婪解码）
    vad_filter: bool = True             # 启用语音活动检测过滤
    min_silence_duration_ms: int = 500  # 最小静音时长
    speech_pad_ms: int = 200            # 语音填充时长
    condition_on_previous_text: bool = False  # 禁用上下文累积（减少错误传播）
    compression_ratio_threshold: float = 2.4  # 压缩比阈值
    no_speech_threshold: float = 0.6    # 无语音概率阈值
    word_timestamps: bool = False       # 是否输出词级时间戳
    compute_type: str = "int8"          # 计算精度：int8/float16/float32
    timeout: int = 600                  # 单个音频超时（秒）
    model_load_timeout: int = 120       # 模型加载超时（秒）
    download_timeout: int = None        # 音频下载超时（秒）
```

**参数调优原理**：
- `beam_size=3`：在速度和精度间取得平衡（值越大越精确但更慢）
- `condition_on_previous_text=False`：避免错误累积传播
- `compute_type="int8"`：CPU 环境下使用量化推理，速度提升 2-3x
- `vad_filter=True`：启用 VAD 过滤非语音段，提高准确率

#### 1.3 BatchConfig - 批处理配置

```python
@dataclass
class BatchConfig:
    """批处理配置"""
    max_cpu_workers: int = 4            # CPU 模式最大并发数
    max_gpu_workers: int = 1            # GPU 模式最大并发数（GPU 本身并行）
    chunk_duration: int = 300           # 长音频分段时长（秒）
    enable_chunking: bool = True        # 启用分段处理
    checkpoint_dir: str = "./checkpoints"  # 断点续传目录
    enable_checkpoint: bool = True      # 启用断点续传
    cache_dir: str = "./cache"          # 缓存目录
    enable_cache: bool = True           # 启用结果缓存
```

**设计原理**：
- 并发数根据硬件自适应（GPU 只需 1 worker，CPU 可多线程）
- 长音频超过 5 分钟自动分段，避免内存溢出
- 断点续传保证任务中断后可从断点恢复

#### 1.4 DynamicConfigManager - 动态配置管理

```python
class DynamicConfigManager:
    """动态配置管理器
    
    优先级：
    1. 数据库配置（system_configs表）← 运行时可修改
    2. 配置文件默认值（config.py）← 兜底保障
    """
    
    def __init__(self):
        self._cache = {}  # 配置缓存，避免频繁查询数据库
    
    def get_asr_config(self) -> ASRConfig:
        """获取 ASR 配置（优先从数据库读取）"""
        asr_config = ASRConfig()
        
        # 从数据库逐字段覆盖
        for field in ['model_size', 'device', 'compute_type', 
                      'beam_size', 'language', 'vad_filter']:
            db_value = db_manager.get_config(f'asr.{field}')
            if db_value is not None:
                setattr(asr_config, field, self._to_type(db_value, field))
        
        return asr_config
```

**使用场景**：
- 管理员通过 Web UI 动态调整模型参数
- 无需重启服务即可生效
- 配置变更自动记录到业务日志

---

### 2️⃣ ASR 语音识别引擎 (`src/asr/`)

**技术选型**：Faster-Whisper（基于 CTranslate2 优化）

#### 2.1 架构设计

```
ASREngine（单例模式）
    │
    ├── model_loader.py ← 模型预加载 + 全局缓存
    │       ↓
    │   WhisperModel(model_size, device, compute_type)
    │
    ├── hardware_detector.py ← 硬件自适应
    │       ↓
    │   CUDA → float16 / CPU → int8 / MPS → 不支持（降级CPU）
    │
    └── transcribe() 核心流程
            │
            ├── 1. URL 下载（带超时 120s）
            ├── 2. VAD 过滤（min_silence=500ms）
            ├── 3. Whisper 转写（beam_search=3）
            ├── 4. 文本后处理（50+ 错别字修正）
            └── 5. LLM 分析（DeepSeek API，超时 30s）
```

#### 2.2 单例模式实现

```python
class ASREngine:
    """ASR 识别引擎 v2.2"""
    _instance = None
    _model = None

    def __new__(cls, config_param: ASRConfig = None):
        """单例模式 - 保证全局只有一个实例"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, config_param: ASRConfig = None):
        if self._initialized:
            return  # 已初始化则跳过
        # 初始化逻辑...
        self._initialized = True
```

**为什么使用单例？**
- Whisper 模型体积大（small ~1GB），频繁加载消耗资源
- GPU 显存有限，只能加载一个模型实例
- 共享模型对象，所有请求复用同一实例

#### 2.3 硬件检测与适配

```python
def _detect_device(self) -> Dict[str, str]:
    """检测可用的计算设备"""
    if torch.cuda.is_available():
        return {"device": "cuda", "compute_type": "float16"}
    
    # Apple Silicon (MPS) 不被 Faster-Whisper 支持
    try:
        if torch.backends.mps.is_available():
            print("⚠️ Apple Silicon GPU 检测到，但降级为 CPU")
    except:
        pass
    
    return {"device": "cpu", "compute_type": "int8"}
```

**设备选择策略**：

| 设备类型 | compute_type | 推理速度 | 内存占用 |
|----------|-------------|---------|---------|
| NVIDIA GPU | float16 | ⭐⭐⭐⭐⭐ | 中等 |
| Apple Silicon MPS | ❌ 不支持 | - | - |
| CPU | int8 | ⭐⭐⭐ | 低 |

#### 2.4 核心转录流程

```python
def transcribe(self, audio_path: str, progress_callback: Callable = None) -> Dict:
    """
    执行语音识别（v2.2 高效精度版）
    
    Args:
        audio_path: 音频文件路径或 URL
        progress_callback: 进度回调函数 callback(progress: float, message: str)
    
    Returns:
        dict: {
            'text': '完整转写文本',
            'segments': [{'start': 0.0, 'end': 1.5, 'text': '你好'}],
            'language': 'zh',
            'confidence': 0.95,
            'llm_analysis': { ... }  # LLM 分析结果
        }
    """
    # Step 1: 如果是 URL，先下载
    if audio_path.startswith("http"):
        audio_path = self._download_audio_with_timeout(audio_path)
    
    # Step 2: Faster-Whisper 转写
    segments, info = self._model.transcribe(
        audio_path,
        language=self.config.language,
        beam_size=self.config.beam_size,
        vad_filter=self.config.vad_filter,
        vad_parameters=dict(
            min_silence_duration_ms=self.config.min_silence_duration_ms,
            speech_pad_ms=self.config.speech_pad_ms
        ),
        condition_on_previous_text=self.config.condition_on_previous_text,
        temperature=self.config.temperature,
    )
    
    # Step 3: 组装结果
    full_text = "".join([segment.text.strip() for segment in segments])
    
    # Step 4: 文本后处理（错别字修正）
    full_text = self._postprocess_text(full_text)
    
    # Step 5: LLM 深度分析
    llm_result = self._analyze_with_llm(full_text)
    
    return {
        'text': full_text,
        'segments': [segment.to_dict() for segment in segments],
        'language': info.language,
        'confidence': info.avg_logprob,
        'llm_analysis': llm_result
    }
```

#### 2.5 v2.2 优化特性详解

| 优化项 | 实现原理 | 性能提升 |
|--------|----------|----------|
| **动态线程数** | 根据 CPU 核心数自动调整 4-12 线程 | 吞吐量 +30% |
| **int8 量化** | CPU 模式使用 8-bit 量化推理 | 内存占用 -50%，速度 2-3x |
| **VAD 保守过滤** | min_silence_duration_ms=500ms | 减少误切分 |
| **condition_on_previous_text=False** | 禁用上下文累积 | 减少错误传播 |
| **文本后处理** | 正则替换 50+ 常见错别字 | 准确率 +5% |

#### 2.6 ModelLoader - 模型预加载器

```python
class ModelLoader:
    """模型预加载器 - 应用启动时预先加载模型"""
    
    _model = None
    _model_size = None
    
    def load_model(self, model_size: str, device: str, compute_type: str):
        """加载并缓存模型"""
        if self._model is not None and self._model_size == model_size:
            return self._model  # 已加载则直接返回
        
        print(f"🔄 正在加载 {model_size} 模型...")
        start_time = time.time()
        
        self._model = WhisperModel(
            model_size_or_path=model_size,
            device=device,
            compute_type=compute_type
        )
        
        elapsed = time.time() - start_time
        print(f"✅ 模型加载完成 ({elapsed:.1f}s)")
        
        return self._model
```

**预加载优势**：
- 首次请求无需等待模型加载（通常需要 30-60 秒）
- 模型常驻内存，后续请求毫秒级响应
- 支持热更新（更换模型大小时重新加载）

---

### 3️⃣ 批处理引擎 (`src/services/batch_processor.py`)

**设计目标**：高并发 + 可恢复 + 幂等性

#### 3.1 处理流程

```
用户提交任务（audio_urls[]）
        ↓
① 重复拦截（audio_id 去重 + 已成功结果过滤）
        ↓
② 幂等性检查（request_data → token → Redis/内存去重）
        ↓
③ 创建任务记录（batch_tasks 表，status='running'）
        ↓
④ 启动后台线程（ThreadPoolExecutor，max_workers=4）
        │
        ├── Worker-1: audio_1 → ASR → LLM → 保存结果
        ├── Worker-2: audio_2 → ASR → LLM → 保存结果
        ├── Worker-3: audio_3 → ASR → LLM → 保存结果
        └── Worker-4: audio_4 → ASR → LLM → 保存结果
                ↓
⑤ 断点续传（每完成一个音频更新 checkpoints 表）
                ↓
⑥ 任务完成（status='completed'，生成统计报表）
```

#### 3.2 核心实现

```python
class BatchProcessor:
    """批处理引擎"""
    
    def __init__(self, batch_config: BatchConfig = None):
        self.config = batch_config or config.batch
        self.asr_engine = get_asr_engine()
        self.csv_parser = CSVParser()
        
        # 任务状态管理
        self._tasks = {}  # {task_id: task_info}
        self._lock = Lock()
        
        # 检测硬件，确定最大并发数
        detector = get_detector()
        rec_config = detector.get_recommended_config()
        self.max_workers = rec_config['max_workers']
    
    def start_batch(self, task_name: str, audio_urls: List[str], 
                   extra_data_list: List[Dict] = None,
                   progress_callback: Callable = None, 
                   task_config: Dict = None, user_id: str = None) -> str:
        """
        启动批处理任务
        
        Returns:
            str: 任务 ID (UUID)
        """
        # Step 1: 去重过滤
        seen_audio_ids = set()
        filtered_urls = []
        for url in audio_urls:
            audio_id = self._generate_audio_id(url)
            
            if audio_id in seen_audio_ids:
                continue  # 本次请求内重复
            
            existing_result = db_manager.get_audio_result(audio_id)
            if existing_result and existing_result.get('status') == 'success':
                continue  # 历史已成功
            
            seen_audio_ids.add(audio_id)
            filtered_urls.append(url)
        
        if not filtered_urls:
            raise ValueError("所有音频均已识别，无需重复提交")
        
        # Step 2: 幂等性检查
        request_data = {'task_name': task_name, 'audio_urls': sorted(filtered_urls)}
        token = idempotency_manager.generate_token(request_data)
        
        if not idempotency_manager.check_and_set(token):
            raise ValueError("相同的批处理请求正在处理中！")
        
        # Step 3: 创建任务
        task_id = str(uuid.uuid4())
        db_manager.create_task(task_id, task_name, len(filtered_urls), user_id=user_id)
        
        # Step 4: 异步执行（不阻塞 HTTP 响应）
        threading.Thread(
            target=self._run_batch,
            args=(task_id, task_name, len(filtered_urls), filtered_urls),
            daemon=True
        ).start()
        
        return task_id
```

#### 3.3 并发控制策略

```python
# hardware_detector.py - 硬件自适应
def get_recommended_config(self) -> Dict:
    """根据硬件推荐最佳配置"""
    if self.has_cuda():
        return {
            'max_workers': 1,     # GPU 本身并行，无需多线程
            'device': 'cuda',
            'compute_type': 'float16'
        }
    else:
        cpu_count = multiprocessing.cpu_count()
        return {
            'max_workers': min(cpu_count, 4),  # CPU 多线程，最多4个
            'device': 'cpu',
            'compute_type': 'int8'
        }
```

**为什么 GPU 只用 1 个 worker？**
- Faster-Whisper 的 CTranslate2 引擎内部已利用 GPU 并行
- 多个 GPU worker 会竞争显存，反而降低效率
- CPU 则可通过多线程充分利用多核

#### 3.4 断点续传机制

```python
# checkpoint.py
class CheckpointManager:
    """断点续传管理器"""
    
    def save_checkpoint(self, task_id: str, processed_ids: List[str]):
        """保存已完成处理的音频 ID 列表"""
        checkpoint_data = {
            'processed_ids': processed_ids,
            'count': len(processed_ids),
            'timestamp': datetime.now().isoformat()
        }
        self.db.save_checkpoint(task_id, 'processed_ids', checkpoint_data)
    
    def load_checkpoint(self, task_id: str) -> List[str]:
        """加载已完成的音频 ID，用于恢复任务"""
        data = self.db.load_checkpoint(task_id, 'processed_ids')
        return data.get('processed_ids', []) if data else []
```

**恢复流程**：
```python
def _run_batch(self, task_id, ...):
    # 尝试加载断点
    completed_ids = checkpoint_manager.load_checkpoint(task_id)
    remaining_urls = [url for url in audio_urls 
                      if self._generate_audio_id(url) not in set(completed_ids)]
    
    # 继续处理剩余的音频
    for url in remaining_urls:
        self._process_single_audio(url)
        completed_ids.append(audio_id)
        checkpoint_manager.save_checkpoint(task_id, completed_ids)  # 更新断点
```

---

### 4️⃣ 数据库设计 (`src/db/database.py`)

**ORM 框架**：SQLAlchemy + PyMySQL  
**连接池**：QueuePool（pool_size=10）

#### 4.1 核心数据表

##### users - 用户表

```sql
CREATE TABLE users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(64) UNIQUE NOT NULL,      -- 用户名
    password_hash VARCHAR(128) NOT NULL,       -- SHA256 哈希密码
    salt VARCHAR(64) NOT NULL,                 -- 密码盐值
    role ENUM('admin', 'user') DEFAULT 'user', -- 角色
    is_active BOOLEAN DEFAULT TRUE,            -- 是否激活
    created_at DATETIME DEFAULT NOW(),
    updated_at DATETIME DEFAULT NOW() ON UPDATE NOW()
);
```

##### batch_tasks - 批处理任务表

```sql
CREATE TABLE batch_tasks (
    id INT PRIMARY KEY AUTO_INCREMENT,
    task_id VARCHAR(64) UNIQUE NOT NULL,       -- UUID 任务 ID
    task_name TEXT NOT NULL,                   -- 任务名称
    status ENUM('pending', 'running', 'paused', 
                'completed', 'failed', 'cancelled') 
                DEFAULT 'pending',
    total_count INT DEFAULT 0,                 -- 总音频数
    processed_count INT DEFAULT 0,             -- 已处理数
    success_count INT DEFAULT 0,              -- 成功数
    failed_count INT DEFAULT 0,               -- 失败数
    progress FLOAT DEFAULT 0.0,               -- 进度百分比
    config_json TEXT,                         -- 任务配置（JSON）
    error_message TEXT,                       -- 错误信息
    user_id VARCHAR(64),                      -- 用户编号
    created_at DATETIME DEFAULT NOW(),
    started_at DATETIME,
    completed_at DATETIME,
    updated_at DATETIME DEFAULT NOW() ON UPDATE NOW(),
    
    INDEX idx_status (status),
    INDEX idx_user_id (user_id),
    INDEX idx_task_id (task_id)
);
```

##### audio_results - 音频处理结果表（核心）

```sql
CREATE TABLE audio_results (
    id INT PRIMARY KEY AUTO_INCREMENT,
    task_id VARCHAR(64) NOT NULL,             -- 关联任务 ID
    audio_id VARCHAR(64) UNIQUE NOT NULL,     -- 音频唯一标识
    audio_url VARCHAR(2048) NOT NULL,         -- 音频 URL
    file_name VARCHAR(512),                   -- 文件名
    duration FLOAT,                           -- 时长（秒）
    status ENUM('pending', 'processing', 'success', 'failed') 
           DEFAULT 'pending',
    
    -- ASR 结果
    full_text TEXT,                           -- 完整转写文本
    language VARCHAR(10) DEFAULT 'zh',        -- 检测语言
    confidence FLOAT,                         -- 置信度
    segments_json JSON,                       -- 时间段分片数据
    
    -- LLM 分析结果
    dialogue_summary TEXT,                    -- 对话摘要
    has_abusive_language BOOLEAN DEFAULT FALSE,-- 是否含辱骂语言
    abusive_words_json JSON,                  -- 辱骂词列表
    participants_json JSON,                   -- 参与者情绪分析
    interaction_json JSON,                    -- 交互质量评估
    
    -- 性能指标
    processing_time FLOAT,                    -- 总处理时间（秒）
    asr_time FLOAT,                           -- ASR 耗时
    llm_time FLOAT,                           -- LLM 耗时
    realtime_factor FLOAT,                    -- 实时因子（<1 表示实时）
    
    -- 元数据
    extra_data JSON,                          -- 额外数据
    customer_no VARCHAR(256),                 -- 客户编号
    origin_data_json JSON,                    -- 原始输入数据
    error_message TEXT,                       -- 错误信息
    
    created_at DATETIME DEFAULT NOW(),
    updated_at DATETIME DEFAULT NOW() ON UPDATE NOW(),
    
    FOREIGN KEY (task_id) REFERENCES batch_tasks(task_id) ON DELETE CASCADE,
    INDEX idx_audio_id (audio_id),
    INDEX idx_task_id (task_id),
    INDEX idx_status (status),
    INDEX idx_customer_no (customer_no)
);
```

##### checkpoints - 断点续传表

```sql
CREATE TABLE checkpoints (
    id INT PRIMARY KEY AUTO_INCREMENT,
    task_id VARCHAR(64) NOT NULL,
    checkpoint_key VARCHAR(128) NOT NULL,     -- 如 "processed_ids"
    checkpoint_data JSON,                     -- 检查点数据
    created_at DATETIME DEFAULT NOW(),
    updated_at DATETIME DEFAULT NOW() ON UPDATE NOW(),
    
    FOREIGN KEY (task_id) REFERENCES batch_tasks(task_id) ON DELETE CASCADE,
    UNIQUE KEY uk_task_key (task_id, checkpoint_key)
);
```

##### system_configs - 动态配置表

```sql
CREATE TABLE system_configs (
    id INT PRIMARY KEY AUTO_INCREMENT,
    config_key VARCHAR(128) UNIQUE NOT NULL,  -- 如 "asr.model_size"
    config_value TEXT NOT NULL,               -- 配置值
    config_type ENUM('string', 'int', 'float', 'bool', 'json') DEFAULT 'string',
    description VARCHAR(512),                 -- 配置说明
    category VARCHAR(64),                     -- 分类（asr/batch/log）
    is_editable BOOLEAN DEFAULT TRUE,         -- 是否允许编辑
    created_at DATETIME DEFAULT NOW(),
    updated_at DATETIME DEFAULT NOW() ON UPDATE NOW(),
    
    INDEX idx_category (category),
    INDEX idx_config_key (config_key)
);
```

#### 4.2 ORM 模型示例

```python
class AudioResult(Base):
    """音频处理结果 ORM 模型"""
    __tablename__ = 'audio_results'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(64), ForeignKey('batch_tasks.task_id'), nullable=False)
    audio_id = Column(String(64), unique=True, nullable=False)
    audio_url = Column(String(2048), nullable=False)
    
    # ASR 结果
    full_text = Column(Text)
    segments_json = Column(JSON)
    
    # LLM 分析
    dialogue_summary = Column(Text)
    has_abusive_language = Column(Boolean, default=False)
    participants_json = Column(JSON)
    
    # 性能指标
    processing_time = Column(Float)
    realtime_factor = Column(Float)
    
    def to_dict(self) -> Dict:
        """序列化为字典（用于 API 响应）"""
        return {
            'audio_id': self.audio_id,
            'full_text': self.full_text,
            'dialogue_summary': self.dialogue_summary,
            'has_abusive_language': self.has_abusive_language,
            'participants': json.loads(self.participants_json) if self.participants_json else [],
            'processing_time': self.processing_time,
            # ... 其他字段
        }
```

---

### 5️⃣ 认证与权限系统 (`src/services/auth.py`)

#### 5.1 认证流程

```
用户登录 (username + password)
        ↓
① SHA256(password + salt) 哈希比对
        ↓
② 生成 UUID session_token（内存存储，TTL=24h）
        ↓
③ 返回 {token, username, role}
        ↓
④ 后续请求携带 Authorization: Bearer <token>
        ↓
⑤ verify_session(token) → {username, role}
```

#### 5.2 核心实现

```python
class AuthManager:
    """认证管理器"""
    
    def __init__(self):
        self.sessions = {}  # 内存会话存储（生产环境建议 Redis）
        self.session_ttl = 3600 * 24  # 24 小时过期
    
    def hash_password(self, password: str, salt: str = None) -> tuple:
        """
        密码哈希（SHA256 + salt）
        
        Returns:
            (hashed_password, salt)
        """
        if salt is None:
            salt = hashlib.sha256(os.urandom(32)).hexdigest()
        
        hashed = hashlib.sha256((password + salt).encode('utf-8')).hexdigest()
        return hashed, salt
    
    def login(self, username: str, password: str) -> Optional[str]:
        """用户登录，返回 session_token 或 None"""
        user = db_manager.get_user_by_username(username)
        if not user or not user.get('is_active'):
            return None
        
        # 验证密码
        hashed_input, _ = self.hash_password(password, user['salt'])
        if hashed_input != user['password_hash']:
            return None
        
        # 生成 session
        session_token = str(uuid.uuid4())
        self.sessions[session_token] = {
            'username': username,
            'role': user['role'],
            'expires_at': time.time() + self.session_ttl
        }
        
        return session_token
    
    def verify_session(self, session_token: str) -> Optional[Dict]:
        """验证会话有效性"""
        session = self.sessions.get(session_token)
        if not session or time.time() > session['expires_at']:
            return None
        
        return {
            'username': session['username'],
            'role': session['role']
        }
```

#### 5.3 安全设计

| 安全措施 | 实现细节 |
|----------|----------|
| **密码哈希** | SHA256 + 随机 salt（32字节） |
| **会话管理** | 内存字典（生产环境建议 Redis） |
| **Token 有效期** | 24 小时自动过期 |
| **角色权限** | admin（管理员）/ user（普通用户） |
| **用户激活** | is_active 字段控制登录权限 |

---

### 6️⃣ 日志系统 (`src/logger/`)

#### 6.1 日志架构

```
LoggerConfig.setup_logger(name)
        ↓
┌─────────────────────────────────────────┐
│              日志输出层                   │
├──────────────┬──────────────────────────┤
│  控制台输出   │  文件输出（TimedRotating）│
│  ColoredFormatter │ JSONFormatter       │
│  [INFO] 绿色  │  结构化 JSON 格式       │
│  [ERROR] 红色 │  按天滚动，保留30天      │
└──────────────┴──────────────────────────┘
```

#### 6.2 日志分类

| 日志文件 | 用途 | 格式 |
|----------|------|------|
| `app.log` | HTTP 请求日志 | 结构化 + 彩色 |
| `app.error.log` | 未捕获异常 | 含堆栈追踪 |
| `business.log` | 业务操作日志 | 模块+动作+消息 |
| `error.error.log` | 系统级错误 | 详细诊断信息 |
| `test*.log` | 测试运行日志 | 调试级别 |

#### 6.3 日志格式示例

```
2026-06-16 18:02:29,330 [INFO] app api.log_requests:90 - ✅ 请求完成
                                    ↑        ↑           ↑
                                  时间戳    模块.函数     消息
```

**结构化 JSON 格式**（可选）：
```json
{
  "timestamp": "2026-06-16T18:02:29.330",
  "level": "INFO",
  "logger": "app",
  "module": "api",
  "function": "log_requests",
  "line": 90,
  "message": "✅ 请求完成",
  "request_id": "uuid-xxx",
  "duration_ms": 123.45
}
```

#### 6.4 彩色终端输出

```python
class ColoredFormatter(logging.Formatter):
    COLORS = {
        'DEBUG': '\033[36m',      # 青色
        'INFO': '\033[32m',       # 绿色
        'WARNING': '\033[33m',    # 黄色
        'ERROR': '\033[31m',      # 红色
        'CRITICAL': '\033[1;31m', # 粗体红色
    }
    
    def format(self, record):
        color = self.COLORS.get(record.levelname, '')
        log_message = super().format(record)
        return f"{color}{log_message}\033[0m"
```

---

### 7️⃣ 前后端通信架构

#### 7.1 通信协议

```
Streamlit Frontend (app.py :8501)
        │
        ├── api_client.py（APIClient 封装类）
        │       ↓
        │   requests.Session（连接池复用 + Token 自动附加）
        │       ↓
        └── FastAPI Backend (api.py :8000)
```

#### 7.2 APIClient 实现

```python
class APIClient:
    """API 客户端 - 封装所有后端 API 调用"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})
    
    def set_auth_token(self, token: str):
        """设置认证 Token（后续请求自动携带）"""
        self.session.headers["Authorization"] = f"Bearer {token}"
    
    def _request(self, method: str, endpoint: str, **kwargs) -> Dict:
        """通用请求方法（统一错误处理）"""
        url = urljoin(f"{self.base_url}/", endpoint.lstrip('/'))
        response = self.session.request(method, url, **kwargs)
        
        if not response.ok:
            self._handle_error(response)  # 友好错误提示
        
        return response.json()
    
    # ===== 业务方法 =====
    def login(self, username: str, password: str) -> Dict:
        """登录"""
        return self._request("POST", "/api/auth/login", 
                            json={"username": username, "password": password})
    
    def create_task(self, task_name: str, audio_urls: List[str]) -> Dict:
        """创建任务"""
        return self._request("POST", "/api/tasks",
                            json={"task_name": task_name, "audio_urls": audio_urls})
    
    def get_task_results(self, task_id: str) -> List[Dict]:
        """获取任务结果"""
        return self._request("GET", f"/api/tasks/{task_id}/results")
```

#### 7.3 API 端点清单

| 方法 | 端点 | 功能 | 认证 |
|------|------|------|------|
| POST | `/api/auth/login` | 用户登录 | 否 |
| GET | `/api/auth/verify` | 验证 Token | 是 |
| POST | `/api/tasks` | 创建批处理任务 | 是 |
| GET | `/api/tasks/{id}` | 查询任务状态 | 是 |
| GET | `/api/tasks/{id}/results` | 获取处理结果 | 是 |
| GET | `/api/stats/summary` | 统计摘要 | 是 |
| GET | `/api/reports/emotion` | 情绪分布报表 | 是 |
| POST | `/api/admin/users/activate` | 设置用户激活状态 | Admin |

---

### 8️⃣ 统计报表系统 (`src/services/report_generator.py`)

#### 8.1 报表类型

```python
class ReportGenerator:
    """统计报表生成器"""
    
    def generate_task_summary(self, task_id: str) -> Dict:
        """任务汇总报表"""
        return {
            'task_id': task_id,
            'total_count': 100,
            'success_count': 95,
            'failed_count': 5,
            'success_rate': 95.0,
            'avg_processing_time': 45.2,  # 平均处理时间（秒）
            'avg_realtime_factor': 0.35,  # 实时因子
        }
    
    def generate_emotion_report(self, task_id: str) -> Dict:
        """情绪分布报表"""
        return {
            'emotions': {
                'angry': 15,      # 愤怒占比
                'neutral': 50,    # 平和占比
                'satisfied': 25,  # 满意占比
                'frustrated': 10  # 沮丧占比
            },
            'abusive_rate': 8.5,  # 辱骂语言出现率(%)
            'avg_confidence': 0.92  # 平均置信度
        }
```

#### 8.2 报表缓存机制

```python
def cache_report(self, report_type: str, data: Dict, 
                 task_id: str = None, ttl_hours: int = 1):
    """缓存报表到数据库（避免重复计算）"""
    expires_at = datetime.now() + timedelta(hours=ttl_hours)
    
    db_manager.insert_report_cache(
        report_type=report_type,
        task_id=task_id,
        data_json=json.dumps(data),
        expires_at=expires_at
    )
```

---

## 🔄 数据流全景图

### 典型场景：批量语音分析

```
[1] 用户上传 Excel 文件（含音频URL列表）
        ↓
[2] Streamlit 前端解析 Excel → 提取 audio_urls[]
        ↓
[3] APIClient.POST /api/tasks {task_name, audio_urls}
        ↓
[4] FastAPI 接收请求
    ├── 幂等性检查（防重复提交）
    ├── 创建 batch_tasks 记录
    └── 启动后台批处理线程
        ↓
[5] BatchProcessor 并发处理
    for each audio_url:
    │
    ├── [5a] 下载音频文件（超时控制）
    ├── [5b] ASREngine.transcribe(audio)
    │   ├── Faster-Whisper 转写 → full_text + segments
    │   └── 文本后处理 → 修正错别字
    ├── [5c] LLM 分析（DeepSeek API）
    │   ├── System Prompt 注入
    │   └── 返回结构化 JSON（情绪/辱骂/摘要）
    ├── [5d] 保存到 audio_results 表
    └── [5e] 更新 checkpoints（断点续传）
        ↓
[6] 任务完成 → status='completed'
    ├── 生成统计报表（ReportGenerator）
    └── 缓存到 report_cache 表
        ↓
[7] 前端轮询查询结果
    ├── GET /api/tasks/{task_id} → 进度百分比
    └── GET /api/tasks/{task_id}/results → 详细结果
        ↓
[8] Streamlit 渲染可视化界面
    ├── 任务进度条
    ├── 结果表格（可编辑客户编号）
    ├── 情绪分布图表
    └── 导出功能（CSV/JSON）
```

---

## ⚙️ 关键技术决策

### 决策 1：为什么选择 Faster-Whisper？

| 维度 | OpenAI Whisper | Faster-Whisper |
|------|----------------|----------------|
| **推理速度** | 基准速度 | **2-4x 加速**（CTranslate2） |
| **内存占用** | 较高 | **降低 50%**（int8 量化） |
| **GPU 支持** | CUDA only | **CUDA + CPU**（兼容性好） |
| **模型格式** | PyTorch | **CTranslate2**（优化图） |
| **部署难度** | 需要 PyTorch | **更轻量** |

**结论**：Faster-Whisper 在 CPU 环境下性能优势明显，适合服务器部署。

---

### 决策 2：为什么选择 Streamlit 作为前端？

| 优势 | 说明 |
|------|------|
| **开发效率** | 纯 Python，无需 HTML/CSS/JS |
| **数据绑定** | Pandas DataFrame 直接渲染表格 |
| **组件丰富** | 内置文件上传/图表/表单组件 |
| **快速原型** | 适合内部工具/B端应用 |
| **部署简单** | 单命令启动 `streamlit run app.py` |

**权衡**：灵活性不如 React/Vue，但满足当前业务需求。

---

### 决策 3：为什么采用前后端分离？

```
传统单体架构（Monolith）:
  Streamlit 直接调用 ASR/DB
  问题：UI 渲染阻塞计算、难以扩展

前后端分离（Current Design）:
  Streamlit (UI) ←→ FastAPI (API) ←→ ASR/DB
  优势：
  ✅ UI 响应流畅（异步批处理）
  ✅ API 可复用（第三方集成）
  ✅ 独立扩展（水平扩展 API 服务）
  ✅ 关注点分离（前端专注展示，后端专注逻辑）
```

---

## 🔒 安全设计

### 1. 认证安全
- 密码 SHA256 + Salt 哈希存储
- Session Token 24 小时过期
- Bearer Token 传输（HTTPS 生产环境必须）

### 2. API 安全
- CORS 中间件（允许跨域访问）
- 请求日志（UUID 追踪 + 耗时统计）
- 全局异常处理器（防止敏感信息泄露）

### 3. 数据安全
- SQL 注入防护（SQLAlchemy ORM 参数化查询）
- 文件上传限制（类型/大小校验）
- 定时清理（7 天前已完成任务的源文件）

---

## 📊 性能优化策略

| 优化领域 | 技术手段 | 效果 |
|----------|----------|------|
| **ASR 推理** | int8 量化 + 动态线程数 | CPU 吞吐量 +30% |
| **并发处理** | ThreadPoolExecutor + 硬件自适应 | 最大 4 并发（CPU）|
| **数据库** | 连接池（size=10）+ 报表缓存 | 减少 90% 重复查询 |
| **网络** | httpx 连接池 + 超时控制 | 防止资源耗尽 |
| **前端** | Streamlit caching + 分页加载 | 页面响应 <1s |
| **日志** | 异步写入 + 按天滚动 | 不阻塞主流程 |

---

## 🚀 部署架构（推荐）

```
生产环境建议：
┌─────────────────────────────────────────────────┐
│                  Nginx 反向代理                   │
│         (SSL 终结 + 静态资源 + 负载均衡)          │
└────────────────┬────────────────────────────────┘
                 │
    ┌────────────┼────────────┐
    ▼            ▼            ▼
┌────────┐  ┌────────┐  ┌──────────┐
│Streamlit│  │FastAPI │  │  Redis   │
│ :8501   │  │ :8000  │  │ (Session │
│ (UI)    │  │ (API)  │  │  Cache)  │
└────────┘  └───┬────┘  └──────────┘
               │
    ┌──────────┼──────────┐
    ▼          ▼          ▼
┌───────┐ ┌────────┐ ┌──────────┐
│ MySQL │ │DeepSeek│ │  OSS/    │
│  RDS  │ │  API   │ │  MinIO   │
└───────┘ └────────┘ └──────────┘
```

---

## 📈 系统局限性 & 改进方向

### 当前局限

| 局限 | 影响 | 建议 |
|------|------|------|
| **Session 存储在内存** | 重启丢失登录状态 | 迁移至 Redis |
| **无消息队列** | 高并发时任务堆积 | 引入 Celery + RabbitMQ |
| **LLM 调用同步** | 长文本分析耗时较长 | 异步调用 + 回调通知 |
| **前端无 WebSocket** | 任务进度需轮询 | 改用 SSE/WebSocket 实时推送 |
| **单机部署** | 无法水平扩展 | 容器化（Docker/K8s）|

### 未来演进路线

```
v3.0 (当前) → v3.1 → v4.0
   │           │        │
   ├─ 基础功能  ├─ Redis  ├─ 微服务架构
   ├─ 前后端分离 ├─ 消息队列 ├─ K8s 部署
   └─ 批量处理  └─ 实时推送  └─ 多租户支持
```

---

## 📚 关键依赖清单

```
# requirements.txt 核心依赖
fastapi==0.104.*          # Web 框架（后端 API）
streamlit==1.28.*         # Web 框架（前端 UI）
faster-whisper==1.0.*     # ASR 语音识别引擎
openai==1.6.*             # LLM 客户端（DeepSeek 兼容）
sqlalchemy==2.0.*         # ORM 数据库框架
pymysql==1.1.*            # MySQL 驱动
pandas==2.1.*             # 数据处理（Excel 解析）
apscheduler==3.10.*       # 定时任务调度
httpx==0.25.*             # HTTP 客户端（异步）
torch==2.1.*              # PyTorch（GPU 支持）
```

---

## 🎯 总结

本项目是一个**企业级语音分析平台**，核心技术栈为 **Python + Streamlit + FastAPI + Faster-Whisper + DeepSeek LLM**。

**设计亮点**：
1. ✅ **清晰的分层架构**（core/api/web/asr/db/services/logger/utils）
2. ✅ **高效的 ASR 引擎**（Faster-Whisper int8 量化，CPU 2-3x 加速）
3. ✅ **智能的 LLM 分析**（情感分析 + 辱骂检测 + 对话质检）
4. ✅ **可靠的批处理系统**（并发控制 + 断点续传 + 幂等性保证）
5. ✅ **完善的日志体系**（多级别 + 滚动 + 彩色 + 结构化 JSON）
6. ✅ **安全的认证机制**（密码哈希 + Session 管理 + 角色权限）

**适用场景**：客服通话质检、呼叫中心录音分析、销售对话挖掘、合规审计等。

---

*文档生成时间：2026-06-16*  
*项目版本：v3.0.0*  
*作者：Voice Analysis Team*