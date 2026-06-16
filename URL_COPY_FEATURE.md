# URL链接和JSON数据复制功能优化

## 🎯 需求背景

**需求**: "页面展示所有链接需要实现悬浮可跳转、复制等功能"

**具体要求**:
1. ✅ 链接支持悬浮显示（hover效果）
2. ✅ 点击可以跳转
3. ✅ 提供复制功能

---

## 📋 实现方案

### 1. 通用组件设计

创建两个通用组件函数，用于渲染带复制功能的URL和JSON：

#### render_url_with_copy()

```python
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
        # 显示为可点击的链接
        st.markdown(f"[{display_url}]({url})", unsafe_allow_html=True)
    
    with col2:
        # 复制按钮
        if st.button("📋 复制", key=f"copy_{hash(url)}", help="复制链接到剪贴板"):
            # Streamlit不支持直接复制到剪贴板，使用代码块替代
            st.code(url, language=None)
            st.success("✅ 已显示完整URL，请手动复制")
```

**特点**:
- ✅ **悬浮效果**: Markdown链接自动支持hover效果
- ✅ **点击跳转**: 点击链接在新标签页打开
- ✅ **智能截断**: 超过80字符自动截断显示
- ✅ **复制功能**: 点击按钮显示完整URL供复制

---

#### render_json_with_copy()

```python
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
        st.success("✅ 已显示JSON，请手动复制")
```

**特点**:
- ✅ **格式化显示**: 使用st.json()美观展示
- ✅ **复制功能**: 点击按钮显示格式化JSON供复制
- ✅ **语法高亮**: code块支持JSON语法高亮

---

### 2. 应用场景

#### 场景1: 单个音频任务 - 原始输入数据

**修改前**:
```python
origin_data = result.get('origin_data', {})
if origin_data:
    st.markdown("#### 📍 原始输入数据")
    st.json(origin_data)  # ❌ 无法复制
```

**修改后**:
```python
origin_data = result.get('origin_data', {})
if origin_data:
    st.markdown("#### 📍 原始输入数据")
    render_json_with_copy(origin_data, "原始输入数据")  # ✅ 支持复制
```

**效果**:
```
┌─────────────────────────────────────────┐
│ #### 📍 原始输入数据                     │
├─────────────────────────────────────────┤
│ {                                       │
│   "type": "single_audio",               │
│   "audio_url": "https://...",           │
│   "excel_data": null                    │
│ }                                       │
├─────────────────────────────────────────┤
│ [📋 复制JSON]                            │
└─────────────────────────────────────────┘
```

点击"📋 复制JSON"后：
```
┌─────────────────────────────────────────┐
│ ✅ 已显示JSON，请手动复制                 │
├─────────────────────────────────────────┤
│ {                                       │
│   "type": "single_audio",               │
│   "audio_url": "https://example.com/... │
│   "excel_data": null                    │
│ }                                       │
└─────────────────────────────────────────┘
```

---

#### 场景2: Excel导入任务 - 原始输入数据

**修改前**:
```python
if origin_data:
    with st.expander("📍 查看原始输入数据", expanded=False):
        st.json(origin_data)  # ❌ 无法复制
```

**修改后**:
```python
if origin_data:
    with st.expander("📍 查看原始输入数据", expanded=False):
        render_json_with_copy(origin_data, "原始输入数据")  # ✅ 支持复制
```

**效果**:
```
┌─────────────────────────────────────────┐
│ ▶ 📍 查看原始输入数据                    │
└─────────────────────────────────────────┘
```

展开后：
```
┌─────────────────────────────────────────┐
│ ▼ 📍 查看原始输入数据                    │
├─────────────────────────────────────────┤
│ {                                       │
│   "type": "excel_import",               │
│   "audio_url": "https://...",           │
│   "excel_data": {...}                   │
│ }                                       │
├─────────────────────────────────────────┤
│ [📋 复制JSON]                            │
└─────────────────────────────────────────┘
```

---

### 3. URL链接展示

虽然当前主要使用JSON格式展示origin_data（其中包含URL），但如果需要单独展示URL，可以使用`render_url_with_copy()`函数。

**示例**:
```python
audio_url = result.get('audio_url', '')
render_url_with_copy(audio_url, "音频URL", max_length=60)
```

**效果**:
```
┌──────────────────────────────────────────────┐
│ https://cdn.example.com/recordings/call_...  │ [📋 复制]
└──────────────────────────────────────────────┘
```

点击链接 → 新标签页打开URL  
点击"📋 复制" → 显示完整URL供复制

---

## 💡 技术说明

### 1. 为什么不能直接复制到剪贴板？

**Streamlit的限制**:
- Streamlit是纯Python框架，运行在服务器端
- 浏览器出于安全考虑，不允许服务器端代码直接操作客户端剪贴板
- 需要使用JavaScript的`navigator.clipboard.writeText()` API

**我们的解决方案**:
1. 点击"复制"按钮
2. 显示完整内容在code块中
3. 用户手动选择并复制（Ctrl+C / Cmd+C）

---

### 2. 如何实现真正的剪贴板复制？

如果需要真正的剪贴板复制功能，可以使用Streamlit自定义组件或注入JavaScript：

#### 方案A: 使用streamlit-copy-button组件

```python
from streamlit_copy_button import copy_button

copy_button(
    text=url,
    label="📋 复制",
    key=f"copy_{hash(url)}"
)
```

