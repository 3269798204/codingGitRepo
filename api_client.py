"""
API客户端封装
用于前端（Streamlit）调用后端（FastAPI）服务
"""

import requests
from typing import Dict, List, Optional
from urllib.parse import urljoin


class APIClient:
    """API客户端 - 封装所有后端API调用"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        """
        初始化API客户端
        
        Args:
            base_url: 后端API基础地址
        """
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json"
        })
    
    def set_auth_token(self, token: str):
        """
        设置认证token
        
        Args:
            token: JWT或session token
        """
        self.session.headers.update({
            "Authorization": f"Bearer {token}"
        })
    
    def clear_auth_token(self):
        """清除认证token"""
        self.session.headers.pop("Authorization", None)
    
    # ==================== 认证API ====================
    
    def login(self, username: str, password: str) -> Dict:
        """
        用户登录
        
        Args:
            username: 用户名
            password: 密码
        
        Returns:
            dict: {token, username, role}
        """
        response = self.session.post(
            f"{self.base_url}/api/auth/login",
            json={"username": username, "password": password}
        )
        response.raise_for_status()
        return response.json()
    
    def verify_token(self, token: str) -> Dict:
        """
        验证token
        
        Args:
            token: 认证token
        
        Returns:
            dict: {username, role}
        """
        response = self.session.get(
            f"{self.base_url}/api/auth/verify",
            headers={"Authorization": f"Bearer {token}"}
        )
        response.raise_for_status()
        return response.json()
    
    # ==================== 任务管理API ====================
    
    def create_task(self, task_name: str, audio_urls: List[str], 
                   extra_data: Optional[List[Dict]] = None) -> Dict:
        """
        创建批处理任务
        
        Args:
            task_name: 任务名称
            audio_urls: 音频URL列表
            extra_data: 额外数据列表
        
        Returns:
            dict: {success, task_id, message}
        """
        response = self.session.post(
            f"{self.base_url}/api/tasks",
            json={
                "task_name": task_name,
                "audio_urls": audio_urls,
                "extra_data": extra_data
            }
        )
        response.raise_for_status()
        return response.json()
    
    def get_task(self, task_id: str) -> Dict:
        """
        获取任务信息
        
        Args:
            task_id: 任务ID
        
        Returns:
            dict: 任务信息
        """
        response = self.session.get(f"{self.base_url}/api/tasks/{task_id}")
        response.raise_for_status()
        return response.json()
    
    def list_tasks(self, status: Optional[str] = None, limit: int = 50) -> Dict:
        """
        获取任务列表
        
        Args:
            status: 任务状态过滤
            limit: 返回数量限制
        
        Returns:
            dict: {tasks: [...]}
        """
        params = {"limit": limit}
        if status:
            params["status"] = status
        
        response = self.session.get(
            f"{self.base_url}/api/tasks",
            params=params
        )
        response.raise_for_status()
        return response.json()
    
    def get_task_results(self, task_id: str, status: Optional[str] = None, 
                        limit: int = 100) -> Dict:
        """
        获取任务结果
        
        Args:
            task_id: 任务ID
            status: 结果状态过滤
            limit: 返回数量限制
        
        Returns:
            dict: {results: [...]}
        """
        params = {"limit": limit}
        if status:
            params["status"] = status
        
        response = self.session.get(
            f"{self.base_url}/api/tasks/{task_id}/results",
            params=params
        )
        response.raise_for_status()
        return response.json()
    
    # ==================== 文件上传API ====================
    
    def upload_file(self, file_path: str) -> Dict:
        """
        上传文件
        
        Args:
            file_path: 文件路径
        
        Returns:
            dict: {success, file_path, preview}
        """
        with open(file_path, 'rb') as f:
            files = {'file': f}
            response = self.session.post(
                f"{self.base_url}/api/upload",
                files=files
            )
        response.raise_for_status()
        return response.json()
    
    def upload_and_process(self, file_path: str, task_name: str = "批量任务") -> Dict:
        """
        上传文件并立即处理
        
        Args:
            file_path: 文件路径
            task_name: 任务名称
        
        Returns:
            dict: {success, task_id, total_count}
        """
        with open(file_path, 'rb') as f:
            files = {'file': f}
            data = {'task_name': task_name}
            response = self.session.post(
                f"{self.base_url}/api/upload/process",
                files=files,
                data=data
            )
        response.raise_for_status()
        return response.json()
    
    # ==================== 报表API ====================
    
    def get_task_summary(self, task_id: str) -> Dict:
        """获取任务汇总报表"""
        response = self.session.get(
            f"{self.base_url}/api/reports/task_summary/{task_id}"
        )
        response.raise_for_status()
        return response.json()
    
    def get_emotion_report(self, task_id: str) -> Dict:
        """获取情绪分布报表"""
        response = self.session.get(
            f"{self.base_url}/api/reports/emotion/{task_id}"
        )
        response.raise_for_status()
        return response.json()
    
    def get_performance_report(self, task_id: str) -> Dict:
        """获取性能监控报表"""
        response = self.session.get(
            f"{self.base_url}/api/reports/performance/{task_id}"
        )
        response.raise_for_status()
        return response.json()
    
    # ==================== 硬件信息API ====================
    
    def get_hardware_info(self) -> Dict:
        """获取硬件配置信息"""
        response = self.session.get(f"{self.base_url}/api/hardware")
        response.raise_for_status()
        return response.json()
    
    # ==================== 系统配置API ====================
    
    def list_configs(self, category: Optional[str] = None) -> Dict:
        """查询系统配置列表"""
        params = {}
        if category:
            params["category"] = category
        
        response = self.session.get(
            f"{self.base_url}/api/configs",
            params=params
        )
        response.raise_for_status()
        return response.json()
    
    def get_config(self, config_key: str) -> Dict:
        """查询单个配置"""
        response = self.session.get(f"{self.base_url}/api/configs/{config_key}")
        response.raise_for_status()
        return response.json()
    
    def update_config(self, config_key: str, value: str, config_type: str = "string") -> Dict:
        """更新系统配置"""
        response = self.session.put(
            f"{self.base_url}/api/configs/{config_key}",
            params={"value": value, "config_type": config_type}
        )
        response.raise_for_status()
        return response.json()
    
    # ==================== 用户管理API ====================
    
    def list_users(self) -> Dict:
        """查询用户列表"""
        response = self.session.get(f"{self.base_url}/api/users")
        response.raise_for_status()
        return response.json()
    
    def get_user(self, username: str) -> Dict:
        """查询单个用户"""
        response = self.session.get(f"{self.base_url}/api/users/{username}")
        response.raise_for_status()
        return response.json()
    
    def create_user(self, username: str, password: str, role: str = "user", email: str = "") -> Dict:
        """创建用户"""
        response = self.session.post(
            f"{self.base_url}/api/users",
            params={
                "username": username,
                "password": password,
                "role": role,
                "email": email
            }
        )
        response.raise_for_status()
        return response.json()
    
    def update_user(self, username: str, role: Optional[str] = None, is_active: Optional[bool] = None) -> Dict:
        """更新用户信息"""
        params = {}
        if role:
            params["role"] = role
        if is_active is not None:
            params["is_active"] = str(is_active).lower()
        
        response = self.session.put(
            f"{self.base_url}/api/users/{username}",
            params=params
        )
        response.raise_for_status()
        return response.json()
    
    def delete_user(self, username: str) -> Dict:
        """删除用户"""
        response = self.session.delete(f"{self.base_url}/api/users/{username}")
        response.raise_for_status()
        return response.json()
    
    # ==================== 健康检查 ====================
    
    def health_check(self) -> Dict:
        """健康检查"""
        response = self.session.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()
