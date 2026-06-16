"""
语音识别 Web UI 系统 - 配置管理
"""

import os
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path
from urllib.parse import quote_plus

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
        encoded_password = quote_plus(self.password)
        return f"mysql+pymysql://{self.user}:{encoded_password}@{self.host}:{self.port}/{self.database}?charset={self.charset}"

@dataclass
class ASRConfig:
    """ASR 配置"""
    # 模型选择
    model_size: str = "small"  # tiny, base, small, medium, large
    language: str = "zh"
    
    # 设备配置
    device: str = "cpu"  # cpu 或 cuda
    
    # 解码参数
    beam_size: int = 3
    temperature: float = 0.0
    
    # VAD 参数
    vad_filter: bool = True
    min_silence_duration_ms: int = 500
    speech_pad_ms: int = 200
    
    # 其他参数
    condition_on_previous_text: bool = False
    compression_ratio_threshold: float = 2.4
    no_speech_threshold: float = 0.6
    word_timestamps: bool = False
    compute_type: str = "int8"  # int8, float16, float32
    
    # 超时配置（秒）
    timeout: int = 600
    
    # 模型加载超时（秒）
    model_load_timeout: int = 120
    
    # 音频下载超时（秒）
    download_timeout: int = None

@dataclass
class BatchConfig:
    """批处理配置"""
    # 并发控制
    max_cpu_workers: int = 4  # CPU 模式最大并发数
    max_gpu_workers: int = 1  # GPU 模式最大并发数（GPU 本身并行）
    
    # 长音频分段
    chunk_duration: int = 300  # 分段时长（秒）
    enable_chunking: bool = True
    
    # 断点续传
    checkpoint_dir: str = "./checkpoints"
    enable_checkpoint: bool = True
    
    # 缓存
    cache_dir: str = "./cache"
    enable_cache: bool = True

@dataclass
class LogConfig:
    """日志配置"""
    log_dir: str = "./logs"
    log_level: str = "INFO"
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5

@dataclass
class AppConfig:
    """应用总配置"""
    # 应用信息
    app_name: str = "语音识别分析系统"
    version: str = "3.0.0"
    
    # 服务器配置
    host: str = "0.0.0.0"
    port: int = 8501  # Streamlit 默认端口
    api_port: int = 8000  # FastAPI 端口
    
    # 子配置
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    asr: ASRConfig = field(default_factory=ASRConfig)
    batch: BatchConfig = field(default_factory=BatchConfig)
    log: LogConfig = field(default_factory=LogConfig)
    
    # 文件路径
    base_dir: Path = Path(__file__).parent
    upload_dir: Path = field(init=False)
    result_dir: Path = field(init=False)

    #LLM-deepseek-api
    OPENAI_API_KEY = "sk-013fdaa2a69443d193684032b02fc1b4"
    OPENAI_BASE_URL = "https://api.deepseek.com/v1"
    LLM_MODEL = "deepseek-chat"
    LLM_TIMEOUT = 30  # LLM 调用超时（秒）
    
    # LLM System Prompt - 情感分析与对话质检专家
    LLM_SYSTEM_PROMPT = """# 角色设定
你是一个专业的情感分析与对话质检专家。你的任务是对给定的客服-客户对话文本进行分析，并严格按照指定的JSON格式输出结构化数据。

# 输入说明
你将收到一段对话记录，其中包含客服（customer_service）和客户（customer）之间的交替发言。对话内容可能涉及投诉、纠纷或一般咨询。

# 输出要求
只输出一个JSON对象，不要包含任何额外的解释、注释或Markdown标记（除非要求使用代码块）。JSON结构如下：

{
  "dialogue_summary": "一句话总结对话的核心争议或主要内容",
  "has_abusive_language": true/false,
  "abusive_words_list": ["检测到的辱骂词1", "检测到的辱骂词2"]，若无则为[],
  "participants": [
    {
      "role": "customer",
      "emotion_analysis": {
        "primary_emotions": ["主要情绪1", "主要情绪2"],
        "emotion_description": "对该角色情绪的具体描述，包括强度、变化及表达方式",
        "confidence": 0.0~1.0之间的置信度
      },
      "abusive_remarks": true/false,
      "abusive_examples": ["该角色说出的辱骂语句原样摘录"]，若无则为null
    },
    {
      "role": "customer_service",
      "emotion_analysis": {
        "primary_emotions": ["主要情绪1", "主要情绪2"],
        "emotion_description": "对该角色情绪的具体描述",
        "confidence": 0.0~1.0之间的置信度
      },
      "abusive_remarks": true/false,
      "abusive_examples": null或数组
    }
  ],
  "interaction_characteristics": {
    "communication_blocked": true/false,
    "repetitive_pattern": true/false,
    "sarcasm_present": true/false,
    "note": "其他值得注意的交互特征（可选）"
  }
}

# 分析准则
1. **辱骂性词语**：包括但不限于明确脏话（如"他妈的""傻逼""操"）、人身攻击（如"你是白痴吗""你算什么东西"）、严重贬低性称呼。网络流行讽刺词（如"你厉害""呵呵"）若无明确脏话则不算辱骂。
2. **情绪标签**：从以下列表中选取最合适的：anger, frustration, sarcasm, helplessness, defensiveness, resignation, mechanical, impatience, calm, satisfaction, confusion, disappointment 等。
3. **重复模式**：若任何一方连续3次以上重复相同或高度相似的语句，repetitive_pattern 设为 true。
4. **置信度**：根据对话中情绪信号的明确程度（如标点、语气词、重复行为、用词强度）给出0.5~1.0之间的值。

# 示例输入（仅供格式参考，不作为输出）
客服：这边查询到您在4月7日申请时自主勾选了购买会员。
客户：我没有勾选！你们这是恶意扣费。
客服：我们只能取消后续扣费，已经产生的99元不能退。
客户：你就是在推卸责任，太恶心了！

# 示例输出（仅格式示例，不是当前任务的输出）
{"dialogue_summary":"客户否认勾选会员，客服坚持无法退已扣费用","has_abusive_language":false,"abusive_words_list":[],...}

# 现在，请对以下对话进行分析（请将待分析的对话文本粘贴在此处）"""

    def __post_init__(self):
        self.upload_dir = self.base_dir / "uploads"
        self.result_dir = self.base_dir / "results"
        
        # 创建必要的目录
        for dir_path in [self.upload_dir, self.result_dir, 
                        Path(self.batch.checkpoint_dir),
                        Path(self.batch.cache_dir),
                        Path(self.log.log_dir)]:
            dir_path.mkdir(parents=True, exist_ok=True)

