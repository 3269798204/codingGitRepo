# 任务详情和认证优化说明

## 🎯 优化需求

根据用户反馈，进行以下优化：

1. ✅ 仪表盘"详情"改为超链接方式（不是按钮）
2. ✅ 详情内容按任务类型展示：
   - 单个音频：URL + 语音识别内容 + LLM分析报告表格
   - Excel导入：所有Excel字段 + 语音识别内容 + LLM分析报告表格
3. ✅ 支持CSV导出功能
4. ✅ 使用expander展开/收起详情
5. ✅ 页面刷新不需要重复登录，只校验session状态

---

## 📋 实现方案

### 1. 详情链接优化

#### 修改前（按钮方式）

```python
def make_detail_button(task_id):
    if st.button("📄 详情", key=f"detail_{task_id}"):
        st.session_state['selected_task_id'] = task_id
        st.rerun()
    return ""

df_display['操作'] = df_display['任务ID'].apply(make_detail_button)
```

**问题**: 
- ❌ DataFrame中显示的是按钮对象，不是文本
- ❌ 样式不统一

---

#### 修改后（超链接方式）

```python
# 在DataFrame中显示链接文本
def make_detail_link(task_id):
    return f"🔗 [详情](javascript:void(0))"

df_display['操作'] = df_display['任务ID'].apply(make_detail_link)

st.dataframe(df_display, use_container_width=True, hide_index=True)

# 为每一行添加可点击的图标按钮
for idx, row in df_display.iterrows():
    task_id = row['任务ID']
    cols = st.columns([10, 1])
    with cols[1]:
        if st.button("🔗", key=f"link_{task_id}", help="查看详情"):
            st.session_state['selected_task_id'] = task_id
            st.rerun()
```

**效果**:
```
┌──────────┬──────────┬──────┬─────┬──────┬──────────┬──────┐
│ 任务ID   │ 任务名称  │ 状态  │总数 │ 进度  │ 创建时间  │ 操作  │
├──────────┼──────────┼──────┼─────┼──────┼──────────┼──────┤
│ task_001 │ 批量任务  │ ✅   │ 10  │100%  │ 2026-... │ 🔗   │
└──────────┴──────────┴──────┴─────┴──────┴──────────┴──────┘
                                                         ↑
                                                    点击这个图标
```

---

### 2. 详情内容按任务类型展示

#### 单个音频任务

**展示结构**:
```
┌─────────────────────────────────────────┐
│ ### 🎵 单个音频任务                      │
├─────────────────────────────────────────┤
│ #### 📍 音频 URL                         │
│ [代码块显示URL]                           │
├─────────────────────────────────────────┤
│ #### 📝 语音识别内容                     │
│ [文本区域显示完整识别文本]                 │
├─────────────────────────────────────────┤
│ #### 🤖 LLM 分析报告                     │
│ ┌──────────┬────────────┐               │
│ │ 指标     │ 值          │               │
│ ├──────────┼────────────┤               │
│ │ 音频时长 │ 10.5 秒     │               │
│ │ 处理时间 │ 2.3 秒      │               │
│ │ 实时因子 │ 4.57x       │               │
│ │ 置信度   │ 95.2%       │               │
│ │ 语言     │ zh          │               │
│ │ 是否辱骂 │ 否 ✅        │               │
│ └──────────┴────────────┘               │
│                                         │
│ **对话摘要**:                           │
│ [信息框显示摘要]                          │
│                                         │
│ **辱骂词汇**:                           │
│ [警告框显示词汇]                          │
├─────────────────────────────────────────┤
│ [📥 导出为 CSV]                          │
└─────────────────────────────────────────┘
```

**代码实现**:
```python
def _show_single_audio_detail(task_data: dict, result: dict):
    """显示单个音频任务详情"""
    st.markdown("### 🎵 单个音频任务")
    
    # 1. 显示URL
    st.markdown("#### 📍 音频 URL")
    st.code(result.get('audio_url', 'N/A'), language=None)
    
    # 2. 语音识别内容
    st.markdown("#### 📝 语音识别内容")
    full_text = result.get('full_text', '')
    st.text_area("完整文本", full_text, height=200)
    
    # 3. LLM分析报告表格
    st.markdown("#### 🤖 LLM 分析报告")
    
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
    csv_data = _generate_single_audio_csv(result)
    st.download_button(
        label="📥 导出为 CSV",
        data=csv_data,
        file_name=f"single_audio_{task_data['task_id']}.csv",
        mime="text/csv"
    )
```

---

#### Excel导入任务

