"""
日志清理定时任务
定期清理过期日志文件
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from logger_config import LoggerConfig


def main():
    """主函数 - 清理过期日志"""
    print("=" * 60)
    print("🧹 开始清理过期日志...")
    print("=" * 60)
    
    # 获取日志目录
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
    
    # 执行清理（默认保留30天）
    LoggerConfig.cleanup_old_logs(log_dir=log_dir, retention_days=30)
    
    print("=" * 60)
    print("✅ 日志清理完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
