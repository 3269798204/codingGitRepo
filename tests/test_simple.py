#!/usr/bin/env python3
"""
简化测试脚本 - 直接测试 ASR 引擎
不依赖完整的 Web UI 架构
"""

import sys
import os
import time

sys.path.insert(0, '/Users/ylm/IdeaProjects/voice-analysis-web')

def test_asr_basic():
    """基础 ASR 测试"""
    print("=" * 80)
    print("🧪 基础 ASR 功能测试")
    print("=" * 80)
    
    # 1. 测试配置加载
    print("\n📋 步骤 1: 测试配置加载")
    try:
        from config import config
        print(f"   ✅ 配置加载成功")
        print(f"      模型: {config.asr.model_size}")
        print(f"      语言: {config.asr.language}")
        print(f"      Beam Size: {config.asr.beam_size}")
    except Exception as e:
        print(f"   ❌ 配置加载失败: {e}")
        return False
    
    # 2. 测试硬件检测
    print("\n📋 步骤 2: 测试硬件检测")
    try:
        from hardware_detector import get_detector
        detector = get_detector()
        hw_info = detector.to_dict()
        
        print(f"   ✅ 硬件检测成功")
        print(f"      CPU: {hw_info['hardware']['cpu_cores']} 核")
        print(f"      GPU: {hw_info['hardware']['gpu_type']}")
        
        rec = hw_info['recommended']
        print(f"      推荐模型: {rec['model_size']}")
        print(f"      推荐配置: {rec['description']}")
    except Exception as e:
        print(f"   ❌ 硬件检测失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 3. 测试数据库连接
    print("\n📋 步骤 3: 测试数据库连接")
    try:
        from database import db_manager
        print(f"   ✅ 数据库连接成功")
        
        # 尝试查询
        tasks = db_manager.list_tasks(limit=1)
        print(f"      当前任务数: {len(tasks)}")
    except Exception as e:
        print(f"   ❌ 数据库连接失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 4. 测试 Faster-Whisper 导入
    print("\n📋 步骤 4: 测试 Faster-Whisper")
    try:
        from faster_whisper import WhisperModel
        print(f"   ✅ Faster-Whisper 导入成功")
    except Exception as e:
        print(f"   ❌ Faster-Whisper 导入失败: {e}")
        return False
    
    # 5. 测试模型加载（可选，耗时较长）
    print("\n📋 步骤 5: 测试模型加载（跳过，需要手动确认）")
    print(f"   ⚠️  如需测试模型加载，请运行:")
    print(f"      python3 test_model_load.py")
    
    return True


def test_csv_parser():
    """测试 CSV 解析器"""
    print("\n" + "=" * 80)
    print("🧪 CSV 解析器测试")
    print("=" * 80)
    
    try:
        from csv_parser import CSVParser
        parser = CSVParser()
        print(f"   ✅ CSV 解析器初始化成功")
        return True
    except Exception as e:
        print(f"   ❌ CSV 解析器初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    print("\n开始测试...\n")
    
    success1 = test_asr_basic()
    success2 = test_csv_parser()
    
    print("\n" + "=" * 80)
    if success1 and success2:
        print("✅ 所有测试通过！")
        print("\n下一步:")
        print("  1. 重启 Streamlit: python3 -m streamlit run app.py")
        print("  2. 访问 http://localhost:8502")
    else:
        print("❌ 部分测试失败")
    print("=" * 80)