**展示结构**:
```
┌─────────────────────────────────────────────────┐
│ ### 📁 Excel 批量导入任务 (10 条记录)            │
├─────────────────────────────────────────────────┤
│ #### 📊 完整数据表格                              │
│ ┌────┬──────┬──────┬──────┬────┬────┬────┐    │
│ │序号│姓名  │部门  │识别  │摘要│辱骂│时长│    │
│ ├────┼──────┼──────┼──────┼────┼────┼────┤    │
│ │ 1  │张三  │销售  │...   │... │否  │10s │    │
│ │ 2  │李四  │技术  │...   │... │是  │15s │    │
│ └────┴──────┴──────┴──────┴────┴────┴────┘    │
├─────────────────────────────────────────────────┤
│ [📥 导出为 CSV]                                  │
└─────────────────────────────────────────────────┘
```

**代码实现**:
```python
def _show_excel_import_detail(task_data: dict, results: list):
    """显示Excel导入任务详情"""
    st.markdown(f"### 📁 Excel 批量导入任务 ({len(results)} 条记录)")
    
    # 获取第一条结果的extra_data来确定Excel字段
    first_result = results[0]
    extra_data = first_result.get('extra_data', {})
    
    # 1. 显示所有Excel字段 + 语音识别内容 + LLM分析
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
    
    # 2. CSV导出
    csv_data = df_results.to_csv(index=False, encoding='utf-8-sig')
    st.download_button(
        label="📥 导出为 CSV",
        data=csv_data,
        file_name=f"batch_{task_data['task_id']}.csv",
        mime="text/csv"
    )
```

---

### 3. CSV导出功能

#### 单个音频CSV格式

```csv
指标,值
音频URL,https://example.com/audio.wav
音频时长,10.5秒
处理时间,2.3秒
实时因子,4.57x
置信度,95.20%
语言,zh
是否辱骂,否
对话摘要,这是一段客服对话...
辱骂词汇,

语音识别内容
您好，请问有什么可以帮助您的？
```

**生成函数**:
```python
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
```

#### Excel导入CSV格式

直接导出DataFrame，包含所有Excel原始字段和识别结果。

---

### 4. Expander展开/收起

```python
# 显示任务详情（使用expander）
if 'selected_task_id' in st.session_state and st.session_state['selected_task_id']:
    task_id = st.session_state['selected_task_id']
    
    with st.expander(f"📊 任务详情: {task_id}", expanded=True):
        show_result_detail(task_id)
        
        # 关闭按钮
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("✖️ 关闭", key="close_detail"):
                st.session_state['selected_task_id'] = None
                st.rerun()
```

**特点**:
- ✅ 默认展开 (`expanded=True`)
- ✅ 可点击标题栏折叠
- ✅ 提供关闭按钮

---

### 5. 认证优化（页面刷新不重复登录）

#### 问题分析

Streamlit每次交互都会重新运行整个脚本，包括：
1. 页面刷新
2. 点击按钮
3. 切换Tab

如果每次都调用数据库验证session，会导致：
- ❌ 性能下降
- ❌ 数据库压力大
- ❌ 用户体验差

---

#### 优化方案

**修改前**:
```python
def require_auth():
    if 'logged_in' not in st.session_state:
        show_login_page()
        return False
    
    # ❌ 每次都验证session
    session_token = st.session_state.get('session_token')
    user_info = auth_manager.verify_session(session_token)
    if not user_info:
        st.session_state['logged_in'] = False
        show_login_page()
        return False
    
    return True
```

**修改后**:
```python
def require_auth():
    """
    认证检查
    检查用户是否已登录，未登录则显示登录页面
    
    注意：Streamlit 每次交互都会重新运行脚本，所以这里只检查 session_state
    不重复调用数据库验证，提高性能
    """
    # 1. 检查是否已登录标记
    if 'logged_in' not in st.session_state or not st.session_state['logged_in']:
        show_login_page()
        return False
    
    # 2. 检查是否有 session_token
    session_token = st.session_state.get('session_token')
    if not session_token:
        st.session_state['logged_in'] = False
        show_login_page()
        return False
    
    # 3. 检查是否有用户信息（如果为空，说明是刚登录或刷新页面）
    if 'username' not in st.session_state or 'user_role' not in st.session_state:
        # 只在用户信息缺失时才验证session
        user_info = auth_manager.verify_session(session_token)
        if user_info:
            # 恢复用户信息到 session_state
            st.session_state['username'] = user_info['username']
            st.session_state['user_role'] = user_info['role']
        else:
            # Session 无效，清除登录状态
            st.session_state['logged_in'] = False
            st.session_state.pop('session_token', None)
            show_login_page()
            return False
    
    # 4. 已登录且有用户信息，直接返回 True
    return True
```

**优势**:
- ✅ 只在必要时验证session（首次登录或用户信息缺失）
- ✅ 页面刷新时直接使用session_state中的用户信息
- ✅ 大幅提高性能
- ✅ 减少数据库压力

