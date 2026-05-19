"""
硬件检测模块
自动检测 CPU/GPU 配置，推荐最优 ASR 参数
"""

import torch
import multiprocessing
import platform
from typing import Dict, Optional
from dataclasses import dataclass


@dataclass
class HardwareInfo:
    """硬件信息数据类"""
    cpu_cores: int
    cpu_name: str
    gpu_available: bool
    gpu_type: str  # "CUDA", "MPS", "None"
    gpu_name: Optional[str] = None
    gpu_memory_gb: float = 0.0
    system: str = ""
    python_version: str = ""


class HardwareDetector:
    """硬件检测器"""
    
    def __init__(self):
        self._hardware_info: Optional[HardwareInfo] = None
    
    def detect(self) -> HardwareInfo:
        """
        检测硬件配置
        
        Returns:
            HardwareInfo: 硬件信息对象
        """
        if self._hardware_info:
            return self._hardware_info
        
        # CPU 信息
        cpu_cores = multiprocessing.cpu_count()
        cpu_name = self._get_cpu_name()
        
        # GPU 信息
        gpu_available, gpu_type, gpu_name, gpu_memory = self._detect_gpu()
        
        # 系统信息
        system = platform.system()
        python_version = platform.python_version()
        
        self._hardware_info = HardwareInfo(
            cpu_cores=cpu_cores,
            cpu_name=cpu_name,
            gpu_available=gpu_available,
            gpu_type=gpu_type,
            gpu_name=gpu_name,
            gpu_memory_gb=gpu_memory,
            system=system,
            python_version=python_version
        )
        
        return self._hardware_info
    
    def _get_cpu_name(self) -> str:
        """获取 CPU 名称"""
        try:
            if platform.system() == "Darwin":  # macOS
                import subprocess
                result = subprocess.run(
                    ["sysctl", "-n", "machdep.cpu.brand_string"],
                    capture_output=True, text=True, timeout=5
                )
                return result.stdout.strip()
            elif platform.system() == "Linux":
                with open("/proc/cpuinfo", "r") as f:
                    for line in f:
                        if "model name" in line:
                            return line.split(":")[1].strip()
            elif platform.system() == "Windows":
                import os
                return os.environ.get("PROCESSOR_IDENTIFIER", "Unknown CPU")
        except Exception:
            pass
        
        return f"{platform.machine()} ({multiprocessing.cpu_count()} cores)"
    
    def _detect_gpu(self) -> tuple:
        """
        检测 GPU 配置
        
        Returns:
            (available, type, name, memory_gb)
        """
        # 检测 CUDA (NVIDIA GPU)
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            gpu_memory = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            return True, "CUDA", gpu_name, gpu_memory
        
        # 检测 MPS (Apple Silicon)
        if torch.backends.mps.is_available():
            return True, "MPS", "Apple Silicon", 0.0
        
        return False, "None", None, 0.0
    
    def get_recommended_config(self) -> Dict:
        """
        根据硬件配置推荐最优 ASR 参数
        
        Returns:
            dict: 推荐的配置参数
        """
        info = self.detect()
        
        # 默认配置（CPU 模式）
        recommended = {
            "model_size": "small",
            "beam_size": 3,
            "compute_type": "int8",
            "max_workers": 4,
            "vad_filter": True,
            "description": f"默认配置（{info.cpu_cores}核 CPU）"
        }
        
        # NVIDIA GPU 配置
        if info.gpu_type == "CUDA":
            if info.gpu_memory_gb >= 8:
                recommended.update({
                    "model_size": "large",
                    "beam_size": 5,
                    "compute_type": "float16",
                    "max_workers": 1,
                    "description": f"NVIDIA GPU ({info.gpu_name}, {info.gpu_memory_gb:.1f}GB) - 高精度模式"
                })
            elif info.gpu_memory_gb >= 4:
                recommended.update({
                    "model_size": "medium",
                    "beam_size": 5,
                    "compute_type": "float16",
                    "max_workers": 1,
                    "description": f"NVIDIA GPU ({info.gpu_name}, {info.gpu_memory_gb:.1f}GB) - 平衡模式"
                })
            else:
                recommended.update({
                    "model_size": "small",
                    "beam_size": 3,
                    "compute_type": "float16",
                    "max_workers": 1,
                    "description": f"NVIDIA GPU ({info.gpu_name}, {info.gpu_memory_gb:.1f}GB) - 速度模式"
                })
        
        # Apple Silicon 配置
        elif info.gpu_type == "MPS":
            recommended.update({
                "model_size": "medium",
                "beam_size": 3,
                "compute_type": "float16",
                "max_workers": 2,
                "description": "Apple Silicon (MPS) - 平衡模式"
            })
        
        # CPU 模式 - 根据核心数调整
        else:
            if info.cpu_cores >= 16:
                recommended.update({
                    "model_size": "medium",
                    "beam_size": 3,
                    "compute_type": "int8",
                    "max_workers": 4,
                    "description": f"高性能 CPU ({info.cpu_cores}核) - 平衡模式"
                })
            elif info.cpu_cores >= 8:
                recommended.update({
                    "model_size": "small",
                    "beam_size": 3,
                    "compute_type": "int8",
                    "max_workers": 4,
                    "description": f"中端 CPU ({info.cpu_cores}核) - 平衡模式"
                })
            elif info.cpu_cores >= 4:
                recommended.update({
                    "model_size": "base",
                    "beam_size": 3,
                    "compute_type": "int8",
                    "max_workers": 2,
                    "description": f"普通 CPU ({info.cpu_cores}核) - 速度模式"
                })
            else:
                recommended.update({
                    "model_size": "tiny",
                    "beam_size": 1,
                    "compute_type": "int8",
                    "max_workers": 1,
                    "description": f"低配 CPU ({info.cpu_cores}核) - 极速模式"
                })
        
        return recommended
    
    def get_hardware_summary(self) -> str:
        """
        生成硬件信息摘要
        
        Returns:
            str: 格式化的硬件信息
        """
        info = self.detect()
        
        lines = [
            "🖥️  硬件配置信息",
            "=" * 50,
            f"操作系统: {info.system}",
            f"Python: {info.python_version}",
            f"CPU: {info.cpu_name}",
            f"CPU 核心数: {info.cpu_cores}",
        ]
        
        if info.gpu_available:
            lines.append(f"GPU: {info.gpu_type}")
            if info.gpu_name:
                lines.append(f"GPU 型号: {info.gpu_name}")
            if info.gpu_memory_gb > 0:
                lines.append(f"GPU 显存: {info.gpu_memory_gb:.1f} GB")
        else:
            lines.append("GPU: 未检测到")
        
        lines.append("=" * 50)
        
        # 添加推荐配置
        rec = self.get_recommended_config()
        lines.append(f"\n💡 推荐配置:")
        lines.append(f"  模型: {rec['model_size']}")
        lines.append(f"  Beam Size: {rec['beam_size']}")
        lines.append(f"  计算类型: {rec['compute_type']}")
        lines.append(f"  最大并发: {rec['max_workers']}")
        lines.append(f"  说明: {rec['description']}")
        
        return "\n".join(lines)
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        info = self.detect()
        rec = self.get_recommended_config()
        
        return {
            "hardware": {
                "cpu_cores": info.cpu_cores,
                "cpu_name": info.cpu_name,
                "gpu_available": info.gpu_available,
                "gpu_type": info.gpu_type,
                "gpu_name": info.gpu_name,
                "gpu_memory_gb": info.gpu_memory_gb,
                "system": info.system,
                "python_version": info.python_version,
            },
            "recommended": rec
        }


# 全局单例
_detector = None

def get_detector() -> HardwareDetector:
    """获取硬件检测器单例"""
    global _detector
    if _detector is None:
        _detector = HardwareDetector()
    return _detector


if __name__ == "__main__":
    # 测试
    detector = get_detector()
    print(detector.get_hardware_summary())
    print("\n完整配置:")
    import json
    print(json.dumps(detector.to_dict(), indent=2, ensure_ascii=False))
