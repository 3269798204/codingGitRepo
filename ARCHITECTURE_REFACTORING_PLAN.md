# 前后端分离架构方案

## 🎯 目标

1. **修复登录刷新问题** - 浏览器F5刷新后保持登录状态
2. **前后端服务分离** - app.py（前端UI）调用api.py（后端服务）
3. **后端单例模式** - 所有后端对象以单例模式创建
4. **API驱动** - 前端通过HTTP API调用后端功能

---

## 📐 架构设计

### 当前架构（混合式）

```
app.py (Streamlit UI)
├── 直接导入batch_processor
├── 直接导入csv_parser  
├── 直接导入db_manager
├── 直接调用业务逻辑
└── 认证逻辑在本地
```

**问题**:
- ❌ 前后端耦合
- ❌ 每次刷新都重新加载模块
- ❌ session_state刷新丢失
-  无法独立扩展

---

### 新架构（前后端分离）

```
┌─────────────────┐         HTTP API         ┌──────────────────┐
│   app.py        │  ◄────────────────────►  │   api.py         │
│  (Streamlit UI) │                          │  (FastAPI后端)   │
│                 │                          │                  │
│ • 登录页面      │                          │ • 任务管理API    │
│ • 仪表盘        │                          │ • 文件上传API    │
│ • 单个音频      │                          │ • 结果查询API    │
│ • 批量处理      │                          │ • 报表生成API    │
│ • 统计报表      │                          │                  │
─────────────────┘                          └─────────────────┘
                                                      │
                                          ┌───────────▼──────────┐
                                          │   后端单例对象        │
                                          │                      │
                                          │ • BatchProcessor     │
                                          │ • CSVParser          │
                                          │ • ReportGenerator    │
                                          │ • DatabaseManager    │
                                          │ • AuthManager        │
                                          ──────────────────────┘
```

**优势**:
- ✅ 前后端解耦
- ✅ 后端对象只加载一次（单例）
- ✅ 前端通过API调用，刷新不影响后端
- ✅ 可独立部署和扩展

---

## 🔐 登录刷新问题解决方案

### 问题根因

**Streamlit的session_state机制**:
- ✅ 在同一浏览器会话中持久（Tab内交互）
-  **F5刷新会创建新的session**（这是Streamlit的设计）
- ❌ 关闭浏览器后session丢失

**为什么刷新后session_state变成None**:
```python
# app.py 第44-51行
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False  # ← 刷新后会执行这行
```

每次F5刷新，Streamlit认为是新的连接，session_state被重置。

---

### 解决方案对比

#### 方案1: Cookie持久化（推荐）⭐

**实现思路**:
```python
# 登录时将token存入Cookie
import streamlit.components.v1 as components

def set_auth_cookie(token):
    js = f"""
    <script>
        document.cookie = "auth_token={token}; path=/; max-age=86400";
    </script>
    """
    components.html(js, height=0)

# 刷新时从Cookie读取
def get_auth_cookie():
    # 通过JavaScript读取Cookie
    js = """
    <script>
        var token = document.cookie.split(';').find(c => c.trim().startsWith('auth_token='));
        window.parent.postMessage(token ? token.split('=')[1] : null, '*');
    </script>
    """
    # 监听postMessage获取token
```

**优势**:
- ✅ F5刷新后仍保持登录
- ✅ 关闭浏览器后仍可保持（设置max-age）
- ✅ 符合Web标准

**局限**:
- ️ 需要JavaScript配合
- ️ Streamlit原生不支持Cookie

---

#### 方案2: localStorage持久化（简单）⭐⭐

**实现思路**:
```python
import streamlit.components.v1 as components

# 登录时保存
def save_to_localstorage(key, value):
    js = f"""
    <script>
        localStorage.setItem('{key}', '{value}');
    </script>
    """
    components.html(js, height=0)

# 刷新时恢复
def load_from_localstorage(key):
    # 通过JavaScript读取并postMessage回Python
    ...
```

**优势**:
- ✅ 实现简单
- ✅ F5刷新后保持
- ✅ 关闭浏览器后仍保持

**局限**:
- ️ 需要JavaScript桥接

---

#### 方案3: URL参数传递（不推荐）

```python
# 登录成功后重定向带token
st.query_params["token"] = session_token
```

