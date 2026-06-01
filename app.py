"""
Streamlit Web UI 主应用
语音识别分析系统 v3.0
"""

import json
import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components
import time
from datetime import datetime

from compat_layer import db_manager
from config import config
from login import require_auth, show_logout_button, is_admin, api_client

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
# batch_processor, csv_parser, report_gen, hardware_info 都通过API调用获取


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


@st.cache_data(show_spinner=False)
def get_customer_code(task_id: str) -> str:
    """
    推断任务的客户编码
    - 单个音频：直接使用音频URL
    - 批量导入：优先从原始Excel数据中取客户编号/手机号/身份证号等唯一标识
    """

    try:
        resp = api_client.get_task_results(task_id, limit=1)
        results = resp.get('results', [])
    except Exception:
        return "N/A"

    if not results:
        return "N/A"

    result = results[0]
    origin_data = result.get('origin_data') or {}
    task_type = origin_data.get('type')

    # 单个音频：直接返回音频URL
    if task_type == 'single_audio':
        return origin_data.get('audio_url') or result.get('audio_url') or "N/A"

    # 批量导入：从excel_data/extra_data中提取客户唯一编号
    excel_data = origin_data.get('excel_data') or result.get('extra_data') or {}
    priority_keywords = [
        "客户编码", "客户编号", "customer", "customer_id", "客户id", "客户ID",
        "手机号", "手机", "mobile", "phone", "联系电话", "电话",
        "身份证", "身份证号", "证件号", "id_number"
    ]

    for keyword in priority_keywords:
        for col, val in excel_data.items():
            if keyword.lower() in str(col).lower():
                candidate = str(val).strip()
                if candidate:
                    return candidate

    # 兜底：返回excel_data中的第一个非空字段，或音频URL
    for val in excel_data.values():
        candidate = str(val).strip()
        if candidate:
            return candidate

    return result.get('audio_url') or "N/A"


# ==================== 结果详情展示函数 ====================

def show_result_detail(task_id: str):
    """显示任务结果详情（按任务类型区分）"""
    
    # 获取任务及结果
    task_data = db_manager.get_task_with_results(task_id)
    
    if not task_data:
        st.error("❌ 任务不存在")
        return
    
    results = task_data.get('results', [])
    
    if not results:
        st.info("暂无结果数据")
        return
    
    # 判断任务类型：单个音频 vs Excel导入
    is_single_audio = len(results) == 1
    
    if is_single_audio:
        # 单个音频任务
        _show_single_audio_detail(task_data, results[0])
    else:
        # Excel导入任务
        _show_excel_import_detail(task_data, results)


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
        {"指标": "音频时长", "值": f"{result.get('duration', 0):.1f} 秒"},
        {"指标": "处理时间", "值": f"{result.get('processing_time', 0):.1f} 秒"},
        {"指标": "实时因子", "值": f"{result.get('realtime_factor', 0):.2f}x"},
        {"指标": "置信度", "值": f"{result.get('confidence', 0):.2%}"},
        {"指标": "语言", "值": result.get('language', 'zh')},
        {"指标": "是否包含辱骂", "值": "是 ⚠️" if result.get('has_abusive_language') else "否 ✅"},
    ]
    
    df_analysis = pd.DataFrame(analysis_data)
    st.dataframe(df_analysis, use_container_width=True, hide_index=True)
    
    # AI对话摘要
    if result.get('dialogue_summary'):
        st.markdown("**对话摘要**:")
        st.info(result.get('dialogue_summary'))
        
        abusive_words = result.get('abusive_words', [])
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
        with st.expander("📍 查看原始输入数据", expanded=False):
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
        
        # 添加其他信息
        row['音频URL'] = result.get('audio_url', '')
        row['时长(秒)'] = result.get('duration', 0)
        row['置信度'] = f"{result.get('confidence', 0):.2%}"
        row['状态'] = result.get('status', '')
        
        data_list.append(row)
    
    df_results = pd.DataFrame(data_list)
    st.dataframe(df_results, use_container_width=True, hide_index=True)
    
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
    hardware_info = api_client.get_hardware_info()
    hw = hardware_info['hardware']
    rec = hardware_info['recommended']
    
    st.sidebar.text(f"CPU: {hw['cpu_cores']} 核")
    st.sidebar.text(f"GPU: {hw['gpu_type']}")
    
    if hw.get('gpu_name'):
        st.sidebar.text(f"型号: {hw['gpu_name']}")
    
    if hw.get('gpu_memory_gb', 0) > 0:
        st.sidebar.text(f"显存: {hw['gpu_memory_gb']:.1f} GB")
    
    # 推荐配置
    st.sidebar.markdown("### 💡 推荐配置")
    st.sidebar.success(rec['description'])
    st.sidebar.text(f"模型: {rec['model_size']}")
    st.sidebar.text(f"Beam Size: {rec['beam_size']}")
    st.sidebar.text(f"并发数: {rec['max_workers']}")
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
tab_names = ["📊 仪表盘", "🎵 单个音频", "📁 批量处理", "📈 统计报表", "⚙️ 系统配置"]
if 'current_tab' not in st.session_state:
    st.session_state.current_tab = 0