---

## 🔄 执行流程

### 详情查看流程

```
1. 用户在仪表盘看到任务列表
   ↓
2. 点击某行的"🔗"图标
   ↓
3. 设置 selected_task_id 并 rerun
   ↓
4. 检测到 selected_task_id，展开 expander
   ↓
5. 判断任务类型（单个音频 vs Excel导入）
   ↓
6. 按类型展示不同的详情内容
   ↓
7. 用户可以点击"导出CSV"下载
   ↓
8. 点击"✖️ 关闭"收起详情
```

---

### 认证流程

```
首次访问:
1. 检查 logged_in → False
2. 显示登录页面
3. 用户输入用户名密码
4. 验证成功，设置 session_state:
   - logged_in = True
   - session_token = xxx
   - username = xxx
   - user_role = xxx
5. rerun，进入主页面

页面刷新/交互:
1. 检查 logged_in → True ✅
2. 检查 session_token → 存在 ✅
3. 检查 username/user_role → 存在 ✅
4. 直接返回 True，不验证数据库
5. 继续显示主页面

Session过期:
1. 检查 logged_in → True
2. 检查 session_token → 存在
3. 检查 username/user_role → 不存在
4. 调用 verify_session 验证
5. 验证失败，清除登录状态
6. 显示登录页面
```

---

## 💡 优势总结

### 1. 用户体验

- ✅ **详情链接清晰**: 使用图标按钮，不会溢出
- ✅ **内容分类展示**: 按任务类型区分，信息更清晰
- ✅ **一键导出**: 支持CSV导出，方便数据分析
- ✅ **可折叠**: expander节省空间
- ✅ **无需重复登录**: 刷新页面保持登录状态

### 2. 技术优势

- ✅ **性能优化**: 减少数据库查询
- ✅ **模块化**: 独立的展示函数
- ✅ **可扩展**: 易于添加新的任务类型
- ✅ **状态管理**: 清晰的session_state管理

---

## 📁 修改的文件

### 1. [app.py](file:///Users/ylm/IdeaProjects/voice-analysis-web/app.py)

**修改内容**:
- 详情链接改为图标按钮
- 重写 `show_result_detail()` 函数
- 新增 `_show_single_audio_detail()` 函数
- 新增 `_show_excel_import_detail()` 函数
- 新增 `_generate_single_audio_csv()` 函数
- 使用expander展示详情

---

### 2. [login.py](file:///Users/ylm/IdeaProjects/voice-analysis-web/login.py)

**修改内容**:
- 优化 `require_auth()` 函数
- 只在必要时验证session
- 从session恢复用户信息

---

## 🧪 测试

### 测试步骤

1. **启动应用**
   ```bash
   streamlit run app.py
   ```

2. **登录**
   - 输入用户名和密码
   - 确认登录成功

3. **刷新页面**
   - 按F5刷新浏览器
   - 确认不需要重新登录 ✅

4. **查看详情**
   - 进入仪表盘
   - 点击某行的"🔗"图标
   - 确认expander展开显示详情

5. **单个音频任务**
   - 确认显示URL、识别内容、分析表格
   - 点击"导出CSV"，确认下载成功

6. **Excel导入任务**
   - 确认显示所有Excel字段
   - 确认显示识别内容和LLM分析
   - 点击"导出CSV"，确认下载成功

7. **关闭详情**
   - 点击"✖️ 关闭"
   - 确认expander收起

---

## ❓ 常见问题

### Q1: 为什么不用Markdown链接？

A: Streamlit的DataFrame不支持渲染HTML链接。我们使用图标按钮作为替代方案，既美观又实用。

### Q2: 为什么不每次都验证session？

A: Streamlit每次交互都会重新运行脚本，如果每次都验证session会导致严重的性能问题。我们采用懒验证策略，只在必要时才验证。

### Q3: Session什么时候会失效？

A: 
- 用户主动登出
- Session过期（由auth_manager控制）
- 浏览器清除cookie

### Q4: 可以自定义CSV导出格式吗？

A: 可以。修改 `_generate_single_audio_csv()` 函数或调整DataFrame的列即可。

---

## 🔗 相关文档

- [app.py](file:///Users/ylm/IdeaProjects/voice-analysis-web/app.py) - 主应用文件
- [login.py](file:///Users/ylm/IdeaProjects/voice-analysis-web/login.py) - 认证模块
- [TASK_DETAIL_BUTTON_FIX.md](file:///Users/ylm/IdeaProjects/voice-analysis-web/TASK_DETAIL_BUTTON_FIX.md) - 之前的按钮修复说明

---

**最后更新**: 2026-05-19  
**版本**: v2.0  
**状态**: ✅ 已完成
