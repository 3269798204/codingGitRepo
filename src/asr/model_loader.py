"""
模型加载器模块
实现单例模式的Whisper模型预加载和管理
"""

import os
import threading
from typing import Optional
from faster_whisper import WhisperModel

import os, sys
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from src.core.config import config


class ModelLoader:
    """模型加载器（单例模式）
    
    负责在应用启动时预加载Whisper模型，确保全局唯一实例
    """
    
    _instance = None
    _lock = threading.Lock()
    _model = None
    _is_loaded = False
    _model_size = None
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        # 防止重复初始化
        if hasattr(self, '_initialized'):
            return
        self._initialized = True
    
    def load_model(self, model_size: str = None, device: str = None, 
                   compute_type: str = None) -> WhisperModel:
        """
        加载或获取已加载的模型
        
        Args:
            model_size: 模型大小 (tiny/base/small/medium/large)
            device: 设备类型 (cpu/cuda)
            compute_type: 计算类型 (int8/float16/float32)
        
        Returns:
            WhisperModel: 加载的模型实例
        """
        if self._is_loaded and self._model_size == model_size:
            print(f"✅ 模型已加载: {self._model_size}")
            return self._model
        
        with self._lock:
            # 双重检查锁定
            if self._is_loaded and self._model_size == model_size:
                return self._model
            
            model_size = model_size or config.asr.model_size
            device = device or config.asr.device
            compute_type = compute_type or config.asr.compute_type
            
            print(f"🚀 正在加载 Whisper 模型: {model_size}")
            print(f"   设备: {device}")
            print(f"   计算类型: {compute_type}")
            
            try:
                # Faster-Whisper会自动处理模型下载
                self._model = WhisperModel(
                    model_size,
                    device=device,
                    compute_type=compute_type,
                    cpu_threads=8,
                    num_workers=2
                )
                
                self._model_size = model_size
                self._is_loaded = True
                
                print(f"✅ 模型加载成功: {model_size}")
                return self._model
                
            except Exception as e:
                print(f"❌ 模型加载失败: {e}")
                raise e
    
    def get_model(self) -> Optional[WhisperModel]:
        """获取当前加载的模型"""
        return self._model
    
    def is_loaded(self) -> bool:
        """检查模型是否已加载"""
        return self._is_loaded
    
    def get_model_size(self) -> Optional[str]:
        """获取当前加载的模型大小"""
        return self._model_size
    
    def reload_model(self, model_size: str = None) -> WhisperModel:
        """
        重新加载模型（用于切换模型大小）
        
        Args:
            model_size: 新的模型大小
        
        Returns:
            WhisperModel: 新加载的模型实例
        """
        self._is_loaded = False
        self._model = None
        return self.load_model(model_size)


# 全局模型加载器实例
model_loader = ModelLoader()


def init_model_on_startup(model_size: str = None):
    """
    应用启动时初始化模型
    
    Args:
        model_size: 模型大小，默认使用配置文件中的值
    """
    try:
        print("=" * 60)
        print("🎯 开始预加载 Whisper 模型...")
        print("=" * 60)
        
        model = model_loader.load_model(model_size)
        
        print("=" * 60)
        print("✅ 模型预加载完成！")
        print("=" * 60)
        
        return model
        
    except Exception as e:
        print("=" * 60)
        print(f"❌ 模型预加载失败: {e}")
        print("=" * 60)
        raise e


if __name__ == "__main__":
    # 测试
    print("测试模型加载器...")
    loader = ModelLoader()
    print(f"模型加载器实例: {loader}")
    print(f"单例测试: {loader is ModelLoader()}")
