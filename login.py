"""
登录页面组件
Streamlit 登录界面
"""

import streamlit as st
from auth import auth_manager


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
                    session_token = auth_manager.login(username, password)
                    
                    if session_token:
                        st.session_state['logged_in'] = True
                        st.session_state['session_token'] = session_token
                        
                        # 获取用户信息
                        user_info = auth_manager.verify_session(session_token)
                        st.session_state['username'] = user_info['username']
                        st.session_state['user_role'] = user_info['role']
                        
                        st.success("✅ 登录成功！")
                        st.rerun()
                    else:
                        st.error("❌ 用户名或密码错误")
        
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
    认证装饰器
    检查用户是否已登录，未登录则显示登录页面
    """
    if 'logged_in' not in st.session_state or not st.session_state['logged_in']:
        show_login_page()
        return False
    
    # 验证会话是否有效
    session_token = st.session_state.get('session_token')
    if not session_token:
        st.session_state['logged_in'] = False
        show_login_page()
        return False
    
    user_info = auth_manager.verify_session(session_token)
    if not user_info:
        st.session_state['logged_in'] = False
        st.session_state.pop('session_token', None)
        show_login_page()
        return False
    
    return True


def show_logout_button():
    """显示登出按钮"""
    if st.sidebar.button("🚪 登出"):
        session_token = st.session_state.get('session_token')
        if session_token:
            auth_manager.logout(session_token)
        
        st.session_state['logged_in'] = False
        st.session_state.pop('session_token', None)
        st.session_state.pop('username', None)
        st.session_state.pop('user_role', None)
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
