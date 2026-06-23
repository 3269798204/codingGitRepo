#!/usr/bin/env python3
"""
调试工具 - 快速诊断系统状态
用于排查问题和验证功能
"""

import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))


def print_section(title: str):
    """打印分隔线"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def check_python_version():
    """检查 Python 版本"""
    print_section("🐍 Python 环境")
    
    import sys
    print(f"Python 版本: {sys.version}")
    print(f"Python 路径: {sys.executable}")
    
    if sys.version_info >= (3, 9):
        print("✅ Python 版本符合要求 (>= 3.9)")
        return True
    else:
        print("❌ Python 版本过低，需要 >= 3.9")
        return False


def check_dependencies():
    """检查依赖包"""
    print_section("📦 依赖包检查")
    
    required_packages = {
        'faster_whisper': 'Faster-Whisper',
        'torch': 'PyTorch',
        'streamlit': 'Streamlit',
        'sqlalchemy': 'SQLAlchemy',
        'pymysql': 'PyMySQL',
        'pandas': 'Pandas',
        'openpyxl': 'OpenPyXL',
    }
    
    all_ok = True
    for package, name in required_packages.items():
        try:
            mod = __import__(package.replace('-', '_'))
            version = getattr(mod, '__version__', 'unknown')
            print(f"✅ {name:20s} {version}")
        except ImportError as e:
            print(f"❌ {name:20s} 未安装 - {e}")
            all_ok = False
    
    return all_ok


def check_config():
    """检查配置"""
    print_section("⚙️  配置检查")
    
    try:
        from src.core.config import config
        print(f"✅ 配置加载成功")
        print(f"   数据库主机: {config.database.host}")
        print(f"   数据库端口: {config.database.port}")
        print(f"   数据库名称: {config.database.database}")
        print(f"   ASR 模型: {config.asr.model_size}")
        print(f"   ASR 语言: {config.asr.language}")
        return True
    except Exception as e:
        print(f"❌ 配置加载失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_hardware():
    """检查硬件"""
    print_section("🖥️  硬件检测")
    
    try:
        from src.asr.hardware_detector import get_detector
        detector = get_detector()
        info = detector.to_dict()
        
        hw = info['hardware']
        rec = info['recommended']
        
        print(f"CPU 核心数: {hw['cpu_cores']}")
        print(f"GPU 类型: {hw['gpu_type']}")
        
        if hw.get('gpu_name'):
            print(f"GPU 型号: {hw['gpu_name']}")
        
        if hw.get('gpu_memory_gb', 0) > 0:
            print(f"GPU 显存: {hw['gpu_memory_gb']:.1f} GB")
        
        print(f"\n推荐配置:")
        print(f"  模型: {rec['model_size']}")
        print(f"  Beam Size: {rec['beam_size']}")
        print(f"  计算类型: {rec['compute_type']}")
        print(f"  最大并发: {rec['max_workers']}")
        print(f"  描述: {rec['description']}")
        
        return True
    except Exception as e:
        print(f"❌ 硬件检测失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_database():
    """检查数据库连接"""
    print_section("🗄️  数据库连接")
    
    try:
        from src.db.database import db_manager
        print(f"✅ 数据库管理器初始化成功")
        
        # 测试查询
        tasks = db_manager.list_tasks(limit=1)
        print(f"✅ 数据库查询成功")
        print(f"   当前任务数: {len(tasks)}")
        
        # 检查表是否存在
        from sqlalchemy import inspect
        inspector = inspect(db_manager.engine)
        tables = inspector.get_table_names()
        print(f"✅ 数据表检查成功")
        print(f"   表列表: {', '.join(tables)}")
        
        return True
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_asr_engine():
    """检查 ASR 引擎"""
    print_section("🎙️  ASR 引擎")
    
    try:
        # 只测试导入，不实际加载模型（耗时较长）
        from src.asr.asr_engine import ASREngine
        print(f"✅ ASR 引擎模块导入成功")
        
        # 检查 Faster-Whisper
        from faster_whisper import WhisperModel
        print(f"✅ Faster-Whisper 可用")
        
        print(f"⚠️  模型加载测试已跳过（耗时较长）")
        print(f"   如需测试，请运行: python3 test_model_load.py")
        
        return True
    except Exception as e:
        print(f"❌ ASR 引擎检查失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_csv_parser():
    """检查 CSV 解析器"""
    print_section("📊 CSV 解析器")
    
    try:
        from src.services.csv_parser import CSVParser
        parser = CSVParser()
        print(f"✅ CSV 解析器初始化成功")
        
        # 测试 URL 检测
        import pandas as pd
        df = pd.DataFrame({
            'url': ['http://test.com/1.mp3'],
            'name': ['test']
        })
        
        col = parser.detect_url_column(df)
        if col == 'url':
            print(f"✅ URL 列检测功能正常")
        else:
            print(f"⚠️  URL 列检测结果异常: {col}")
        
        return True
    except Exception as e:
        print(f"❌ CSV 解析器检查失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_batch_processor():
    """检查批处理器"""
    print_section("⚡ 批处理器")
    
    try:
        from src.services.batch_processor import BatchProcessor
        print(f"✅ 批处理器模块导入成功")
        print(f"⚠️  完整初始化测试需要 ASR 引擎正常工作")
        return True
    except Exception as e:
        print(f"❌ 批处理器检查失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_logger():
    """检查日志系统"""
    print_section("📝 日志系统")
    
    try:
        from logger_monitor import get_logger, logger_manager
        
        logger = get_logger()
        logger.info("调试工具 - 日志系统测试")
        
        print(f"✅ 日志系统初始化成功")
        print(f"   日志目录: {logger_manager.log_dir}")
        
        # 检查日志文件
        if logger_manager.log_dir.exists():
            log_files = list(logger_manager.log_dir.glob('*.log'))
            print(f"   日志文件数: {len(log_files)}")
            for lf in log_files[:5]:
                print(f"     - {lf.name}")
        
        return True
    except Exception as e:
        print(f"❌ 日志系统检查失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_streamlit():
    """检查 Streamlit"""
    print_section("🌐 Streamlit Web UI")
    
    try:
        import streamlit as st
        print(f"✅ Streamlit 可用")
        print(f"   版本: {st.__version__}")
        
        # 检查 app.py
        app_file = Path('app.py')
        if app_file.exists():
            print(f"✅ app.py 存在")
            print(f"   大小: {app_file.stat().st_size / 1024:.1f} KB")
        else:
            print(f"❌ app.py 不存在")
            return False
        
        return True
    except Exception as e:
        print(f"❌ Streamlit 检查失败: {e}")
        return False


def generate_report():
    """生成诊断报告"""
    print_section("📋 诊断总结")
    
    checks = [
        ("Python 环境", check_python_version),
        ("依赖包", check_dependencies),
        ("配置", check_config),
        ("硬件检测", check_hardware),
        ("数据库", check_database),
        ("ASR 引擎", check_asr_engine),
        ("CSV 解析器", check_csv_parser),
        ("批处理器", check_batch_processor),
        ("日志系统", check_logger),
        ("Streamlit", check_streamlit),
    ]
    
    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ {name} 检查异常: {e}")
            results.append((name, False))
    
    # 打印总结
    print_section("✅ 检查结果汇总")
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{status:10s} {name}")
    
    print(f"\n总计: {passed}/{total} 项通过")
    
    if passed == total:
        print("\n🎉 所有检查通过！系统状态良好。")
    else:
        print(f"\n⚠️  有 {total - passed} 项检查失败，请查看上方详细信息。")
    
    return passed == total


if __name__ == '__main__':
    print("\n" + "🔧" * 40)
    print("  语音识别分析系统 - 诊断工具 v1.0")
    print("🔧" * 40)
    
    success = generate_report()
    
    print("\n" + "=" * 80)
    if success:
        print("✅ 系统诊断完成 - 一切正常！")
    else:
        print("❌ 系统诊断完成 - 发现问题，请修复后重试")
    print("=" * 80 + "\n")
    
    sys.exit(0 if success else 1)