tab1, tab2, tab3, tab4, tab5 = st.tabs(tab_names)


# ==================== Tab 1: 仪表盘 ====================

with tab1:
    st.header("📊 系统概览")
    
    # 查询任务统计（每次切换到Tab都会重新执行）
    try:
        tasks_response = api_client.list_tasks(limit=100)
        tasks = tasks_response.get('tasks', [])
    except Exception as e:
        st.error(f"❌ 获取任务列表失败: {str(e)}")
        tasks = []
    
    total_tasks = len(tasks)
    running_tasks = sum(1 for t in tasks if t['status'] == 'running')
    completed_tasks = sum(1 for t in tasks if t['status'] == 'completed')
    failed_tasks = sum(1 for t in tasks if t['status'] == 'failed')
    
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
    
    # 最近任务列表
    st.subheader("📋 最近任务")
    
    if tasks:
        df_tasks = pd.DataFrame(tasks)

        # 支持按任务ID筛选
        task_filter = st.text_input("🔍 按任务编码筛选", placeholder="输入任务ID的一部分即可", key="task_code_filter")
        if task_filter:
            df_tasks = df_tasks[df_tasks['task_id'].str.contains(task_filter, case=False, na=False)]

        # 格式化显示
        # 重命名列
        df_display = df_tasks[['task_id', 'task_name', 'status', 'total_count', 'progress', 'created_at']].copy()
        df_display.rename(columns={
            'task_id': '任务ID',
            'task_name': '任务名称',
            'status': '状态',
            'total_count': '总数',
            'progress': '进度',
            'created_at': '创建时间'
        }, inplace=True)

        # 客户编码列：紧挨任务ID（缓存加速）
        customer_code_map = {row['任务ID']: get_customer_code(row['任务ID']) for _, row in df_display.iterrows()}
        df_display.insert(1, '客户编码', df_display['任务ID'].apply(lambda tid: customer_code_map.get(tid, "N/A")))

        # 格式化显示
        df_display['进度'] = df_display['进度'].apply(lambda x: f"{x:.1f}%")
        df_display['创建时间'] = pd.to_datetime(df_display['创建时间']).dt.strftime('%Y-%m-%d %H:%M')
        # 详情选择列：使用 data_editor 的复选框，不需要跳转
        df_display.insert(0, '查看详情', False)

        edited = st.data_editor(
            df_display[['查看详情', '任务ID', '客户编码', '任务名称', '状态', '总数', '进度', '创建时间']],
            use_container_width=True,
            hide_index=True,
            column_config={
                "查看详情": st.column_config.CheckboxColumn("详情", width="small"),
                "任务ID": st.column_config.TextColumn("任务ID", width="medium"),
                "客户编码": st.column_config.TextColumn("客户编码", width="medium"),
                "任务名称": st.column_config.TextColumn("任务名称", width="large"),
                "状态": st.column_config.TextColumn("状态", width="small"),
                "总数": st.column_config.NumberColumn("总数", width="small"),
                "进度": st.column_config.TextColumn("进度", width="small"),
                "创建时间": st.column_config.TextColumn("创建时间", width="medium")
            },
            key="task_data_editor"
        )

        selected_rows = edited[edited['查看详情']]

        st.markdown("---")
        if not selected_rows.empty:
            # 默认取首条勾选的任务
            task_id = selected_rows.iloc[0]['任务ID']
            st.session_state['selected_task_id'] = task_id
            with st.expander(f"📊 任务详情: {task_id}", expanded=True):
                show_result_detail(task_id)
        else:
            st.session_state['selected_task_id'] = None
            st.info("勾选某行的「详情」以查看任务详情")
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
                        task_name=f"单个音频: {audio_url[:50]}...",
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
                    import traceback
                    st.error(traceback.format_exc())

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
                        import traceback
                        st.error(traceback.format_exc())
            
            finally:
                # 清理请求记录
                if request_key in st.session_state.submitted_requests:
                    st.session_state.submitted_requests.discard(request_key)


