"""
动态配置管理器
优先从数据库读取配置，如果数据库中没有则使用默认值
"""

from typing import Any, Optional
import os, sys
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from src.core.config import config, ASRConfig, BatchConfig
from src.db.database import db_manager


class DynamicConfigManager:
    """动态配置管理器
    
    优先级：
    1. 数据库配置（system_configs表）
    2. 配置文件默认值（config.py）
    """
    
    def __init__(self):
        self._cache = {}  # 配置缓存，避免频繁查询数据库
    
    def get_asr_config(self) -> ASRConfig:
        """
        获取ASR配置（优先从数据库读取）
        
        Returns:
            ASRConfig: ASR配置对象
        """
        # 创建基础配置
        asr_config = ASRConfig()
        
        # 从数据库覆盖配置
        db_model_size = db_manager.get_config('asr.model_size')
        if db_model_size:
            asr_config.model_size = db_model_size
        
        db_device = db_manager.get_config('asr.device')
        if db_device:
            asr_config.device = db_device
        
        db_compute_type = db_manager.get_config('asr.compute_type')
        if db_compute_type:
            asr_config.compute_type = db_compute_type
        
        db_beam_size = db_manager.get_config('asr.beam_size')
        if db_beam_size is not None:
            asr_config.beam_size = int(db_beam_size)
        
        db_language = db_manager.get_config('asr.language')
        if db_language:
            asr_config.language = db_language
        
        db_vad_filter = db_manager.get_config('asr.vad_filter')
        if db_vad_filter is not None:
            asr_config.vad_filter = self._to_bool(db_vad_filter)
        
        print(f"📋 ASR配置加载:")
        print(f"   model_size: {asr_config.model_size}")
        print(f"   device: {asr_config.device}")
        print(f"   compute_type: {asr_config.compute_type}")
        print(f"   beam_size: {asr_config.beam_size}")
        
        return asr_config
    
    def get_batch_config(self) -> BatchConfig:
        """
        获取批处理配置（优先从数据库读取）
        
        Returns:
            BatchConfig: 批处理配置对象
        """
        batch_config = BatchConfig()
        
        # 从数据库覆盖配置
        db_max_workers = db_manager.get_config('batch.max_workers')
        if db_max_workers is not None:
            # 根据是否有GPU决定设置哪个参数
            if config.asr.device == 'cuda':
                batch_config.max_gpu_workers = int(db_max_workers)
            else:
                batch_config.max_cpu_workers = int(db_max_workers)
        
        db_chunk_duration = db_manager.get_config('batch.chunk_duration')
        if db_chunk_duration is not None:
            batch_config.chunk_duration = int(db_chunk_duration)
        
        return batch_config
    
    def get_config_value(self, key: str, default: Any = None) -> Any:
        """
        获取单个配置值（带缓存）
        
        Args:
            key: 配置键
            default: 默认值
        
        Returns:
            配置值
        """
        # 检查缓存
        if key in self._cache:
            return self._cache[key]
        
        # 从数据库读取
        value = db_manager.get_config(key, default)
        
        # 写入缓存
        self._cache[key] = value
        
        return value
    
    def refresh_cache(self):
        """刷新配置缓存"""
        self._cache.clear()
        print("✅ 配置缓存已刷新")
    
    @staticmethod
    def _to_bool(value) -> bool:
        """转换为布尔值"""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ('true', '1', 'yes')
        return bool(value)


# 全局配置管理器实例
dynamic_config = DynamicConfigManager()


def get_dynamic_asr_config() -> ASRConfig:
    """获取动态ASR配置（便捷函数）"""
    return dynamic_config.get_asr_config()


def get_dynamic_batch_config() -> BatchConfig:
    """获取动态批处理配置（便捷函数）"""
    return dynamic_config.get_batch_config()


if __name__ == "__main__":
    # 测试
    print("=" * 60)
    print("测试动态配置管理器")
    print("=" * 60)
    
    # 测试ASR配置
    print("\n1. 测试ASR配置:")
    asr_config = get_dynamic_asr_config()
    print(f"   model_size: {asr_config.model_size}")
    print(f"   device: {asr_config.device}")
    print(f"   compute_type: {asr_config.compute_type}")
    
    # 测试批处理配置
    print("\n2. 测试批处理配置:")
    batch_config = get_dynamic_batch_config()
    print(f"   max_cpu_workers: {batch_config.max_cpu_workers}")
    print(f"   chunk_duration: {batch_config.chunk_duration}")
    
    print("\n✅ 测试完成")
