"""
接口幂等性管理器
防止重复提交相同的请求
"""

import hashlib
import json
import time
from typing import Dict, Optional


class IdempotencyManager:
    """幂等性管理器（内存缓存实现）
    
    注意：生产环境建议使用 Redis 替代内存缓存，以支持多实例部署
    """
    
    def __init__(self, ttl: int = 300):
        self.cache: Dict[str, float] = {}
        self.ttl = ttl
    
    def generate_token(self, request_data: dict) -> str:
        content = json.dumps(request_data, sort_keys=True, default=str)
        token = hashlib.md5(content.encode("utf-8")).hexdigest()
        return token
    
    def check_and_set(self, token: str) -> bool:
        current_time = time.time()
        self._cleanup_expired(current_time)
        
        if token in self.cache:
            if current_time - self.cache[token] < self.ttl:
                return False
            else:
                del self.cache[token]
        
        self.cache[token] = current_time
        return True
    
    def _cleanup_expired(self, current_time: float):
        expired_tokens = [
            token for token, timestamp in self.cache.items()
            if current_time - timestamp >= self.ttl
        ]
        for token in expired_tokens:
            del self.cache[token]
    
    def get_cache_size(self) -> int:
        return len(self.cache)
    
    def clear(self):
        self.cache.clear()


idempotency_manager = IdempotencyManager(ttl=300)