# ==================== Tab 4: 统计报表 ====================

with tab4:
    st.header("📈 统计报表")
    
    # 选择任务
    try:
        tasks_response = api_client.list_tasks(status='completed', limit=50)
        tasks = tasks_response.get('tasks', [])
    except Exception as e:
        st.error(f"❌ 获取任务列表失败: {str(e)}")
        tasks = []
    
    if tasks:
        task_options = {t['task_id']: t['task_name'] for t in tasks}
        selected_task_id = st.selectbox(
            "选择任务",
            options=list(task_options.keys()),
            format_func=lambda x: task_options[x]
        )
        
        if selected_task_id:
            # 生成报表
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("生成汇总报表"):
                    with st.spinner("生成中..."):
                        try:
                            report = api_client.get_task_summary(selected_task_id)
                            st.json(report)
                        except Exception as e:
                            st.error(f" 生成报表失败: {str(e)}")
            
            with col2:
                if st.button("生成情绪报表"):
                    with st.spinner("生成中..."):
                        try:
                            report = api_client.get_emotion_report(selected_task_id)
                            
                            # 可视化情绪分布
                            if 'emotion_distribution' in report:
                                emotions = report['emotion_distribution']
                                
                                if emotions:
                                    df_emotion = pd.DataFrame([
                                        {'情绪': k, '数量': v['count'], '百分比': v['percentage']}
                                        for k, v in emotions.items()
                                    ])
                                    
                                    fig = px.pie(
                                        df_emotion,
                                        values='数量',
                                        names='情绪',
                                        title='情绪分布'
                                    )
                                    st.plotly_chart(fig, use_container_width=True)
                        except Exception as e:
                            st.error(f"❌ 生成报表失败: {str(e)}")
            
            # 性能报表
            if st.button("生成性能报表"):
                with st.spinner("生成中..."):
                    try:
                        report = api_client.get_performance_report(selected_task_id)
                        
                        if 'processing_time_stats' in report:
                            stats = report['processing_time_stats']
                            
                            fig = go.Figure()
                            fig.add_trace(go.Bar(
                                x=['最小值', '平均值', '最大值', 'P90', 'P95'],
                                y=[stats['min'], stats['avg'], stats['max'], stats['p90'], stats['p95']],
                                name='处理时间（秒）'
                            ))
                            
                            fig.update_layout(title='处理时间统计')
                            st.plotly_chart(fig, use_container_width=True)
                    except Exception as e:
                        st.error(f"❌ 生成报表失败: {str(e)}")
    
    else:
        st.info("暂无已完成的任务")


# ==================== Tab 5: 系统配置 ====================

with tab5:
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
        configs_response = api_client.list_configs(category_filter)
        configs = configs_response.get('configs', [])
    except Exception as e:
        st.error(f"❌ 获取配置失败: {str(e)}")
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
                            st.success(f" 配置 {config_key} 已更新")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ 更新失败: {str(e)}")
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
    if is_admin():
        st.markdown("---")
        st.subheader(" 用户管理")
        
        # 显示用户列表
        try:
            users_response = api_client.list_users()
            users = users_response.get('users', [])
            
            if users:
                df_users = pd.DataFrame(users)
                st.dataframe(
                    df_users[['username', 'role', 'email', 'is_active', 'created_at']],
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("暂无用户数据")
        except Exception as e:
            st.error(f"❌ 获取用户列表失败: {str(e)}")

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
