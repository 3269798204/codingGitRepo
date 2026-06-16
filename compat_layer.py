"""
临时兼容层 - 用于前后端分离过渡期
提供 db_manager 的 API 调用包装
"""

from api_client import APIClient

# 创建全局API客户端实例
_api_client = APIClient(base_url="http://localhost:8000")


class DatabaseManagerCompat:
    """数据库管理器兼容层 - 通过API调用"""
    
    def __init__(self):
        self.api = _api_client
    
    def list_tasks(self, status=None, limit=50, customer_no=None, task_name=None, user_id=None, is_admin=False, current_username=None):
        """获取任务列表"""
        response = self.api.list_tasks(status=status, limit=limit, customer_no=customer_no, task_name=task_name, user_id=user_id, is_admin=is_admin, current_username=current_username)
        return response.get('tasks', [])
    
    def get_task(self, task_id):
        """获取任务信息"""
        return self.api.get_task(task_id)
    
    def get_task_results(self, task_id, status=None, limit=100):
        """获取任务结果"""
        response = self.api.get_task_results(task_id, status=status, limit=limit)
        return response.get('results', [])
    
    def get_task_with_results(self, task_id):
        """获取任务及其所有结果"""
        task = self.api.get_task(task_id)
        results = self.api.get_task_results(task_id)
        task['results'] = results.get('results', [])
        return task


# 创建兼容实例（用于过渡期）
db_manager = DatabaseManagerCompat()