# 全局配置实例
config = AppConfig()

def get_hardware_optimized_config() -> dict:
    """
    根据硬件配置返回最优的 ASR 参数
    
    Returns:
        dict: 推荐的配置参数
    """
    import torch
    
    recommended = {
        "model_size": "small",
        "beam_size": 3,
        "compute_type": "int8",
        "max_workers": 4,
        "description": "默认配置（CPU 模式）"
    }
    
    # 检测 CUDA (NVIDIA GPU)
    if torch.cuda.is_available():
        gpu_name = torch.cuda.get_device_name(0)
        gpu_memory = torch.cuda.get_device_properties(0).total_memory / (1024**3)
        
        if gpu_memory >= 8:
            recommended.update({
                "model_size": "large",
                "beam_size": 5,
                "compute_type": "float16",
                "max_workers": 1,
                "description": f"NVIDIA GPU ({gpu_name}, {gpu_memory:.1f}GB) - 高精度模式"
            })
        elif gpu_memory >= 4:
            recommended.update({
                "model_size": "medium",
                "beam_size": 5,
                "compute_type": "float16",
                "max_workers": 1,
                "description": f"NVIDIA GPU ({gpu_name}, {gpu_memory:.1f}GB) - 平衡模式"
            })
        else:
            recommended.update({
                "model_size": "small",
                "beam_size": 3,
                "compute_type": "float16",
                "max_workers": 1,
                "description": f"NVIDIA GPU ({gpu_name}, {gpu_memory:.1f}GB) - 速度模式"
            })
    
    # 检测 MPS (Apple Silicon)
    elif torch.backends.mps.is_available():
        recommended.update({
            "model_size": "medium",
            "beam_size": 3,
            "compute_type": "float16",
            "max_workers": 2,
            "description": "Apple Silicon (MPS) - 平衡模式"
        })
    
    # CPU 模式 - 根据核心数调整
    else:
        import multiprocessing
        cpu_count = multiprocessing.cpu_count()
        
        if cpu_count >= 8:
            recommended.update({
                "model_size": "small",
                "beam_size": 3,
                "compute_type": "int8",
                "max_workers": 4,
                "description": f"高性能 CPU ({cpu_count}核) - 平衡模式"
            })
        elif cpu_count >= 4:
            recommended.update({
                "model_size": "base",
                "beam_size": 3,
                "compute_type": "int8",
                "max_workers": 2,
                "description": f"普通 CPU ({cpu_count}核) - 速度模式"
            })
        else:
            recommended.update({
                "model_size": "tiny",
                "beam_size": 1,
                "compute_type": "int8",
                "max_workers": 1,
                "description": f"低配 CPU ({cpu_count}核) - 极速模式"
            })
    
    return recommended
