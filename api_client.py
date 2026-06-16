"""
API客户端封装
用于前端（Streamlit）调用后端（FastAPI）服务
"""

import os
import requests
from typing import Dict, List, Optional
from urllib.parse import urljoin


class APIError(Exception):
    """API错误异常类"""
    def __init__(self, message: str, status_code: int = None, response: Dict = None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response


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
    
    def _handle_error(self, response: requests.Response) -> None:
        """
        处理API错误响应
        
        Args:
            response: HTTP响应对象
            
        Raises:
            APIError: 包含状态码和错误信息的异常
        """
        try:
            error_data = response.json()
            error_msg = error_data.get('detail', str(error_data))
        except:
            error_msg = response.text or f"HTTP {response.status_code}"
        
        # 根据状态码提供更友好的错误信息
        status_messages = {
            400: "请求参数错误",
            401: "未授权访问，请重新登录",
            403: "权限不足",
            404: "资源不存在",
            422: "请求参数验证失败",
            429: "请求过于频繁，请稍后再试",
            500: "服务器内部错误",
            502: "网关错误",
            503: "服务暂时不可用",
            504: "网关超时"
        }
        
        friendly_msg = status_messages.get(response.status_code, f"HTTP {response.status_code}")
        full_message = f"{friendly_msg}: {error_msg}"
        
        raise APIError(full_message, response.status_code, error_data)
    
    def _request(self, method: str, endpoint: str, **kwargs) -> Dict:
        """
        通用请求方法
        
        Args:
            method: HTTP方法
            endpoint: API端点
            **kwargs: 请求参数
            
        Returns:
            Dict: 响应数据
            
        Raises:
            APIError: API错误
        """
        url = urljoin(f"{self.base_url}/", endpoint.lstrip('/'))
        response = self.session.request(method, url, **kwargs)
        
        if not response.ok:
            self._handle_error(response)
        
        try:
            return response.json()
        except:
            return {"data": response.text}
    
    # ==================== 认证API ====================
    
    def login(self, username: str, password: str) -> Dict:
        """
        用户登录
        
        Args:
            username: 用户名
            password: 密码
        
        Returns:
            dict: {token, username, role}
            
        Raises:
            APIError: 登录失败
        """
        return self._request('POST', '/api/auth/login', json={
            "username": username, 
            "password": password
        })
    
    def set_user_active(self, username: str, is_active: bool) -> Dict:
        """
        设置用户激活状态
        
        Args:
            username: 用户名
            is_active: 是否激活
        
        Returns:
            dict: {success, message}
            
        Raises:
            APIError: 设置失败
        """
        return self._request('POST', '/api/admin/users/activate', json={
            'username': username,
            'is_active': is_active
        })
    
    def verify_token(self, token: str) -> Dict:
        """
        验证token
        
        Args:
            token: 认证token
        
        Returns:
            dict: {username, role}
            
        Raises:
            APIError: token验证失败
        """
        headers = {"Authorization": f"Bearer {token}"}
        return self._request('GET', '/api/auth/verify', headers=headers)
    
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
            
        Raises:
            APIError: 任务创建失败
        """
        return self._request('POST', '/api/tasks', json={
            "task_name": task_name,
            "audio_urls": audio_urls,
            "extra_data": extra_data
        })
    
    def get_task(self, task_id: str) -> Dict:
        """
        获取任务信息
        
        Args:
            task_id: 任务ID
        
        Returns:
            dict: 任务信息
            
        Raises:
            APIError: 任务获取失败
        """
        return self._request('GET', f'/api/tasks/{task_id}')
    
    def continue_task(self, task_id: str) -> Dict:
        """
        继续执行未完成的任务
        
        Args:
            task_id: 任务ID
        
        Returns:
            dict: {success, task_id, message}
            
        Raises:
            APIError: 继续任务失败
        """
        return self._request('POST', f'/api/tasks/{task_id}/continue')
    
    def list_tasks(self, status: Optional[str] = None, limit: int = 50, 
                   customer_no: Optional[str] = None, task_name: Optional[str] = None, user_id: Optional[str] = None,
                   is_admin: Optional[bool] = False, current_username: Optional[str] = None) -> Dict:
        """
        获取任务列表
        
        Args:
            status: 任务状态过滤
            limit: 返回数量限制
            customer_no: 客户编码过滤
            task_name: 任务名称过滤
            user_id: 用户编号过滤
            is_admin: 当前用户是否为管理员
            current_username: 当前用户名
        
        Returns:
            dict: {tasks: [...]}
            
        Raises:
            APIError: 任务列表获取失败
        """
        params = {"limit": limit}
        if status:
            params["status"] = status
        if customer_no:
            params["customer_no"] = customer_no
        if task_name:
            params["task_name"] = task_name
        if user_id:
            params["user_id"] = user_id
        if is_admin is not None:
            params["is_admin"] = is_admin
        if current_username:
            params["current_username"] = current_username
        
        return self._request('GET', '/api/tasks', params=params)
    
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
            
        Raises:
            APIError: 任务结果获取失败
        """
        params = {"limit": limit}
        if status:
            params["status"] = status
        
        return self._request('GET', f'/api/tasks/{task_id}/results', params=params)
    
    # ==================== 文件上传API ====================
    
    def upload_file(self, file_path: str) -> Dict:
        """
        上传文件
        
        Args:
            file_path: 文件路径
        
        Returns:
            dict: {success, file_path, preview}
            
        Raises:
            APIError: 文件上传失败
        """
        # 确保文件存在
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        with open(file_path, 'rb') as f:
            # 使用字典格式，FastAPI期望的格式
            files = {'file': (os.path.basename(file_path), f, 'application/octet-stream')}
            return self._request('POST', '/api/upload', files=files)
    
    def upload_and_process(self, file_path: str, task_name: str = "批量任务") -> Dict:
        """
        上传文件并立即处理
        
        Args:
            file_path: 文件路径
            task_name: 任务名称
        
        Returns:
            dict: {success, task_id, total_count}
            
        Raises:
            APIError: 文件处理失败
        """
        try:
            # 确保文件存在
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"文件不存在: {file_path}")
            
            with open(file_path, 'rb') as f:
                filename = os.path.basename(file_path)
                files = {'file': (filename, f, 'application/octet-stream')}
                data = {'task_name': task_name}
                return self._request('POST', '/api/upload/process', files=files, data=data)
        except APIError as e:
            # 记录错误到日志
            from logger import business_logger
            business_logger.log_error('api_client', 'upload_and_process', e, file_path=file_path, task_name=task_name)
            raise
    
    # ==================== 报表API ====================
    
    # ==================== 硬件信息API ====================
    
    def get_hardware_info(self) -> Dict:
        """
        获取硬件配置信息
        
        Returns:
            dict: 硬件信息
            
        Raises:
            APIError: 硬件信息获取失败
        """
        return self._request('GET', '/api/hardware')
    
    # ==================== 系统配置API ====================
    
    def list_configs(self, category: Optional[str] = None) -> Dict:
        """
        查询系统配置列表
        
        Args:
            category: 配置分类过滤
        
        Returns:
            dict: 配置列表
            
        Raises:
            APIError: 配置列表获取失败
        """
        params = {}
        if category:
            params["category"] = category
        
        return self._request('GET', '/api/configs', params=params)
    
    def get_config(self, config_key: str) -> Dict:
        """
        查询单个配置
        
        Args:
            config_key: 配置键
        
        Returns:
            dict: 配置信息
            
        Raises:
            APIError: 配置获取失败
        """
        return self._request('GET', f'/api/configs/{config_key}')
    
    def update_config(self, config_key: str, value: str, config_type: str = "string") -> Dict:
        """
        更新系统配置
        
        Args:
            config_key: 配置键
            value: 配置值
            config_type: 配置类型
        
        Returns:
            dict: 更新结果
            
        Raises:
            APIError: 配置更新失败
        """
        params = {"value": value, "config_type": config_type}
        return self._request('PUT', f'/api/configs/{config_key}', params=params)
    
    # ==================== 用户管理API ====================
    
    def list_users(self) -> Dict:
        """
        查询用户列表
        
        Returns:
            dict: 用户列表
            
        Raises:
            APIError: 用户列表获取失败
        """
        return self._request('GET', '/api/users')
    
    def get_user(self, username: str) -> Dict:
        """
        查询单个用户
        
        Args:
            username: 用户名
        
        Returns:
            dict: 用户信息
            
        Raises:
            APIError: 用户获取失败
        """
        return self._request('GET', f'/api/users/{username}')
    
    def create_user(self, username: str, password: str, role: str = "user", email: str = "") -> Dict:
        """
        创建用户
        
        Args:
            username: 用户名
            password: 密码
            role: 角色
            email: 邮箱
        
        Returns:
            dict: 创建结果
            
        Raises:
            APIError: 用户创建失败
        """
        params = {
            "username": username,
            "password": password,
            "role": role,
            "email": email
        }
        return self._request('POST', '/api/users', params=params)
    
    def update_user(self, username: str, role: Optional[str] = None, is_active: Optional[bool] = None) -> Dict:
        """
        更新用户信息
        
        Args:
            username: 用户名
            role: 角色
            is_active: 是否激活
        
        Returns:
            dict: 更新结果
            
        Raises:
            APIError: 用户更新失败
        """
        params = {}
        if role:
            params["role"] = role
        if is_active is not None:
            params["is_active"] = str(is_active).lower()
        
        return self._request('PUT', f'/api/users/{username}', params=params)
    
    def delete_user(self, username: str) -> Dict:
        """
        删除用户
        
        Args:
            username: 用户名
        
        Returns:
            dict: 删除结果
            
        Raises:
            APIError: 用户删除失败
        """
        return self._request('DELETE', f'/api/users/{username}')
    
    # ==================== 健康检查 ====================
    
    def health_check(self) -> Dict:
        """
        健康检查
        
        Returns:
            dict: 健康状态
            
        Raises:
            APIError: 健康检查失败
        """
        return self._request('GET', '/health')