**问题**:
- ❌ 不安全（token暴露在URL）
- ❌ URL长度限制
- ❌ 用户体验差

---

### 推荐方案: localStorage + API认证

**完整实现**:

#### 1. 前端（app.py）

```python
import streamlit as st
import streamlit.components.v1 as components
import requests

API_BASE_URL = "http://localhost:8000"

# ==================== Cookie/LocalStorage管理 ====================

def init_auth_storage():
    """初始化认证存储（JavaScript桥接）"""
    js = """
    <script>
    // 读取localStorage中的token
    var token = localStorage.getItem('auth_token');
    var username = localStorage.getItem('username');
    var role = localStorage.getItem('user_role');
    
    if (token) {
        window.parent.postMessage({
            type: 'auth_restore',
            token: token,
            username: username,
            role: role
        }, '*');
    }
    </script>
    """
    components.html(js, height=0)

def save_auth_to_storage(token, username, role):
    """保存认证信息到localStorage"""
    js = f"""
    <script>
    localStorage.setItem('auth_token', '{token}');
    localStorage.setItem('username', '{username}');
    localStorage.setItem('user_role', '{role}');
    </script>
    """
    components.html(js, height=0)

def clear_auth_storage():
    """清除认证信息"""
    js = """
    <script>
    localStorage.removeItem('auth_token');
    localStorage.removeItem('username');
    localStorage.removeItem('user_role');
    </script>
    """
    components.html(js, height=0)

# ==================== 认证检查 ====================

def require_auth():
    """认证检查 - 支持localStorage持久化"""
    
    # 1. 检查session_state
    if st.session_state.get('logged_in'):
        return True
    
    # 2. 尝试从localStorage恢复
    if 'auth_restored' not in st.session_state:
        st.session_state.auth_restored = False
        init_auth_storage()
        return False
    
    # 3. 验证token
    token = st.session_state.get('restored_token')
    if token:
        # 调用后端API验证
        try:
            response = requests.get(
                f"{API_BASE_URL}/api/auth/verify",
                headers={"Authorization": f"Bearer {token}"}
            )
            if response.status_code == 200:
                user_info = response.json()
                st.session_state['logged_in'] = True
                st.session_state['username'] = user_info['username']
                st.session_state['user_role'] = user_info['role']
                st.session_state['session_token'] = token
                return True
        except:
            pass
    
    # 4. 显示登录页面
    show_login_page()
    return False
```

---

#### 2. 后端（api.py）

```python
from fastapi import FastAPI, HTTPException, Header
from typing import Optional

app = FastAPI()

# 后端单例对象
batch_processor = BatchProcessor()  # 只创建一次
csv_parser = CSVParser()
report_gen = ReportGenerator()

@app.get("/api/auth/verify")
async def verify_token(authorization: Optional[str] = Header(None)):
    """验证token"""
    if not authorization:
        raise HTTPException(status_code=401, detail="未提供token")
    
    token = authorization.replace("Bearer ", "")
    
    # 验证token（从数据库或Redis）
    user_info = auth_manager.verify_session(token)
    if not user_info:
        raise HTTPException(status_code=401, detail="token无效或已过期")
    
    return user_info

@app.post("/api/auth/login")
async def login(username: str, password: str):
    """用户登录"""
    token = auth_manager.login(username, password)
    if not token:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    
    user_info = auth_manager.verify_session(token)
    return {
        "token": token,
        "username": user_info['username'],
        "role": user_info['role']
    }
```

---

## 🏗️ 实施步骤

### 第一阶段: 修复登录刷新（1-2天）

1. ✅ 实现localStorage桥接
2. ✅ 修改login.py支持持久化
3. ✅ 修改app.py的require_auth逻辑
4. ✅ 测试F5刷新保持登录

### 第二阶段: 后端API完善（2-3天）

1. ✅ 在api.py中添加认证API
2. ✅ 添加所有业务API端点
3. ✅ 实现单例模式的后端对象
4. ✅ 添加API文档（Swagger）

### 第三阶段: 前端改造（3-5天）

1. ✅ 修改app.py调用API而非直接导入
2. ✅ 移除app.py中的业务逻辑
3. ✅ 实现错误处理和重试
4. ✅ 添加加载状态提示

### 第四阶段: 测试和优化（2-3天）

