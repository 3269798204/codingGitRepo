"""
Streamlit Web UI 主应用
语音识别分析系统 v3.0
"""

import json
import os
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import time
from datetime import datetime
from typing import Optional

import os, sys
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from src.core.compat_layer import db_manager
from src.core.config import config
from src.web.login import require_auth, show_logout_button, is_admin, api_client

# ==================== 页面配置 ====================

st.set_page_config(
    page_title="语音识别分析系统 v3.0",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== 初始化组件 ====================

# 初始化 session state（确保登录状态持久化）
# 关键：只在首次运行时初始化，刷新时保留已有状态
if 'submitted_requests' not in st.session_state:
    st.session_state.submitted_requests = set()

if 'ui_css_injected' not in st.session_state:
    st.markdown(
        """
        <style>
        div[data-testid="stDataFrameEditedCell"],
        div[data-testid="stDataFrameEditableCell"][data-content-is-edited="true"],
        div[data-baseweb="data-table"] [data-is-edited="true"] {
            background-color: transparent !important;
            box-shadow: none !important;
            border: none !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )
    st.session_state.ui_css_injected = True

# 确保登录相关字段存在（防止刷新时丢失）
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'username' not in st.session_state:
    st.session_state.username = None
if 'user_role' not in st.session_state:
    st.session_state.user_role = None
if 'session_token' not in st.session_state:
    st.session_state.session_token = None

# 监听来自JavaScript的localStorage数据
def on_message():
    """接收localStorage恢复的认证信息"""
    js = """
    <script>
    window.addEventListener('message', function(e) {
        if (e.data.type === 'auth_restore') {
            window.parent.postMessage({
                type: 'streamlit:setComponentValue',
                value: {
                    token: e.data.token,
                    username: e.data.username,
                    role: e.data.role
                }
            }, '*');
        }
    });
    </script>
    """
    components.html(js, height=0)

# 初始化监听
if 'message_listener_initialized' not in st.session_state:
    st.session_state['message_listener_initialized'] = True
    on_message()

# ==================== 认证检查 ====================
# 注意：必须在模型加载完成后才进行认证检查

if not require_auth():
    st.stop()

# ==================== 获取单例资源 ====================
# 这些对象只会在首次调用时创建，后续请求直接使用缓存

# 使用API客户端（已全局初始化）
# 批量处理、解析器等能力均通过后端 API 获取


# ==================== 通用组件 ====================

def render_url_with_copy(url: str, label: str = "URL", max_length: int = 80):
    """
    渲染带复制功能的URL链接
    
    Args:
        url: URL地址
        label: 显示标签
        max_length: 最大显示长度
    
    Returns:
        None (直接渲染到页面)
    """
    if not url:
        st.text("N/A")
        return
    
    # 截断显示
    display_url = url if len(url) <= max_length else url[:max_length] + "..."
    
    # 使用columns布局
    col1, col2 = st.columns([4, 1])
    
    with col1:
        # 显示为可点击的链接，带悬浮效果
        st.markdown(
            f"<a href='{url}' target='_blank' "
            f"style='color: #1f77b4; text-decoration: underline; cursor: pointer;' "
            f"onmouseover=\"this.style.color='#ff6b6b'\" "
            f"onmouseout=\"this.style.color='#1f77b4'\">"
            f"{display_url}"
            f"</a>",
            unsafe_allow_html=True
        )
    
    with col2:
        # 复制按钮
        if st.button("📋 复制", key=f"copy_{hash(url)}", help="复制链接到剪贴板"):
            # Streamlit不支持直接复制到剪贴板，使用代码块替代
            st.code(url, language=None)
            st.success("✅ 已显示完整URL，请手动复制（Ctrl+C / Cmd+C）")


def render_json_with_copy(data: dict, label: str = "JSON数据"):
    """
    渲染带复制功能的JSON数据
    
    Args:
        data: JSON数据
        label: 显示标签
    
    Returns:
        None (直接渲染到页面)
    """
    if not data:
        st.text("N/A")
        return
    
    import json
    json_str = json.dumps(data, ensure_ascii=False, indent=2)
    
    # 显示JSON
    st.json(data)
    
    # 提供复制按钮
    if st.button("📋 复制JSON", key=f"copy_json_{hash(json_str)}", help="复制JSON到剪贴板"):
        st.code(json_str, language="json")
        st.success("✅ 已显示JSON，请手动复制（Ctrl+C / Cmd+C）")


def validate_uri(uri: str) -> bool:
    """验证URI是否为有效的http/https地址"""
    if not uri:
        return False
    uri = uri.strip()
    return uri.startswith('http://') or uri.startswith('https://')


ROLE_ALIASES = {
    "customer": "customer",
    "user": "customer",
    "client": "customer",
    "客户": "customer",
    "顾客": "customer",
    "乘客": "customer",
    "customer_service": "customer_service",
    "agent": "customer_service",
    "客服": "customer_service",
    "坐席": "customer_service",
    "质检": "customer_service",
    "话务员": "customer_service",
    "system": "system",
    "系统": "system",
    "机器人": "system",
}


ROLE_LABELS = {
    "customer": "客户",
    "customer_service": "客服",
    "system": "系统",
    "unknown": "其他角色",
}


def _normalize_role(role: str) -> str:
    if not role:
        return "unknown"

    cleaned = str(role).strip()
    lowered = cleaned.lower()

    for candidate in (cleaned, lowered, cleaned.replace(" ", ""), lowered.replace(" ", "")):
        if candidate in ROLE_ALIASES:
            return ROLE_ALIASES[candidate]

    return lowered or "unknown"


def _format_role_label(role: str) -> str:
    normalized = _normalize_role(role)
    if normalized in ROLE_LABELS:
        return ROLE_LABELS[normalized]
    return role.replace('_', ' ').title() if role else "其他角色"


def build_participant_summaries(participants: list) -> dict:
    """根据participants结构化数据生成角色摘要文本"""
    summaries = {}

    for participant in participants or []:
        role = _normalize_role(participant.get('role'))
        fragments = []

        summary_text = (participant.get('summary') or '').strip()
        if summary_text:
            fragments.append(summary_text)

        emotion_info = participant.get('emotion_analysis') or {}
        emotion_desc = (emotion_info.get('emotion_description') or '').strip()
        if emotion_desc and emotion_desc not in fragments:
            fragments.append(emotion_desc)
        else:
            primary_emotions = emotion_info.get('primary_emotions') or []
            if primary_emotions:
                fragments.append("情绪：" + "、".join(primary_emotions))

        if participant.get('abusive_remarks'):
            examples = participant.get('abusive_examples')
            if examples:
                fragments.append("包含辱骂：" + "、".join(examples))
            else:
                fragments.append("包含辱骂言论")

        if fragments:
            summaries.setdefault(role, []).append("；".join(fragments))

    return {role: "；".join(texts) for role, texts in summaries.items()}


def render_participant_summaries(participants: list) -> bool:
    """在前端渲染角色摘要，返回是否渲染成功"""
    summaries = build_participant_summaries(participants)
    if not summaries:
        return False

    ordered_roles = []
    for preferred in ("customer", "customer_service", "system", "unknown"):
        if preferred in summaries and preferred not in ordered_roles:
            ordered_roles.append(preferred)

    for role in summaries:
        if role not in ordered_roles:
            ordered_roles.append(role)

    for role in ordered_roles:
        st.markdown(f"- **{_format_role_label(role)}**: {summaries[role]}")

    return True


def _resolve_result_display_label(result: dict, index: int) -> str:
    """为批量任务记录生成更友好的展示标题"""
    extra = result.get('extra_data') or {}

    preferred_keys = [
        "客户名称", "客户编码", "客户编号", "客户ID", "customer", "customer_id",
        "手机号", "手机", "mobile", "phone"
    ]

    for key in preferred_keys:
        value = extra.get(key)
        if value:
            return str(value)

    audio_url = result.get('audio_url') or ''
    if audio_url:
        return audio_url.rsplit('/', 1)[-1] or audio_url

    return f"记录 {index}"


@st.cache_data(show_spinner=False, ttl=300)
def fetch_hardware_info_cached(token: Optional[str]) -> dict:
    return api_client.get_hardware_info()


@st.cache_data(show_spinner=False, ttl=120)
def fetch_configs_cached(token: Optional[str], category: Optional[str]) -> dict:
    return api_client.list_configs(category)


@st.cache_data(show_spinner=False, ttl=120)
def fetch_users_cached(token: Optional[str]) -> dict:
    return api_client.list_users()


def _extract_customer_code_from_result(result: dict) -> str:
    # 客户编码取值逻辑为 audio_result.customer_no
    return result.get('customer_no') or "N/A"


def _fetch_customer_code(task_id: str) -> str:
    """
    获取任务的客户编码
    客户编码取值逻辑为 audio_result.customer_no
    """

    try:
        resp = api_client.get_task_results(task_id, limit=1)
        results = resp.get('results', [])
    except Exception:
        return "N/A"

    if not results:
        return "N/A"

    result = results[0]
    return _extract_customer_code_from_result(result)


def get_customer_code(task_id: str) -> str:
    cache = st.session_state.setdefault('_customer_code_cache', {})
    if task_id in cache:
        return cache[task_id]

    # 客户编码取值逻辑为 audio_result.customer_no
    code = _fetch_customer_code(task_id)
    cache[task_id] = code
    return code


# ==================== 结果详情展示函数 ====================

def show_result_detail(task_id: str):
    """显示任务结果详情（按任务类型区分）"""

    task_info = api_client.get_task(task_id)
    if not task_info:
        st.error("❌ 任务不存在")
        return

    try:
        initial_response = api_client.get_task_results(task_id, limit=2)
        initial_results = initial_response.get('results', [])
    except Exception as exc:
        st.error(f"❌ 获取任务结果失败: {exc}")
        return

    if not initial_results:
        st.info("暂无结果数据")
        return

    is_single_audio = len(initial_results) == 1

    if is_single_audio:
        result = initial_results[0]
        _show_single_audio_detail(task_info, result)
        st.session_state.setdefault('_customer_code_cache', {})[task_id] = _extract_customer_code_from_result(result)
    else:
        try:
            full_response = api_client.get_task_results(task_id, limit=1000)
            results = full_response.get('results', [])
        except Exception as exc:
            st.error(f"❌ 获取批量结果失败: {exc}")
            return

        if not results:
            st.info("暂无结果数据")
            return

        st.session_state.setdefault('_customer_code_cache', {})[task_id] = _extract_customer_code_from_result(results[0])
        _show_excel_import_detail(task_info, results)


def _show_single_audio_detail(task_data: dict, result: dict):
    """显示单个音频任务详情"""
    st.markdown("### 🎵 单个音频任务")
    
    # 1. 显示原始输入数据
    origin_data = result.get('origin_data', {})
    if origin_data:
        st.markdown("#### 📍 原始输入数据")
        render_json_with_copy(origin_data, "原始输入数据")
    
    # 2. 语音识别内容
    st.markdown("#### 📝 语音识别内容")
    full_text = result.get('full_text', '')
    st.text_area("完整文本", full_text, height=200, key=f"text_{result.get('id', '')}")
    
    # 3. LLM分析报告表格
    st.markdown("#### 🤖 LLM 分析报告")
    
    # 构建分析数据表格
    analysis_data = [
        {"指标": "音频时长", "值": f"{result.get('duration') or 0:.1f} 秒"},
        {"指标": "处理时间", "值": f"{result.get('processing_time') or 0:.1f} 秒"},
        {"指标": "实时因子", "值": f"{result.get('realtime_factor') or 0:.2f}x"},
        {"指标": "置信度", "值": f"{result.get('confidence') or 0:.2%}"},
        {"指标": "语言", "值": result.get('language', 'zh')},
        {"指标": "是否包含辱骂", "值": "是 ⚠️" if result.get('has_abusive_language') else "否 ✅"},
    ]
    
    df_analysis = pd.DataFrame(analysis_data)
    st.dataframe(df_analysis, use_container_width=True, hide_index=True)
    
    # AI对话摘要
    dialogue_summary = (result.get('dialogue_summary') or '').strip()
    if dialogue_summary:
        st.markdown("**对话摘要**:")
        st.info(dialogue_summary)

    participants = result.get('participants') or []
    if participants:
        st.markdown("**对话角色摘要**:")
        if not render_participant_summaries(participants):
            st.info("暂无可用的角色摘要文本")

    abusive_words = result.get('abusive_words') or result.get('abusive_words_list') or []
    if abusive_words:
        st.markdown("**辱骂词汇**:")
        st.warning(", ".join(abusive_words))
    
    # CSV导出
    st.markdown("---")
    csv_data = _generate_single_audio_csv(result)
    st.download_button(
        label="📥 导出为 CSV",
        data=csv_data,
        file_name=f"single_audio_{task_data['task_id']}.csv",
        mime="text/csv",
        key=f"download_{task_data['task_id']}"
    )


def _show_excel_import_detail(task_data: dict, results: list):
    """显示Excel导入任务详情"""
    st.markdown(f"### 📁 Excel 批量导入任务 ({len(results)} 条记录)")
    
    # 获取第一条结果的extra_data来确定Excel字段
    first_result = results[0]
    extra_data = first_result.get('extra_data', {})
    origin_data = first_result.get('origin_data', {})
    
    # 1. 显示原始输入数据（如果有）
    if origin_data:
        st.markdown("#### 📍 原始输入数据")
        render_json_with_copy(origin_data, "原始输入数据")
    
    # 2. 显示所有Excel字段 + 语音识别内容 + LLM分析
    st.markdown("#### 📊 完整数据表格")
    
    data_list = []
    for result in results:
        row = {}
        
        # 添加Excel原始字段
        extra = result.get('extra_data', {})
        if extra:
            row.update(extra)
        
        # 添加语音识别内容
        row['语音识别内容'] = result.get('full_text', '')
        
        # 添加LLM分析字段
        row['对话摘要'] = result.get('dialogue_summary', '')
        row['是否辱骂'] = '是' if result.get('has_abusive_language') else '否'
        role_summaries = build_participant_summaries(result.get('participants') or [])
        row['客户摘要'] = role_summaries.get('customer') or role_summaries.get('user') or ''
        row['客服摘要'] = role_summaries.get('customer_service') or role_summaries.get('agent') or ''
        other_roles = [
            f"{_format_role_label(role)}: {content}"
            for role, content in role_summaries.items()
            if role not in {'customer', 'user', 'customer_service', 'agent'}
        ]
        row['其他角色摘要'] = " | ".join(other_roles) if other_roles else ''
        
        # 添加其他信息
        row['音频URL'] = result.get('audio_url', '')
        row['时长(秒)'] = result.get('duration', 0)
        row['置信度'] = f"{result.get('confidence', 0):.2%}"
        row['状态'] = result.get('status', '')
        
        data_list.append(row)
    
    df_results = pd.DataFrame(data_list)
    st.dataframe(df_results, use_container_width=True, hide_index=True)

    # 2.1 展示每条记录的对话角色摘要
    st.markdown("#### 🗣️ 对话角色摘要")
    any_summary = False
    for idx, result in enumerate(results, start=1):
        participants = result.get('participants') or []
        label = _resolve_result_display_label(result, idx)

        st.markdown(f"##### 🎧 {label}")
        dialogue_summary = (result.get('dialogue_summary') or '').strip()
        if dialogue_summary:
            st.markdown("**对话摘要:**")
            st.info(dialogue_summary)

        if participants:
            if render_participant_summaries(participants):
                any_summary = True
            else:
                st.info("暂无可用的角色摘要文本")
        else:
            st.info("暂无参与者信息")

    if not any_summary:
        st.info("暂无可用的角色摘要文本")

    
    # 3. CSV导出
    st.markdown("---")
    csv_data = df_results.to_csv(index=False, encoding='utf-8-sig')
    st.download_button(
        label="📥 导出为 CSV",
        data=csv_data,
        file_name=f"batch_{task_data['task_id']}.csv",
        mime="text/csv",
        key=f"download_{task_data['task_id']}"
    )


def _generate_single_audio_csv(result: dict) -> str:
    """生成单个音频的CSV数据"""
    import io
    
    output = io.StringIO()
    
    # 写入基本信息
    output.write("指标,值\n")
    output.write(f"音频URL,{result.get('audio_url', '')}\n")
    output.write(f"音频时长,{result.get('duration', 0):.1f}秒\n")
    output.write(f"处理时间,{result.get('processing_time', 0):.1f}秒\n")
    output.write(f"实时因子,{result.get('realtime_factor', 0):.2f}x\n")
    output.write(f"置信度,{result.get('confidence', 0):.2%}\n")
    output.write(f"语言,{result.get('language', 'zh')}\n")
    output.write(f"是否辱骂,{'是' if result.get('has_abusive_language') else '否'}\n")
    output.write(f"对话摘要,{result.get('dialogue_summary', '')}\n")
    output.write(f"辱骂词汇,{','.join(result.get('abusive_words', []))}\n")
    output.write("\n")
    
    # 写入识别文本
    output.write("语音识别内容\n")
    output.write(f"{result.get('full_text', '')}\n")
    
    return output.getvalue()


# ==================== 侧边栏配置 ====================

st.sidebar.title("⚙️ 系统配置")

# 显示当前用户信息
if 'username' in st.session_state:
    st.sidebar.markdown(f"### 👤 当前用户: {st.session_state['username']}")
    if 'user_role' in st.session_state:
        role_badge = "👑 管理员" if st.session_state['user_role'] == 'admin' else "👤 普通用户"
        st.sidebar.markdown(f"**角色**: {role_badge}")
    
    # 登出按钮
    show_logout_button()
    st.sidebar.markdown("---")

# 硬件信息显示
st.sidebar.markdown("### ️ 硬件信息")

# 设置默认配置（防止API调用失败）
default_rec = {
    'model_size': 'base',
    'beam_size': 3,
    'max_workers': 4,
    'description': '默认配置'
}

try:
    hardware_info = fetch_hardware_info_cached(st.session_state.get('session_token'))
    hw = hardware_info.get('hardware', {})
    rec = hardware_info.get('recommended', default_rec)

    if hw:
        st.sidebar.text(f"CPU: {hw.get('cpu_cores', 'N/A')} 核")
        st.sidebar.text(f"GPU: {hw.get('gpu_type', 'N/A')}")

        if hw.get('gpu_name'):
            st.sidebar.text(f"型号: {hw['gpu_name']}")

        if hw.get('gpu_memory_gb', 0) > 0:
            st.sidebar.text(f"显存: {hw['gpu_memory_gb']:.1f} GB")

    st.sidebar.markdown("### 💡 推荐配置")
    st.sidebar.success(rec.get('description', default_rec['description']))
    st.sidebar.text(f"模型: {rec.get('model_size', default_rec['model_size'])}")
    st.sidebar.text(f"Beam Size: {rec.get('beam_size', default_rec['beam_size'])}")
    st.sidebar.text(f"并发数: {rec.get('max_workers', default_rec['max_workers'])}")
except Exception as e:
    st.sidebar.warning(f"⚠️ 无法获取硬件信息: {str(e)}")
    rec = default_rec

# 手动配置覆盖
st.sidebar.markdown("---")
st.sidebar.markdown("### 🔧 手动配置")

model_size = st.sidebar.selectbox(
    "模型大小",
    ["tiny", "base", "small", "medium", "large"],
    index=["tiny", "base", "small", "medium", "large"].index(rec['model_size'])
)

beam_size = st.sidebar.slider("Beam Size", 1, 5, rec['beam_size'])

max_workers = st.sidebar.slider("最大并发数", 1, 8, rec['max_workers'])


# ==================== 主页面 ====================

st.title("🎙️ 语音识别分析系统 v3.0")
st.markdown("---")

# Tab 切换
# 使用session_state跟踪当前tab，实现局部刷新
tab_names = ["📊 仪表盘", "🎵 单个音频", "📁 批量处理", "⚙️ 系统配置"]
if 'current_tab' not in st.session_state:
    st.session_state.current_tab = 0

tab1, tab2, tab3, tab4 = st.tabs(tab_names)


# ==================== Tab 1: 仪表盘 ====================

with tab1:
    st.header("📊 系统概览")

    refresh_col, _ = st.columns([1, 3])
    with refresh_col:
        if st.button("🔄 刷新任务列表", key="refresh_tasks"):
            # 清除所有任务相关的缓存键
            for k in list(st.session_state.keys()):
                if k.startswith("_tasks_cache") or k == '_customer_code_cache':
                    st.session_state.pop(k, None)
            st.rerun()
    
    # 1. 始终查询并展示全局任务统计指标（不随列表查询过滤而改变，展示系统真实概览）
    try:
        if st.session_state.get('_tasks_cache_all') is None:
            st.session_state['_tasks_cache_all'] = api_client.list_tasks(limit=100)
        all_tasks_response = st.session_state['_tasks_cache_all']
        all_tasks = all_tasks_response.get('tasks', [])
    except Exception as e:
        all_tasks = []
        from src.logger.logger import business_logger
        business_logger.log_error('app', 'list_all_tasks_dashboard', e)
    
    total_tasks = len(all_tasks)
    running_tasks = sum(1 for t in all_tasks if t['status'] == 'running')
    completed_tasks = sum(1 for t in all_tasks if t['status'] == 'completed')
    failed_tasks = sum(1 for t in all_tasks if t['status'] == 'failed')
    
    # 显示统计卡片
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("总任务数", total_tasks)
    
    with col2:
        st.metric("运行中", running_tasks)
    
    with col3:
        st.metric("已完成", completed_tasks)
    
    with col4:
        st.metric("失败", failed_tasks)
    
    # 最近任务列表与多维度查询
    st.subheader("📋 最近任务")
    
    # 2. 多维度查询输入框（支持任务名称、客户编码、用户编号的后台数据库联合查询）
    filter_col1, filter_col2, filter_col3, filter_col4 = st.columns(4)
    with filter_col1:
        task_name_filter = st.text_input("🔍 按任务名称查询", placeholder="支持模糊匹配任务名称", key="task_name_query_filter")
    with filter_col2:
        customer_filter = st.text_input("👤 按客户编码查询", placeholder="与语音结果等值连接过滤", key="customer_code_query_filter")
    with filter_col3:
        user_filter = st.text_input("🆔 按用户编号查询", placeholder="输入用户编号过滤", key="user_id_query_filter")
    with filter_col4:
        task_filter = st.text_input("🆔 按任务编码查询", placeholder="输入任务ID过滤", key="task_id_query_filter")
    
    # 3. 动态从后台数据库查询任务列表
    try:
        # 获取当前用户信息
        is_admin = st.session_state.get('user_role') == 'admin'
        current_username = st.session_state.get('username')
        
        # 使用过滤条件组合生成缓存键，保证输入变化时自动刷新后端请求
        cache_key = f"_tasks_cache_{task_name_filter}_{customer_filter}_{user_filter}_{is_admin}_{current_username}"
        if st.session_state.get(cache_key) is None:
            # 清除其他旧的带条件任务列表缓存
            for k in list(st.session_state.keys()):
                if k.startswith("_tasks_cache_"):
                    st.session_state.pop(k, None)
            st.session_state[cache_key] = api_client.list_tasks(
                limit=100,
                customer_no=customer_filter if customer_filter else None,
                task_name=task_name_filter if task_name_filter else None,
                user_id=user_filter if (user_filter and is_admin) else None,
                is_admin=is_admin,
                current_username=current_username
            )
        tasks_response = st.session_state[cache_key]
        tasks = tasks_response.get('tasks', [])
    except Exception as e:
        st.error(f"❌ 获取任务列表失败: {str(e)}")
        # 记录详细错误到后端日志
        from src.logger.logger import business_logger
        business_logger.log_error('app', 'list_tasks_with_filters', e)
        tasks = []
    
    if tasks:
        df_tasks = pd.DataFrame(tasks)

        # 4. 前端辅助任务ID本地筛选
        if task_filter:
            df_tasks = df_tasks[df_tasks['task_id'].str.contains(task_filter, case=False, na=False)]

        # 格式化显示
        # 重命名列
        df_display = df_tasks[['task_id', 'task_name', 'status', 'total_count', 'processed_count', 'success_count', 'progress', 'created_at']].copy()
        df_display.rename(columns={
            'task_id': '任务ID',
            'task_name': '任务名称',
            'status': '状态',
            'total_count': '总数',
            'processed_count': '已处理',
            'success_count': '成功数',
            'progress': '进度',
            'created_at': '创建时间'
        }, inplace=True)

        # 客户编号列：取值为 audio_result.customer_no
        customer_no_map = {
            row['task_id']: (str(row['customer_no']).strip() if row.get('customer_no') else "N/A")
            for _, row in df_tasks.iterrows()
        }
        df_display.insert(
            1,
            '客户编号',
            df_display['任务ID'].apply(lambda tid: customer_no_map.get(tid, "N/A"))
        )

        # 用户编号列：取值为 users.username
        username_map = {
            row['task_id']: (str(row['username']).strip() if row.get('username') else "N/A")
            for _, row in df_tasks.iterrows()
        }
        df_display.insert(
            2,
            '用户编号',
            df_display['任务ID'].apply(lambda tid: username_map.get(tid, "N/A"))
        )

        # 格式化显示 - 进度显示为百分比和已完成数/总数
        def format_progress(row):
            total = row['总数']
            processed = row['已处理']
            success = row['成功数']
            progress_pct = row['进度']
            return f"{progress_pct:.1f}% ({success}/{total})"
        
        df_display['进度'] = df_display.apply(format_progress, axis=1)
        df_display['创建时间'] = pd.to_datetime(df_display['创建时间']).dt.strftime('%Y-%m-%d %H:%M')
        st.caption("💡 以下以表格形式展示任务列表，单选查看详情")
        st.caption("👉 表格默认显示 5 行，可滚动查看更多任务")

        current_selected = st.session_state.get('selected_task_id')

        valid_task_ids = set(df_display['任务ID'])
        if current_selected and current_selected not in valid_task_ids:
            st.session_state.pop('selected_task_id', None)
            current_selected = None

        df_table = df_display.copy()
        df_table.insert(0, '查看详情', df_table['任务ID'].apply(lambda tid: tid == current_selected))
        
        # 添加继续执行按钮列（仅限未完成任务）
        def can_continue_task(status):
            return status in ['pending', 'processing', 'paused', 'failed']
        
        df_table.insert(1, '继续执行', df_table['状态'].apply(lambda s: can_continue_task(s)))
        
        visible_rows = min(len(df_table), 5)
        header_height = 38
        row_height = 44
        table_height = header_height + max(1, visible_rows) * row_height

        if 'task_table_prev' not in st.session_state:
            st.session_state['task_table_prev'] = df_table.copy()

        editor_result = st.data_editor(
            df_table,
            hide_index=True,
            use_container_width=True,
            height=table_height,
            column_config={
                '查看详情': st.column_config.CheckboxColumn(
                    '查看详情',
                    help='勾选后加载该任务详情',
                    default=False
                ),
                '继续执行': st.column_config.CheckboxColumn(
                    '继续执行',
                    help='勾选后继续执行该任务（仅限未完成任务）',
                    default=False
                )
            },
            disabled=[col for col in df_table.columns if col not in ['查看详情', '继续执行']],
            key='task_table_editor'
        )

        prev_table = st.session_state.get('task_table_prev')
        if prev_table is None or list(prev_table['任务ID']) != list(editor_result['任务ID']):
            st.session_state['task_table_prev'] = editor_result.copy()
        else:
            # 处理查看详情勾选
            diff_mask = editor_result['查看详情'] != prev_table['查看详情']
            if diff_mask.any():
                last_changed_idx = diff_mask[diff_mask].index[-1]
                selected_task_id = editor_result.iloc[last_changed_idx]['任务ID']
                if editor_result.iloc[last_changed_idx]['查看详情']:
                    st.session_state['selected_task_id'] = selected_task_id
                else:
                    if st.session_state.get('selected_task_id') == selected_task_id:
                        st.session_state.pop('selected_task_id', None)
                st.session_state['task_table_prev'] = editor_result.copy()
                st.rerun()
            
            # 处理继续执行勾选
            continue_mask = editor_result['继续执行'] != prev_table['继续执行']
            if continue_mask.any():
                last_changed_idx = continue_mask[continue_mask].index[-1]
                selected_task_id = editor_result.iloc[last_changed_idx]['任务ID']
                if editor_result.iloc[last_changed_idx]['继续执行']:
                    try:
                        with st.spinner(f"正在继续执行任务 {selected_task_id}..."):
                            api_client.continue_task(selected_task_id)
                        st.success(f"✅ 任务 {selected_task_id} 已继续执行")
                        # 取消勾选
                        editor_result.at[last_changed_idx, '继续执行'] = False
                        st.session_state['task_table_prev'] = editor_result.copy()
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ 继续执行任务失败: {str(e)}")
                        # 取消勾选
                        editor_result.at[last_changed_idx, '继续执行'] = False
                        st.session_state['task_table_prev'] = editor_result.copy()

        st.markdown("---")
        current_selected = st.session_state.get('selected_task_id')
        if current_selected:
            with st.expander(f"📊 任务详情: {current_selected}", expanded=True):
                show_result_detail(current_selected)
        else:
            st.info("在表格中勾选“查看详情”即可展开任务详情")
    else:
        st.info("暂无任务记录")


# ==================== Tab 2: 单个音频分析 ====================

with tab2:
    st.header("🎵 单个音频分析")
    
    audio_url = st.text_input("音频 URL 或本地路径", placeholder="https://example.com/audio.wav")
    
    if st.button("开始分析", type="primary"):
        if not audio_url:
            st.error("请输入音频 URL")
            st.stop()
        
        if not validate_uri(audio_url):
            st.error("请输入有效的 http/https URL")
            st.stop()
        
        # 前端幂等性检查
        request_key = f"single_audio_{audio_url}"
        if request_key in st.session_state.submitted_requests:
            st.warning("⚠️ 该请求正在处理中，请勿重复提交！")
            st.stop()
        
        try:
            with st.spinner("正在创建分析任务..."):
                # 记录请求
                st.session_state.submitted_requests.add(request_key)
                
                try:
                    # 调用API创建任务
                    task_response = api_client.create_task(
                        task_name=f"单个音频: {audio_url}",
                        audio_urls=[audio_url]
                    )
                    
                    task_id = task_response['task_id']
                    st.success(f"✅ 任务已创建！任务 ID: {task_id}")
                    st.info("正在处理中，请稍候...")
                    
                    # 轮询等待任务完成
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    max_wait = 300  # 最多等待5分钟
                    wait_count = 0
                    
                    while wait_count < max_wait:
                        try:
                            task_info = api_client.get_task(task_id)
                            status = task_info.get('status', '')
                            progress = task_info.get('progress', 0)
                            
                            progress_bar.progress(progress / 100)
                            status_text.text(f"状态: {status} | 进度: {progress:.1f}%")
                            
                            if status in ['completed', 'failed']:
                                break
                            
                            time.sleep(2)
                            wait_count += 2
                            
                        except Exception as e:
                            st.error(f"❌ 获取任务状态失败: {str(e)}")
                            # 记录详细错误到后端日志
                            from src.logger.logger import business_logger
                            business_logger.log_error('app', 'get_task_status', e, task_id=task_id)
                            break
                    
                    if wait_count >= max_wait:
                        st.warning("⚠️ 等待超时，请切换到仪表盘查看任务状态")
                    else:
                        # 获取结果
                        results_response = api_client.get_task_results(task_id)
                        results = results_response.get('results', [])
                        
                        if results:
                            result = results[0]
                            
                            st.subheader("📝 识别结果")
                            st.text_area("完整文本", result.get('full_text', ''), height=200)
                            
                            st.subheader("📊 分析结果")
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                st.metric("音频时长", f"{result.get('duration', 0):.1f}秒")
                                st.metric("处理时间", f"{result.get('processing_time', 0):.1f}秒")
                            
                            with col2:
                                st.metric("实时因子", f"{result.get('realtime_factor', 0):.2f}x")
                                st.metric("置信度", f"{result.get('confidence', 0):.2%}")
                            
                            # LLM 分析
                            if result.get('dialogue_summary'):
                                st.subheader("🤖 AI 分析")
                                st.write("**对话摘要**:", result.get('dialogue_summary'))
                                st.write("**是否包含辱骂**:", "是 ⚠️" if result.get('has_abusive_language') else "否 ✅")
                        else:
                            st.info("暂无结果数据，请切换到仪表盘查看")
                
                except Exception as e:
                    st.error(f"❌ 分析失败: {str(e)}")
                    # 记录详细错误到后端日志
                    import traceback
                    from src.logger.logger import business_logger
                    business_logger.log_error('app', 'single_audio_analysis', e)

        finally:
            # 清理请求记录
            if request_key in st.session_state.submitted_requests:
                st.session_state.submitted_requests.discard(request_key)


# ==================== Tab 3: 批量处理 ====================

with tab3:
    st.header("📁 批量处理")
    
    # 文件上传
    uploaded_file = st.file_uploader("上传 CSV/Excel 文件", type=['csv', 'xlsx', 'xls'])
    
    if uploaded_file:
        # 保存文件
        upload_dir = config.upload_dir
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, uploaded_file.name)
        
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        st.success(f"✅ 文件上传成功: {uploaded_file.name}")
        
        # 使用API上传并处理
        task_name = st.text_input("任务名称", value=f"批量任务_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        
        if st.button("开始批处理", type="primary"):
            # 前端幂等性检查
            request_key = f"batch_{file_path}_{task_name}"
            if request_key in st.session_state.submitted_requests:
                st.warning("️ 该批处理请求正在处理中，请勿重复提交！")
                st.stop()
            
            try:
                with st.spinner("正在上传并启动批处理..."):
                    # 记录请求
                    st.session_state.submitted_requests.add(request_key)
                    
                    try:
                        # 调用API上传并处理
                        task_response = api_client.upload_and_process(
                            file_path=file_path,
                            task_name=task_name
                        )
                        
                        task_id = task_response['task_id']
                        total_count = task_response.get('total_count', 0)
                        
                        st.success(f"✅ 批处理已启动！任务 ID: {task_id}")
                        st.info(f"共 {total_count} 个音频，正在后台处理中...")
                        
                        # 显示进度提示
                        st.markdown("---")
                        st.markdown("**提示**: 切换到「仪表盘」查看实时进度")
                        
                        # 创建快速跳转按钮
                        if st.button(" 跳转到仪表盘", key="goto_dashboard"):
                            st.session_state['current_tab'] = 0
                            st.rerun()
                    
                    except Exception as e:
                        st.error(f"❌ 启动失败: {str(e)}")
                        # 记录详细错误到后端日志
                        import traceback
                        from src.logger.logger import business_logger
                        business_logger.log_error('app', 'batch_process_start', e)
            
            finally:
                # 清理请求记录
                if request_key in st.session_state.submitted_requests:
                    st.session_state.submitted_requests.discard(request_key)


# ==================== Tab 4: 系统配置 ====================

with tab4:
    st.header(" 系统配置管理")
    
    # 配置分类选择
    category = st.selectbox(
        "选择配置分类",
        ["全部", "asr", "llm", "batch", "system"],
        index=0
    )
    
    # 查询配置
    try:
        category_filter = None if category == "全部" else category
        configs_response = fetch_configs_cached(st.session_state.get('session_token'), category_filter)
        configs = configs_response.get('configs', [])
    except Exception as e:
        st.error(f"❌ 获取配置失败: {str(e)}")
        # 记录详细错误到后端日志
        from src.logger.logger import business_logger
        business_logger.log_error('app', 'list_configs', e, category=category)
        configs = []
    
    if configs:
        # 按分类分组显示
        current_category = None
        for config_item in configs:
            if config_item['category'] != current_category:
                current_category = config_item['category']
                st.subheader(f" {current_category.upper()} 配置")
            
            # 根据类型显示不同的输入控件
            col1, col2, col3 = st.columns([2, 2, 1])
            
            with col1:
                st.write(f"**{config_item['config_key']}**")
                if config_item['description']:
                    st.caption(config_item['description'])
            
            with col2:
                config_key = config_item['config_key']
                config_type = config_item['config_type']
                current_value = config_item['config_value']
                is_editable = config_item['is_editable']
                
                if is_editable:
                    if config_type == 'bool':
                        new_value = st.checkbox(
                            "值",
                            value=current_value.lower() in ('true', '1', 'yes'),
                            key=f"config_{config_key}"
                        )
                    elif config_type == 'int':
                        new_value = st.number_input(
                            "值",
                            value=int(current_value),
                            key=f"config_{config_key}"
                        )
                    elif config_type == 'float':
                        new_value = st.number_input(
                            "值",
                            value=float(current_value),
                            step=0.1,
                            key=f"config_{config_key}"
                        )
                    else:
                        new_value = st.text_input(
                            "值",
                            value=current_value,
                            key=f"config_{config_key}"
                        )
                    
                    # 保存按钮
                    if st.button(" 保存", key=f"save_{config_key}"):
                        try:
                            api_client.update_config(
                                config_key=config_key,
                                value=str(new_value),
                                config_type=config_type
                            )
                            fetch_configs_cached.clear()
                            st.success(f" 配置 {config_key} 已更新")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ 更新失败: {str(e)}")
                            # 记录详细错误到后端日志
                            from src.logger.logger import business_logger
                            business_logger.log_error('app', 'update_config', e, config_key=config_key, value=value)
                else:
                    st.text_input("值", value=current_value, disabled=True, key=f"config_{config_key}")
                    st.caption(" 此配置不可编辑")
            
            with col3:
                st.write(f"**类型**: {config_type}")
    else:
        st.info("暂无配置数据")
    
    st.markdown("---")
    st.caption("💡 提示: 修改配置后，部分配置可能需要重启应用才能生效")
    
    # 用户管理（仅管理员可见）
    if st.session_state.get('user_role') == 'admin':
        st.markdown("---")
        st.subheader(" 用户管理")
        
        # 用户查询
        col1, col2 = st.columns([3, 1])
        with col1:
            user_search = st.text_input("🔍 搜索用户", placeholder="输入用户名或邮箱", key="user_search")
        with col2:
            role_filter = st.selectbox("角色筛选", ["全部", "admin", "user"], key="role_filter")
        
        # 获取用户列表
        users = []
        try:
            users_response = fetch_users_cached(st.session_state.get('session_token'))
            users = users_response.get('users', [])
            
            # 应用筛选
            if user_search:
                users = [u for u in users if user_search.lower() in u.get('username', '').lower() or user_search.lower() in u.get('email', '').lower()]
            if role_filter != "全部":
                users = [u for u in users if u.get('role') == role_filter]
            
            if users:
                df_users = pd.DataFrame(users)
                # 添加激活状态列的中文显示
                df_users['激活状态'] = df_users['is_active'].apply(lambda x: '✅ 已激活' if x else '❌ 未激活')
                st.dataframe(
                    df_users[['username', 'role', 'email', '激活状态', 'created_at']],
                    use_container_width=True,
                    hide_index=True
                )
                
                # 用户激活管理
                st.markdown("### 🔐 用户激活管理")
                for user in users:
                    col1, col2, col3 = st.columns([3, 2, 2])
                    with col1:
                        st.write(f"**{user['username']}** ({user['role']})")
                    with col2:
                        current_status = "已激活" if user['is_active'] else "未激活"
                        st.write(f"当前状态: {current_status}")
                    with col3:
                        if user['role'] != 'admin':  # 不允许禁用admin用户
                            if user['is_active']:
                                if st.button(f"禁用 {user['username']}", key=f"disable_{user['username']}"):
                                    try:
                                        api_client.set_user_active(user['username'], False)
                                        st.success(f"已禁用用户 {user['username']}")
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"禁用失败: {str(e)}")
                            else:
                                if st.button(f"启用 {user['username']}", key=f"enable_{user['username']}"):
                                    try:
                                        api_client.set_user_active(user['username'], True)
                                        st.success(f"已启用用户 {user['username']}")
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"启用失败: {str(e)}")
                    st.markdown("---")
            else:
                st.info("暂无用户数据")
        except Exception as e:
            st.error(f"❌ 获取用户列表失败: {str(e)}")
            # 记录详细错误到后端日志
            from src.logger.logger import business_logger
            business_logger.log_error('app', 'list_users', e)
        
        st.markdown("---")
        
        # 新增用户
        with st.expander("➕ 新增用户", expanded=False):
            with st.form("add_user_form"):
                new_username = st.text_input("用户名", key="new_username")
                new_password = st.text_input("密码", type="password", key="new_password")
                new_role = st.selectbox("角色", ["user", "admin"], key="new_role")
                new_email = st.text_input("邮箱（可选）", key="new_email")
                
                if st.form_submit_button("创建用户", type="primary"):
                    if not new_username or not new_password:
                        st.error("请输入用户名和密码")
                    else:
                        try:
                            api_client.create_user(
                                username=new_username,
                                password=new_password,
                                role=new_role,
                                email=new_email
                            )
                            fetch_users_cached.clear()
                            st.success(f"✅ 用户 {new_username} 创建成功")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ 创建用户失败: {str(e)}")
                            # 记录详细错误到后端日志
                            from src.logger.logger import business_logger
                            business_logger.log_error('app', 'create_user', e, username=new_username)
        
        # 修改/删除用户
        with st.expander("✏️ 修改/删除用户", expanded=False):
            with st.form("modify_user_form"):
                if users:
                    user_options = {u['username']: u for u in users}
                    target_username = st.selectbox("选择用户", list(user_options.keys()), key="target_username")
                    
                    if target_username:
                        user_info = user_options[target_username]
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            modify_role = st.selectbox("修改角色", ["user", "admin"], index=["user", "admin"].index(user_info.get('role', 'user')), key="modify_role")
                        with col2:
                            modify_active = st.selectbox("状态", ["激活", "注销"], index=0 if user_info.get('is_active') else 1, key="modify_active")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.form_submit_button("保存修改", type="primary"):
                                try:
                                    api_client.update_user(
                                        username=target_username,
                                        role=modify_role,
                                        is_active=(modify_active == "激活")
                                    )
                                    fetch_users_cached.clear()
                                    st.success(f"✅ 用户 {target_username} 修改成功")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"❌ 修改失败: {str(e)}")
                                    # 记录详细错误到后端日志
                                    from src.logger.logger import business_logger
                                    business_logger.log_error('app', 'update_user', e, username=target_username)
                        
                        with col2:
                            if st.form_submit_button("删除用户", type="secondary"):
                                try:
                                    api_client.delete_user(target_username)
                                    fetch_users_cached.clear()
                                    st.success(f"✅ 用户 {target_username} 已删除")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"❌ 删除失败: {str(e)}")
                                    # 记录详细错误到后端日志
                                    from src.logger.logger import business_logger
                                    business_logger.log_error('app', 'delete_user', e, username=target_username)
                else:
                    st.info("暂无用户可供修改")

# ==================== 页脚 ====================

st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: gray;'>
        <p>语音识别分析系统 v3.0 | Powered by Faster-Whisper & Streamlit</p>
    </div>
    """,
    unsafe_allow_html=True
)