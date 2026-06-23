#!/usr/bin/env python3
"""
测试脚本 - 单个音频分析
用于调试和验证 app.py 的单个音频处理功能
"""

import sys
import os
import time
from datetime import datetime

# 添加项目路径
sys.path.insert(0, '/Users/ylm/IdeaProjects/voice-analysis-web')

from src.core.config import config
from src.db.database import db_manager
from src.services.batch_processor import BatchProcessor
from src.asr.hardware_detector import get_detector


def test_single_audio(audio_url: str = None):
    """
    测试单个音频分析
    
    Args:
        audio_url: 音频 URL，如果未提供则使用默认测试 URL
    """
    
    print("=" * 80)
    print("🧪 单个音频分析测试")
    print("=" * 80)
    
    # 1. 显示硬件信息
    print("\n📋 步骤 1: 检测硬件配置")
    detector = get_detector()
    hw_info = detector.to_dict()
    
    print(f"   CPU 核心数: {hw_info['hardware']['cpu_cores']}")
    print(f"   GPU 类型: {hw_info['hardware']['gpu_type']}")
    
    if hw_info['hardware'].get('gpu_name'):
        print(f"   GPU 型号: {hw_info['hardware']['gpu_name']}")
    
    if hw_info['hardware'].get('gpu_memory_gb', 0) > 0:
        print(f"   GPU 显存: {hw_info['hardware']['gpu_memory_gb']:.1f} GB")
    
    rec = hw_info['recommended']
    print(f"\n   💡 推荐配置:")
    print(f"      模型: {rec['model_size']}")
    print(f"      Beam Size: {rec['beam_size']}")
    print(f"      并发数: {rec['max_workers']}")
    print(f"      描述: {rec['description']}")
    
    # 2. 初始化批处理器
    print("\n📋 步骤 2: 初始化批处理器")
    try:
        batch_processor = BatchProcessor()
        print("   ✅ 批处理器初始化成功")
    except Exception as e:
        print(f"   ❌ 批处理器初始化失败: {e}")
        return False
    
    # 3. 准备测试音频
    if not audio_url:
        # 使用一个公开的测试音频 URL（中文语音）
        audio_url = "https://github.com/SYSTRAN/faster-whisper/raw/master/test_data/audio.mp3"
        print(f"\n📋 步骤 3: 使用默认测试音频")
        print(f"   URL: {audio_url}")
    else:
        print(f"\n📋 步骤 3: 使用指定测试音频")
        print(f"   URL: {audio_url}")
    
    # 4. 执行分析
    print("\n📋 步骤 4: 开始分析...")
    start_time = time.time()
    
    try:
        # 创建任务
        task_name = f"测试-单个音频-{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        def progress_callback(task_id, progress, message):
            print(f"   📊 进度: {progress:.1f}% - {message}")
        
        task_id = batch_processor.start_batch(
            task_name=task_name,
            audio_urls=[audio_url],
            progress_callback=progress_callback
        )
        
        elapsed = time.time() - start_time
        print(f"\n   ✅ 分析完成！")
        print(f"   任务 ID: {task_id}")
        print(f"   耗时: {elapsed:.2f} 秒")
        
    except Exception as e:
        print(f"\n   ❌ 分析失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 5. 查询结果
    print("\n📋 步骤 5: 查询分析结果")
    try:
        results = db_manager.get_task_results(task_id)
        
        if not results:
            print("   ❌ 未找到分析结果")
            return False
        
        result = results[0]
        
        print(f"   ✅ 找到 {len(results)} 条结果")
        print(f"\n   📝 识别结果:")
        print(f"   {'-' * 76}")
        
        # 显示完整文本
        full_text = result.get('full_text', '')
        if full_text:
            # 分段显示，每行最多 80 字符
            words = full_text.split()
            line = ""
            for i, word in enumerate(words):
                if len(line) + len(word) + 1 > 80:
                    print(f"   {line}")
                    line = word
                else:
                    line = line + " " + word if line else word
            if line:
                print(f"   {line}")
        else:
            print("   (无文本)")
        
        print(f"   {'-' * 76}")
        
        # 显示统计信息
        print(f"\n   📊 统计信息:")
        print(f"      音频时长: {result.get('duration', 0):.2f} 秒")
        print(f"      处理时间: {result.get('processing_time', 0):.2f} 秒")
        print(f"      ASR 时间: {result.get('asr_time', 0):.2f} 秒")
        print(f"      实时因子: {result.get('realtime_factor', 0):.2f}x")
        print(f"      语言: {result.get('language', 'unknown')}")
        print(f"      置信度: {result.get('confidence', 0):.2%}")
        
        # 显示 LLM 分析结果（如果有）
        if result.get('dialogue_summary'):
            print(f"\n   🤖 LLM 分析:")
            print(f"      摘要: {result['dialogue_summary'][:200]}...")
            
            if result.get('has_abusive_language'):
                print(f"      ⚠️  检测到辱骂语言")
                if result.get('abusive_words_json'):
                    print(f"      辱骂词: {result['abusive_words_json']}")
            else:
                print(f"      ✅ 未检测到辱骂语言")
        
        # 显示任务状态
        task_info = db_manager.get_task_by_id(task_id)
        if task_info:
            print(f"\n   📋 任务状态:")
            print(f"      状态: {task_info['status']}")
            print(f"      总数: {task_info['total_count']}")
            print(f"      成功: {task_info['success_count']}")
            print(f"      失败: {task_info['failed_count']}")
            print(f"      进度: {task_info['progress']:.1f}%")
        
        return True
        
    except Exception as e:
        print(f"   ❌ 查询结果失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_with_local_file(file_path: str):
    """
    测试本地音频文件
    
    Args:
        file_path: 本地音频文件路径
    """
    if not os.path.exists(file_path):
        print(f"❌ 文件不存在: {file_path}")
        return False
    
    print(f"📁 测试本地文件: {file_path}")
    print(f"   文件大小: {os.path.getsize(file_path) / 1024 / 1024:.2f} MB")
    
    return test_single_audio(file_path)


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='测试单个音频分析功能')
    parser.add_argument('--url', type=str, help='音频 URL')
    parser.add_argument('--file', type=str, help='本地音频文件路径')
    
    args = parser.parse_args()
    
    if args.file:
        # 测试本地文件
        success = test_with_local_file(args.file)
    elif args.url:
        # 测试指定 URL
        success = test_single_audio(args.url)
    else:
        # 使用默认测试 URL
        success = test_single_audio()
    
    print("\n" + "=" * 80)
    if success:
        print("✅ 测试通过！")
    else:
        print("❌ 测试失败！")
    print("=" * 80)
    
    sys.exit(0 if success else 1)