1. ✅ 端到端测试
2. ✅ 性能测试
3. ✅ 安全性检查
4. ✅ 文档更新

---

## 📁 文件结构

### 当前结构

```
voice-analysis-web/
├── app.py              # Streamlit UI + 业务逻辑（混合）
── api.py              # FastAPI（未充分利用）
├── login.py            # 认证UI
├── auth.py             # 认证逻辑
├── batch_processor.py  # 业务逻辑
└── ...
```

### 新结构

```
voice-analysis-web/
├── frontend/                   # 前端目录
│   ├── app.py                 # Streamlit UI（纯前端）
│   ├── login.py               # 登录页面
│   ├── api_client.py          # API客户端
│   └── components/            # UI组件
│
├── backend/                    # 后端目录
│   ├── api.py                 # FastAPI服务
│   ├── services/              # 业务服务
│   │   ├── batch_service.py   # 批处理服务
│   │   ├── auth_service.py    # 认证服务
│   │   └── report_service.py  # 报表服务
│   ├── models/                # 数据模型
│   └── singletons.py          # 单例对象管理
│
└── shared/                     # 共享模块
    ├── config.py
    ├── database.py
    └── utils.py
```

---

## 💡 关键技术点

### 1. Streamlit JavaScript桥接

```python
import streamlit.components.v1 as components
import streamlit as st

# 发送数据到JavaScript
def send_to_js(data):
    js = f"""
    <script>
    window.parent.postMessage({data}, '*');
    </script>
    """
    components.html(js, height=0)

# 接收JavaScript数据
@st.experimental_fragment
def receive_from_js():
    # 使用st.query_params或st.session_state
    ...
```

### 2. API客户端封装

```python
import requests
from typing import Dict, Optional

class APIClient:
    """API客户端"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = requests.Session()
    
    def set_auth_token(self, token: str):
        """设置认证token"""
        self.session.headers.update({
            "Authorization": f"Bearer {token}"
        })
    
    def login(self, username: str, password: str) -> Dict:
        """登录"""
        response = self.session.post(
            f"{self.base_url}/api/auth/login",
            json={"username": username, "password": password}
        )
        response.raise_for_status()
        return response.json()
    
    def get_tasks(self, limit: int = 50) -> Dict:
        """获取任务列表"""
        response = self.session.get(
            f"{self.base_url}/api/tasks",
            params={"limit": limit}
        )
        response.raise_for_status()
        return response.json()
```

### 3. 后端单例模式

```python
# backend/singletons.py

from functools import lru_cache

@lru_cache(maxsize=1)
def get_batch_processor():
    """获取批处理器单例"""
    return BatchProcessor()

@lru_cache(maxsize=1)
def get_csv_parser():
    """获取CSV解析器单例"""
    return CSVParser()

# 使用
processor = get_batch_processor()  # 只创建一次
```

---

## ⚠️ 注意事项

### 1. 安全性

- 🔒 使用HTTPS
- 🔒 Token设置过期时间
- 🔒 API限流
- 🔒 CORS配置

### 2. 性能

-  使用连接池
-  实现缓存机制
-  异步处理耗时操作

### 3. 错误处理

- 🛡️ API超时处理
- 🛡️ 重试机制
- 🛡️ 友好的错误提示

---

## ✨ 预期收益

### 修复登录刷新问题

| 场景 | 修改前 | 修改后 |
|------|--------|--------|
| F5刷新 | ❌ 需要重新登录 | ✅ 保持登录 |
| 切换Tab | ✅ 保持登录 | ✅ 保持登录 |
| 关闭浏览器 | ❌ 丢失 | ✅ 保持（localStorage） |

### 前后端分离收益

| 方面 | 修改前 | 修改后 |
|------|--------|--------|
| 耦合度 | ❌ 高 | ✅ 低 |
| 可维护性 | ⭐ | ⭐⭐⭐⭐⭐ |
| 可扩展性 | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| 部署灵活性 | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| 团队分工 | ❌ 困难 | ✅ 容易 |

---

##  下一步行动

1. **确认方案** - 与我讨论并确认实施方案
2. **分阶段实施** - 按阶段逐步改造
3. **测试验证** - 每个阶段完成后测试
4. **文档更新** - 更新相关文档

**建议从第一阶段开始**：先解决登录刷新问题，再进行前后端分离。
