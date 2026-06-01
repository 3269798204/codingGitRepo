"""
临时兼容层 - 用于前后端分离过渡期
提供db_manager, report_gen等对象的API调用包装
"""

from api_client import APIClient

# 创建全局API客户端实例
_api_client = APIClient(base_url="http://localhost:8000")


class DatabaseManagerCompat:
    """数据库管理器兼容层 - 通过API调用"""
    
    def __init__(self):
        self.api = _api_client
    
    def list_tasks(self, status=None, limit=50):
        """获取任务列表"""
        response = self.api.list_tasks(status=status, limit=limit)
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


class ReportGeneratorCompat:
    """报表生成器兼容层 - 通过API调用"""
    
    def __init__(self):
        self.api = _api_client
    
    def generate_task_summary(self, task_id):
        """生成任务汇总报表"""
        return self.api.get_task_summary(task_id)
    
    def generate_emotion_report(self, task_id):
        """生成情绪分布报表"""
        return self.api.get_emotion_report(task_id)
    
    def generate_performance_report(self, task_id):
        """生成性能监控报表"""
        return self.api.get_performance_report(task_id)


# 创建兼容实例（用于过渡期）
db_manager = DatabaseManagerCompat()
report_gen = ReportGeneratorCompat()
