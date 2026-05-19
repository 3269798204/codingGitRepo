"""
Streamlit Web UI 主应用
语音识别分析系统 v3.0
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import json
import os
import time

from config import config
from hardware_detector import get_detector
from database import db_manager
from batch_processor import BatchProcessor
from csv_parser import CSVParser
from report_generator import ReportGenerator
from middleware.idempotency import idempotency_manager


# ==================== 页面配置 ====================

st.set_page_config(
    page_title="语音识别分析系统 v3.0",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== 初始化组件 ====================

# 初始化 session state 用于前端去重
if 'submitted_requests' not in st.session_state:
    st.session_state.submitted_requests = set()

@st.cache_resource
def get_batch_processor():
    return BatchProcessor()

@st.cache_resource
def get_csv_parser():
    return CSVParser()

@st.cache_resource
def get_report_generator():
    return ReportGenerator()

@st.cache_resource
def get_hardware_info():
    detector = get_detector()
    return detector.to_dict()


batch_processor = get_batch_processor()
csv_parser = get_csv_parser()
report_gen = get_report_generator()
hardware_info = get_hardware_info()


# ==================== 侧边栏配置 ====================

st.sidebar.title("⚙️ 系统配置")

# 硬件信息显示
st.sidebar.markdown("### 🖥️ 硬件信息")
hw = hardware_info['hardware']
st.sidebar.text(f"CPU: {hw['cpu_cores']} 核")
st.sidebar.text(f"GPU: {hw['gpu_type']}")

if hw.get('gpu_name'):
    st.sidebar.text(f"型号: {hw['gpu_name']}")

if hw.get('gpu_memory_gb', 0) > 0:
    st.sidebar.text(f"显存: {hw['gpu_memory_gb']:.1f} GB")

# 推荐配置
rec = hardware_info['recommended']
st.sidebar.markdown("### 💡 推荐配置")
st.sidebar.success(rec['description'])
st.sidebar.text(f"模型: {rec['model_size']}")
st.sidebar.text(f"Beam Size: {rec['beam_size']}")
st.sidebar.text(f"并发数: {rec['max_workers']}")

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
tab1, tab2, tab3, tab4 = st.tabs(["📊 仪表盘", "🎵 单个音频", "📁 批量处理", "📈 统计报表"])


# ==================== Tab 1: 仪表盘 ====================

with tab1:
    st.header("📊 系统概览")
    
    # 查询任务统计
    tasks = db_manager.list_tasks(limit=100)
    
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
        
        # 格式化显示
        # 重命名列
        df_display = df_tasks[['task_name', 'status', 'total_count', 'progress', 'created_at']].copy()
        df_display.rename(columns={
            'task_name': '任务名称',
            'status': '状态',
            'total_count': '总数',
            'progress': '进度',
            'created_at': '创建时间'
        }, inplace=True)

        # 格式化显示
        df_display['进度'] = df_display['进度'].apply(lambda x: f"{x:.1f}%")
        df_display['创建时间'] = pd.to_datetime(df_display['创建时间']).dt.strftime('%Y-%m-%d %H:%M')

        st.dataframe(
            df_display[['任务名称', '状态', '总数', '进度', '创建时间']],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("暂无任务记录")


# ==================== Tab 2: 单个音频分析 ====================

with tab2:
    st.header("🎵 单个音频分析")
    
    audio_url = st.text_input("音频 URL 或本地路径", placeholder="https://example.com/audio.wav")
    
    if st.button("开始分析", type="primary"):
        if not audio_url:
            st.error("请输入音频 URL")
            # 前端幂等性检查
            request_key = f"single_audio_{audio_url}"
            if request_key in st.session_state.submitted_requests:
                st.warning("⚠️ 该请求正在处理中，请勿重复提交！")
                st.stop()
            
            try:
                with st.spinner("正在分析..."):
                    # 记录请求
                    st.session_state.submitted_requests.add(request_key)
                try:
                    # 调用批处理器处理单个音频
                    task_id = batch_processor.start_batch(
                        task_name=f"单个音频: {audio_url}",
                        audio_urls=[audio_url]
                    )
                    
                    st.success(f"✅ 分析完成！任务 ID: {task_id}")
                    
                    # 显示结果
                    results = db_manager.get_task_results(task_id)
                    
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
                
            
            finally:
                # 清理请求记录
                if request_key in st.session_state.submitted_requests:
                    st.session_state.submitted_requests.discard(request_key)
                except Exception as e:
                    st.error(f"❌ 分析失败: {str(e)}")


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
        
        # 预览文件
        st.subheader("📋 文件预览")
        
        try:
            preview = csv_parser.get_file_preview(file_path)
            
            st.write(f"**总行数**: {preview['total_rows']}")
            st.write(f"**URL 列**: {preview['url_column']}")
            
            if preview['preview_data']:
                df_preview = pd.DataFrame(preview['preview_data'])
                st.dataframe(df_preview, use_container_width=True)
            
            # 开始批处理
            task_name = st.text_input("任务名称", value=f"批量任务_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            
            if st.button("开始批处理", type="primary"):
                with st.spinner("正在启动批处理..."):
                    try:
                        # 提取音频列表
                        audio_list = csv_parser.extract_audio_list(file_path)
                        
                        urls = [item['url'] for item in audio_list]
                        extra_data = [item['extra_data'] for item in audio_list]
                        
                        # 启动批处理（后台任务）
                        task_id = batch_processor.start_batch(
                            task_name=task_name,
                            audio_urls=urls,
                            extra_data_list=extra_data
                        )
                        
                        st.success(f"✅ 批处理已启动！任务 ID: {task_id}")
                        st.info(f"共 {len(urls)} 个音频，预计需要 {len(urls) * 2 / 60:.1f} 分钟")
                        
                        # 自动刷新进度
                        st.markdown("**提示**: 切换到「仪表盘」查看实时进度")
                    
                    except Exception as e:
                        st.error(f"❌ 启动失败: {str(e)}")
        
        except Exception as e:
            st.error(f"❌ 解析失败: {str(e)}")


# ==================== Tab 4: 统计报表 ====================

with tab4:
    st.header("📈 统计报表")
    
    # 选择任务
    tasks = db_manager.list_tasks(status='completed', limit=50)
    
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
                        report = report_gen.generate_task_summary(selected_task_id)
                        st.json(report)
            
            with col2:
                if st.button("生成情绪报表"):
                    with st.spinner("生成中..."):
                        report = report_gen.generate_emotion_report(selected_task_id)
                        
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
            
            # 性能报表
            if st.button("生成性能报表"):
                with st.spinner("生成中..."):
                    report = report_gen.generate_performance_report(selected_task_id)
                    
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
    
    else:
        st.info("暂无已完成的任务")


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
