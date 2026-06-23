# ASRConfig device属性修复说明

## 🔍 问题分析

### 错误信息
```
AttributeError: 'ASRConfig' object has no attribute 'device'
```

### 根本原因
`ASRConfig`配置类中缺少`device`属性定义，但`model_loader.py`中尝试访问该属性。

**问题代码位置**:
- **文件**: `model_loader.py` 第62行
- **代码**: `device = device or config.asr.device`

---

## ✅ 修复方案

### 修改的文件

#### [config.py](file:///Users/ylm/IdeaProjects/voice-analysis-web/config.py)

在`ASRConfig`类中添加`device`属性：

**修改前**:
```python
@dataclass
class ASRConfig:
    """ASR 配置"""
    # 模型选择
    model_size: str = "small"
    language: str = "zh"
    
    # 解码参数
    beam_size: int = 3
    ...
```

**修改后**:
```python
@dataclass
class ASRConfig:
    """ASR 配置"""
    # 模型选择
    model_size: str = "small"
    language: str = "zh"
    
    # 设备配置
    device: str = "cpu"  # cpu 或 cuda
    
    # 解码参数
    beam_size: int = 3
    ...
```

---

## 📋 配置说明

### device属性

**类型**: `str`  
**默认值**: `"cpu"`  
**可选值**: 
- `"cpu"` - 使用CPU进行推理（默认）
- `"cuda"` - 使用NVIDIA GPU进行推理

### 其他相关配置

```python
@dataclass
class ASRConfig:
    # 设备配置
    device: str = "cpu"
    
    # 计算类型（与device配合使用）
    compute_type: str = "int8"  # int8, float16, float32
    
    # 模型大小
    model_size: str = "small"  # tiny, base, small, medium, large
```

---

## 🎯 使用场景

### 1. CPU模式（默认）

适合没有GPU或内存有限的场景：

```python
# config.py
device: str = "cpu"
compute_type: str = "int8"  # CPU推荐使用int8
```

### 2. GPU模式

适合有NVIDIA GPU的场景，速度更快：

```python
# config.py
device: str = "cuda"
compute_type: str = "float16"  # GPU推荐使用float16
```

### 3. 动态切换

在代码中动态指定设备：

```python
from model_loader import model_loader

# 使用CPU
model = model_loader.load_model(device="cpu", compute_type="int8")

# 使用GPU
model = model_loader.load_model(device="cuda", compute_type="float16")
```

---

## 🔧 硬件检测自动配置

系统提供了硬件检测功能，可以自动选择最优配置：

```python
from config import get_hardware_optimized_config

# 获取推荐的配置
recommended = get_hardware_optimized_config()
print(f"推荐设备: {recommended['device']}")
print(f"推荐计算类型: {recommended['compute_type']}")
print(f"推荐模型大小: {recommended['model_size']}")
```

---

## 📊 性能对比

| 配置 | 速度 | 内存占用 | 适用场景 |
|------|------|----------|----------|
| CPU + int8 | 慢 | 低 | 无GPU、低配机器 |
| CPU + float32 | 最慢 | 高 | 需要高精度 |
| CUDA + float16 | 快 | 中等 | 有GPU、平衡性能 |
| CUDA + float32 | 最快 | 高 | 有GPU、追求极致速度 |

---

## ⚙️ 配置示例

### 示例1: 开发环境（CPU）

```python
@dataclass
class ASRConfig:
    device: str = "cpu"
    compute_type: str = "int8"
    model_size: str = "base"  # 小模型，快速测试
```

### 示例2: 生产环境（GPU）

```python
@dataclass
class ASRConfig:
    device: str = "cuda"
    compute_type: str = "float16"
    model_size: str = "small"  # 平衡精度和速度
```

### 示例3: 高精度需求

```python
@dataclass
class ASRConfig:
    device: str = "cuda"
    compute_type: str = "float32"
    model_size: str = "large"  # 最大模型，最高精度
```

---

## 🧪 验证修复

### 方法1: Python命令行

```bash
python3 -c "
from config import config
print(f'device: {config.asr.device}')
print(f'compute_type: {config.asr.compute_type}')
"
```

**预期输出**:
```
device: cpu
compute_type: int8
```

### 方法2: 测试ModelLoader

```bash
python3 -c "
from model_loader import ModelLoader
from config import config

loader = ModelLoader()
print(f'ModelLoader初始化成功')
print(f'配置device: {config.asr.device}')
"
```

**预期输出**:
```
ModelLoader初始化成功
配置device: cpu
```

---

## 🔗 相关代码

### model_loader.py 中的使用

```python
def load_model(self, model_size: str = None, device: str = None, 
               compute_type: str = None) -> WhisperModel:
    """加载或获取已加载的模型"""
    
    # 从配置中获取默认值
    model_size = model_size or config.asr.model_size
    device = device or config.asr.device  # ✅ 现在可以正常访问
    compute_type = compute_type or config.asr.compute_type
    
    # 加载模型
    self._model = WhisperModel(
        model_size,
        device=device,
        compute_type=compute_type,
        cpu_threads=8,
        num_workers=2
    )
    
    return self._model
```

---

## ❓ 常见问题

### Q1: 如何检查是否有GPU？

A: 运行以下命令：
```bash
python3 -c "import torch; print('CUDA可用:', torch.cuda.is_available())"
```

### Q2: GPU模式下报错怎么办？

A: 确保已安装CUDA和正确的驱动：
```bash
nvidia-smi  # 检查GPU状态
```

### Q3: 如何切换设备？

A: 修改`config.py`中的`device`值，或使用参数覆盖：
```python
model = model_loader.load_model(device="cuda")
```

### Q4: int8和float16有什么区别？

A: 
- **int8**: 量化模型，速度快，内存占用少，精度略降
- **float16**: 半精度浮点，速度快，精度接近float32

---

## 📝 最佳实践

### 1. 根据硬件选择配置

```python
# 检测硬件并自动配置
import torch

if torch.cuda.is_available():
    device = "cuda"
    compute_type = "float16"
else:
    device = "cpu"
    compute_type = "int8"
```

### 2. 开发时使用小模型

```python
# 开发阶段
model_size = "tiny"  # 快速迭代

# 生产阶段
model_size = "small"  # 平衡性能
```

### 3. 监控资源使用

```bash
# CPU模式
htop  # 监控CPU和内存

# GPU模式
nvidia-smi  # 监控GPU使用
```

---

## 🔗 相关文档

- [config.py](file:///Users/ylm/IdeaProjects/voice-analysis-web/config.py) - 配置文件
- [model_loader.py](file:///Users/ylm/IdeaProjects/voice-analysis-web/model_loader.py) - 模型加载器
- [asr_engine.py](file:///Users/ylm/IdeaProjects/voice-analysis-web/asr_engine.py) - ASR引擎

---

**最后更新**: 2026-05-19  
**版本**: v1.0  
**状态**: ✅ 已修复
