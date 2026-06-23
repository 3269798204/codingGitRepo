"""
认证管理模块
实现用户登录、注册、会话管理和权限控制
"""

import hashlib
import os
import time
import uuid
from typing import Dict, Optional, List
from datetime import datetime

import os, sys
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from src.db.database import db_manager


class AuthManager:
    """认证管理器"""
    
    def __init__(self):
        # 内存会话存储（生产环境应使用Redis）
        self.sessions = {}
        # 会话过期时间（秒）
        self.session_ttl = 3600 * 24  # 24小时
    
    def hash_password(self, password: str, salt: str = None) -> tuple:
        """
        密码哈希（SHA256 + salt）
        
        Args:
            password: 明文密码
            salt: 盐值（可选，不提供则自动生成）
        
        Returns:
            tuple: (hashed_password, salt)
        """
        if salt is None:
            salt = hashlib.sha256(os.urandom(32)).hexdigest()
        
        hashed = hashlib.sha256((password + salt).encode('utf-8')).hexdigest()
        return hashed, salt
    
    def register_user(self, username: str, password: str, role: str = 'user') -> bool:
        """
        注册用户
        
        Args:
            username: 用户名
            password: 密码
            role: 角色（admin/user）
        
        Returns:
            bool: 是否成功
        """
        try:
            # 检查用户是否已存在
            existing_user = db_manager.get_user_by_username(username)
            if existing_user:
                return False
            
            # 哈希密码
            hashed_password, salt = self.hash_password(password)
            
            # 保存用户
            db_manager.create_user(username, hashed_password, salt, role)
            return True
            
        except Exception as e:
            print(f"❌ 注册用户失败: {e}")
            return False
    
    def login(self, username: str, password: str) -> Optional[str]:
        """
        用户登录
        
        Args:
            username: 用户名
            password: 密码
        
        Returns:
            str: session token（成功）或 None（失败）
        """
        try:
            # 获取用户信息
            user = db_manager.get_user_by_username(username)
            if not user:
                return None
            
            # 检查用户是否激活
            if not user.get('is_active', False):
                return None
            
            # 验证密码
            hashed_password, _ = self.hash_password(password, user['salt'])
            if hashed_password != user['password_hash']:
                return None
            
            # 生成session token
            session_token = str(uuid.uuid4())
            expires_at = time.time() + self.session_ttl
            
            # 保存会话
            self.sessions[session_token] = {
                'username': username,
                'role': user['role'],
                'expires_at': expires_at,
                'created_at': time.time()
            }
            
            # 记录登录日志
            db_manager.log_business_action('INFO', 'auth', 'login', 
                                          f'用户登录: {username}')
            
            return session_token
            
        except Exception as e:
            print(f"❌ 登录失败: {e}")
            return None
    
    def verify_session(self, session_token: str) -> Optional[Dict]:
        """
        验证会话
        
        Args:
            session_token: session token
        
        Returns:
            dict: 会话信息（包含username和role）或 None
        """
        if session_token not in self.sessions:
            return None
        
        session = self.sessions[session_token]
        
        # 检查是否过期
        if time.time() > session['expires_at']:
            del self.sessions[session_token]
            return None
        
        return {
            'username': session['username'],
            'role': session['role']
        }
    
    def logout(self, session_token: str):
        """登出"""
        if session_token in self.sessions:
            session_info = self.sessions[session_token]
            del self.sessions[session_token]
            
            # 记录登出日志
            db_manager.log_business_action('INFO', 'auth', 'logout',
                                          f"用户登出: {session_info['username']}")
    
    def has_permission(self, session_token: str, required_role: str = None) -> bool:
        """
        检查权限
        
        Args:
            session_token: session token
            required_role: 所需角色（admin/user）
        
        Returns:
            bool: 是否有权限
        """
        session_info = self.verify_session(session_token)
        if not session_info:
            return False
        
        # 如果没有指定角色要求，只要登录即可
        if required_role is None:
            return True
        
        # 检查角色权限
        user_role = session_info['role']
        
        # admin拥有所有权限
        if user_role == 'admin':
            return True
        
        # 检查具体角色
        return user_role == required_role
    
    def cleanup_expired_sessions(self):
        """清理过期会话"""
        current_time = time.time()
        expired_tokens = [
            token for token, session in self.sessions.items()
            if current_time > session['expires_at']
        ]
        for token in expired_tokens:
            del self.sessions[token]


# 全局认证管理器实例
auth_manager = AuthManager()


if __name__ == "__main__":
    # 测试
    print("测试认证管理器...")
    manager = AuthManager()
    
    # 注册测试用户
    success = manager.register_user("admin", "admin123", "admin")
    print(f"注册用户: {'成功' if success else '失败'}")
    
    # 登录测试
    token = manager.login("admin", "admin123")
    print(f"登录: {'成功' if token else '失败'}")
    print(f"Session Token: {token}")
    
    # 验证会话
    if token:
        info = manager.verify_session(token)
        print(f"会话信息: {info}")
        
        # 检查权限
        has_perm = manager.has_permission(token, "admin")
        print(f"是否有admin权限: {has_perm}")
