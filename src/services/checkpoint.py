"""
断点续传管理器
封装数据库的检查点操作，提供简洁接口
"""

from typing import List, Optional
import os, sys
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from src.db.database import db_manager


class CheckpointManager:
    """断点续传管理器"""
    
    def __init__(self):
        self.db = db_manager
    
    def save_checkpoint(self, task_id: str, processed_ids: List[str]):
        """
        保存检查点
        
        Args:
            task_id: 任务 ID
            processed_ids: 已处理的音频 ID 列表
        """
        checkpoint_data = {
            'processed_ids': processed_ids,
            'count': len(processed_ids)
        }
        
        self.db.save_checkpoint(task_id, 'processed_ids', checkpoint_data)
    
    def load_checkpoint(self, task_id: str) -> List[str]:
        """
        加载检查点
        
        Args:
            task_id: 任务 ID
        
        Returns:
            list: 已处理的音频 ID 列表
        """
        checkpoint_data = self.db.load_checkpoint(task_id, 'processed_ids')
        
        if checkpoint_data:
            return checkpoint_data.get('processed_ids', [])
        
        return []
    
    def get_unprocessed(self, task_id: str, all_ids: List[str]) -> List[str]:
        """
        获取未处理的音频 ID
        
        Args:
            task_id: 任务 ID
            all_ids: 所有音频 ID 列表
        
        Returns:
            list: 未处理的音频 ID 列表
        """
        processed_ids = self.load_checkpoint(task_id)
        
        # 转换为集合提高查找效率
        processed_set = set(processed_ids)
        
        unprocessed = [aid for aid in all_ids if aid not in processed_set]
        
        return unprocessed
    
    def clear_checkpoint(self, task_id: str):
        """
        清除检查点
        
        Args:
            task_id: 任务 ID
        """
        self.db.clear_checkpoint(task_id)
    
    def has_checkpoint(self, task_id: str) -> bool:
        """
        检查是否存在检查点
        
        Args:
            task_id: 任务 ID
        
        Returns:
            bool: 是否存在检查点
        """
        checkpoint_data = self.db.load_checkpoint(task_id, 'processed_ids')
        return checkpoint_data is not None
    
    def get_progress_info(self, task_id: str, total_count: int) -> dict:
        """
        获取进度信息
        
        Args:
            task_id: 任务 ID
            total_count: 总数量
        
        Returns:
            dict: 进度信息
        """
        processed_ids = self.load_checkpoint(task_id)
        processed_count = len(processed_ids)
        
        return {
            'total': total_count,
            'processed': processed_count,
            'remaining': total_count - processed_count,
            'progress_percent': (processed_count / total_count * 100) if total_count > 0 else 0
        }


# 全局单例
checkpoint_manager = CheckpointManager()


if __name__ == "__main__":
    # 测试
    print("断点续传管理器初始化成功")