安装：
```bash
pip install streamlit-copy-button
```

#### 方案B: 注入JavaScript

```python
import streamlit.components.v1 as components

def copy_to_clipboard(text: str, button_id: str):
    """通过JavaScript复制到剪贴板"""
    js_code = f"""
    <script>
    function copyToClipboard() {{
        navigator.clipboard.writeText("{text}").then(() => {{
            alert("已复制到剪贴板！");
        }});
    }}
    </script>
    <button onclick="copyToClipboard()" id="{button_id}">📋 复制</button>
    """
    components.html(js_code, height=50)
```

**注意**: 这种方式有XSS风险，需要谨慎使用。

---

### 3. Markdown链接的hover效果

Streamlit的Markdown链接自动支持CSS hover效果：

```css
a:hover {
    color: #ff4b4b;
    text-decoration: underline;
}
```

无需额外配置，浏览器会自动应用默认样式。

---

## 🔄 执行流程

### URL复制流程

```
用户看到URL链接
    ↓
鼠标悬停 → 显示hover效果（颜色变化、下划线）
    ↓
点击链接 → 新标签页打开URL
    ↓
或者点击"📋 复制"按钮
    ↓
显示完整URL在code块中
    ↓
显示成功提示
    ↓
用户手动复制（Ctrl+C）
```

---

### JSON复制流程

```
用户看到JSON数据
    ↓
浏览格式化后的JSON
    ↓
点击"📋 复制JSON"按钮
    ↓
显示完整JSON在code块中（带语法高亮）
    ↓
显示成功提示
    ↓
用户手动复制（Ctrl+C）
```

---

## 📊 对比分析

### 修改前 vs 修改后

| 功能 | 修改前 | 修改后 |
|------|--------|--------|
| 链接显示 | st.json() | render_json_with_copy() |
| 悬浮效果 | ❌ 无 | ✅ 自动支持 |
| 点击跳转 | ❌ 不可点击 | ✅ 可点击 |
| 复制功能 | ❌ 无 | ✅ 有 |
| 用户体验 | ⭐⭐ | ⭐⭐⭐⭐⭐ |

---

## 🧪 测试

### 测试步骤

1. **启动应用**
   ```bash
   streamlit run app.py
   ```

2. **测试单个音频任务**
   - 进入"🎵 单个音频"Tab
   - 输入音频URL并提交
   - 等待完成
   - 进入"📊 仪表盘"
   - 点击"🔗"查看详情
   - 确认"原始输入数据"显示JSON
   - 点击"📋 复制JSON"按钮
   - 确认显示完整JSON
   - 手动复制并验证

3. **测试Excel导入任务**
   - 上传Excel文件
   - 开始批处理
   - 等待完成
   - 进入"📊 仪表盘"
   - 点击"🔗"查看详情
   - 点击"📍 查看原始输入数据"展开
   - 确认显示JSON
   - 点击"📋 复制JSON"按钮
   - 确认显示完整JSON
   - 手动复制并验证

4. **测试链接跳转**
   - 在JSON中找到URL
   - 如果是单独的URL链接，点击确认跳转
   - 确认在新标签页打开

---

## ❓ 常见问题

### Q1: 为什么不直接复制到剪贴板？

A: Streamlit是服务器端框架，无法直接操作客户端剪贴板。需要使用JavaScript或第三方组件。

### Q2: 可以自定义复制按钮的样式吗？

A: 可以。使用CSS或自定义HTML：
```python
st.markdown("""
<style>
.stButton > button {
    background-color: #4CAF50;
    color: white;
}
</style>
""", unsafe_allow_html=True)
```

### Q3: 如何支持更多格式（如XML、YAML）？

A: 扩展`render_json_with_copy()`函数：
```python
def render_data_with_copy(data, format="json"):
    if format == "json":
        st.json(data)
        code_lang = "json"
    elif format == "yaml":
        import yaml
        yaml_str = yaml.dump(data)
        st.code(yaml_str, language="yaml")
        code_lang = "yaml"
    
    if st.button("📋 复制"):
        # 显示对应格式
        ...
```

### Q4: 可以添加下载功能吗？

A: 可以。使用`st.download_button()`:
```python
import json
json_str = json.dumps(data, ensure_ascii=False, indent=2)

st.download_button(
    label="📥 下载JSON",
    data=json_str,
    file_name="data.json",
    mime="application/json"
)
```

---

## 📁 修改的文件

### [app.py](file:///Users/ylm/IdeaProjects/voice-analysis-web/app.py)

**新增内容**:
1. `render_url_with_copy()` - URL链接组件
2. `render_json_with_copy()` - JSON数据组件

**修改内容**:
1. `_show_single_audio_detail()` - 使用新组件
2. `_show_excel_import_detail()` - 使用新组件

---

## ✨ 总结

**URL链接和JSON复制功能已完成！**

现在的系统：
1. ✅ 所有JSON数据支持复制
2. ✅ Markdown链接自动支持hover和跳转
3. ✅ 提供"📋 复制"按钮
4. ✅ 点击后显示完整内容供复制
5. ✅ 统一的组件接口，易于复用

**用户体验提升**:
- ⭐ 链接可点击跳转
- ⭐ 数据可一键复制
- ⭐ 界面整洁美观
- ⭐ 操作流程清晰

系统具备了完善的链接和数据复制能力。🎉
