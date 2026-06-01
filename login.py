"""
登录页面组件
Streamlit 登录界面 - 支持localStorage持久化和API调用
"""

import streamlit as st
import streamlit.components.v1 as components
from api_client import APIClient
from auth import auth_manager

# 初始化API客户端
api_client = APIClient(base_url="http://localhost:8000")


def save_auth_to_localstorage(token: str, username: str, role: str):
    """保存认证信息到浏览器localStorage（持久化）"""
    js = f"""
    <script>
    localStorage.setItem('auth_token', '{token}');
    localStorage.setItem('username', '{username}');
    localStorage.setItem('user_role', '{role}');
    localStorage.setItem('logged_in', 'true');
    </script>
    """
    components.html(js, height=0)


def clear_auth_from_localstorage():
    """从浏览器localStorage清除认证信息"""
    js = """
    <script>
    localStorage.removeItem('auth_token');
    localStorage.removeItem('username');
    localStorage.removeItem('user_role');
    localStorage.removeItem('logged_in');
    </script>
    """
    components.html(js, height=0)


def restore_auth_from_localstorage():
    """从浏览器localStorage恢复认证信息并返回payload"""
    return components.html(
        """
        <script>
        const token = localStorage.getItem('auth_token');
        const username = localStorage.getItem('username');
        const role = localStorage.getItem('user_role');
        const loggedIn = localStorage.getItem('logged_in') === 'true';

        const payload = (loggedIn && token && username && role)
          ? {token, username, role}
          : null;

        window.parent.postMessage({
          type: 'streamlit:setComponentValue',
          value: payload
        }, '*');
        </script>
        """,
        height=0
    )


def show_login_page():
    """显示登录页面"""
    st.markdown("""
        <style>
        .login-container {
            max-width: 400px;
            margin: 100px auto;
            padding: 40px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    st.title("🔐 用户登录")
    st.markdown("---")
    
    # 登录表单
    with st.form("login_form"):
        username = st.text_input("👤 用户名", placeholder="请输入用户名")
        password = st.text_input("🔑 密码", type="password", placeholder="请输入密码")
        
        col1, col2 = st.columns(2)
        with col1:
            submit_button = st.form_submit_button("登录", use_container_width=True)
        with col2:
            register_button = st.form_submit_button("注册", use_container_width=True)
        
        if submit_button:
            if not username or not password:
                st.error("❌ 请输入用户名和密码")
            else:
                with st.spinner("正在登录..."):
                    try:
                        # 调用后端API登录
                        result = api_client.login(username, password)
                        
                        token = result['token']
                        username = result['username']
                        role = result['role']
                        
                        # 设置API客户端token
                        api_client.set_auth_token(token)
                        
                        # 保存到session_state
                        st.session_state['logged_in'] = True
                        st.session_state['session_token'] = token
                        st.session_state['username'] = username
                        st.session_state['user_role'] = role
                        # 保存到URL参数，支持刷新恢复
                        st.query_params = {
                            "auth_token": token,
                            "username": username,
                            "user_role": role
                        }
                        
                        # 保存到localStorage（持久化）
                        save_auth_to_localstorage(token, username, role)
                        
                        st.success("✅ 登录成功！")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ 登录失败: {str(e)}")
        
        if register_button:
            st.session_state['show_register'] = True
            st.rerun()
    
    # 注册表单
    if st.session_state.get('show_register', False):
        st.markdown("---")
        st.subheader("📝 新用户注册")
        
        with st.form("register_form"):
            reg_username = st.text_input("👤 用户名", key="reg_username")
            reg_password = st.text_input("🔑 密码", type="password", key="reg_password")
            reg_confirm_password = st.text_input("🔑 确认密码", type="password", key="reg_confirm")
            
            col1, col2 = st.columns(2)
            with col1:
                reg_submit = st.form_submit_button("注册", use_container_width=True)
            with col2:
                cancel_reg = st.form_submit_button("取消", use_container_width=True)
            
            if reg_submit:
                if not reg_username or not reg_password:
                    st.error("❌ 请填写所有字段")
                elif reg_password != reg_confirm_password:
                    st.error("❌ 两次输入的密码不一致")
                else:
                    with st.spinner("正在注册..."):
                        success = auth_manager.register_user(reg_username, reg_password, 'user')
                        
                        if success:
                            st.success("✅ 注册成功！请登录")
                            st.session_state['show_register'] = False
                            st.rerun()
                        else:
                            st.error("❌ 用户名已存在")
            
            if cancel_reg:
                st.session_state['show_register'] = False
                st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)


def require_auth():
    """
    认证检查
    检查用户是否已登录，未登录则显示登录页面
    
    优化策略：
    1. 先检查session_state
    2. 如果session_state没有，尝试从localStorage恢复
    3. 恢复成功后调用API验证token
    4. 验证通过则设置session_state
    """

    # 1. 快速路径：session_state中已有登录信息即可直接通过
    if (st.session_state.get('logged_in') and
        st.session_state.get('username') and
        st.session_state.get('user_role')):
        # 确保API客户端持有token（如果有）
        if st.session_state.get('session_token'):
            api_client.set_auth_token(st.session_state['session_token'])
        return True

    # 2. 尝试从URL参数恢复（刷新后）
    q = st.query_params
    token = q.get("auth_token")
    username = q.get("username")
    role = q.get("user_role")
    if token and username and role:
        st.session_state['logged_in'] = True
        st.session_state['session_token'] = token
        st.session_state['username'] = username
        st.session_state['user_role'] = role
        api_client.set_auth_token(token)
        return True

    # 3. 尝试从localStorage恢复（刷新后）
    payload = restore_auth_from_localstorage()
    if isinstance(payload, dict) and payload:
        st.session_state['logged_in'] = True
        st.session_state['session_token'] = payload.get('token')
        st.session_state['username'] = payload.get('username')
        st.session_state['user_role'] = payload.get('role')
        if payload.get('token'):
            api_client.set_auth_token(payload['token'])
        return True

    # 4. 未登录则直接显示登录页
    show_login_page()
    return False


def show_logout_button():
    """显示登出按钮"""
    if st.sidebar.button("🚪 登出"):
        # 清除API客户端token
        api_client.clear_auth_token()
        
        # 清除localStorage
        clear_auth_from_localstorage()
        
        # 清除session_state
        st.session_state['logged_in'] = False
        st.session_state.pop('session_token', None)
        st.session_state.pop('username', None)
        st.session_state.pop('user_role', None)
        st.session_state.pop('auth_restored', None)
        st.session_state.pop('restored_token', None)
        
        st.rerun()


def get_current_user():
    """获取当前登录用户信息"""
    if 'logged_in' in st.session_state and st.session_state['logged_in']:
        session_token = st.session_state.get('session_token')
        if session_token:
            return auth_manager.verify_session(session_token)
    return None


def is_admin():
    """检查当前用户是否为管理员"""
    user_role = st.session_state.get('user_role')
    return user_role == 'admin'
