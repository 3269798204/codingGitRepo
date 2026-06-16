# origin_data_json 字段优化说明

## 🎯 需求背景

**需求**: "语音识别结果（详情）调整：语音识别结果audio_results,需增加一列origin_data_json用于记录语音识别输入数据"

**具体要求**:
- a. 单个音频任务类型：语音文件资源URL
- b. Excel导入任务类型：excel原始数据json

---

## 📋 实现方案

### 1. 数据库层修改

#### 添加字段

在 `audio_results` 表中添加 `origin_data_json` 字段：

```sql
ALTER TABLE audio_results 
ADD COLUMN origin_data_json JSON COMMENT '原始输入数据（单个音频：URL；Excel导入：原始JSON）' AFTER extra_data;
```

**字段说明**:
- **类型**: JSON
- **用途**: 记录语音识别的原始输入数据
- **位置**: 在 `extra_data` 字段之后

---

#### ORM模型更新

**database.py - AudioResult类**:

```python
class AudioResult(Base):
    # ... 其他字段 ...
    
    # 元数据
    extra_data = Column(JSON)
    origin_data_json = Column(JSON)  # ✅ 新增字段
    error_message = Column(Text)
```

**to_dict方法**:

```python
def to_dict(self):
    return {
        # ... 其他字段 ...
        'origin_data': json.loads(self.origin_data_json) if self.origin_data_json else None,
        # ...
    }
```

---

#### 保存逻辑更新

**database.py - save_audio_result方法**:

```python
def save_audio_result(self, result_dict: dict):
    with self.get_session() as session:
        audio_result = AudioResult(
            # ... 其他字段 ...
            origin_data_json=json.dumps(result_dict.get('origin_data'), ensure_ascii=False) if result_dict.get('origin_data') else None,
            # ...
        )
        session.add(audio_result)
```

---

### 2. 业务逻辑层修改

#### batch_processor.py - _process_single方法

在处理单个音频时，构建origin_data：

```python
def _process_single(self, task_id: str, audio_url: str, 
                   extra_data: dict, index: int, total: int) -> Dict:
    # ... 处理逻辑 ...
    
    result_dict = {
        # ... 其他字段 ...
        
        # ✅ 记录原始输入数据
        'origin_data': {
            'type': 'single_audio' if not extra_data else 'excel_import',
            'audio_url': audio_url,
            'excel_data': extra_data if extra_data else None
        }
    }
    
    db_manager.save_audio_result(result_dict)
    return result_dict
```

**origin_data结构**:

##### 单个音频任务
```json
{
  "type": "single_audio",
  "audio_url": "https://example.com/audio.wav",
  "excel_data": null
}
```

##### Excel导入任务
```json
{
  "type": "excel_import",
  "audio_url": "https://example.com/audio1.wav",
  "excel_data": {
    "姓名": "张三",
    "部门": "销售部",
    "工号": "EMP001"
  }
}
```

---

### 3. UI层修改

#### app.py - 单个音频详情展示

```python
def _show_single_audio_detail(task_data: dict, result: dict):
    st.markdown("### 🎵 单个音频任务")
    
    # 1. 显示原始输入数据
    origin_data = result.get('origin_data', {})
    if origin_data:
        st.markdown("#### 📍 原始输入数据")
        st.json(origin_data)  # ✅ 以JSON格式展示
    
    # 2. 语音识别内容
    st.markdown("#### 📝 语音识别内容")
    full_text = result.get('full_text', '')
    st.text_area("完整文本", full_text, height=200)
    
    # 3. LLM分析报告表格
    # ...
```

**效果**:
```
┌─────────────────────────────────────────┐
│ ### 🎵 单个音频任务                      │
├─────────────────────────────────────────┤
│ #### 📍 原始输入数据                     │
│ ┌───────────────────────────────────┐   │
│ {                                   │   │
│   "type": "single_audio",           │   │
│   "audio_url": "https://...",       │   │
│   "excel_data": null                │   │
│ }                                   │   │
│ └───────────────────────────────────┘   │
├─────────────────────────────────────────┤
│ #### 📝 语音识别内容                     │
│ [文本区域]                               │
└─────────────────────────────────────────┘
```

---

#### app.py - Excel导入详情展示

```python
def _show_excel_import_detail(task_data: dict, results: list):
    st.markdown(f"### 📁 Excel 批量导入任务 ({len(results)} 条记录)")
    
    first_result = results[0]
    origin_data = first_result.get('origin_data', {})
    
    # 1. 显示原始输入数据（可折叠）
    if origin_data:
        with st.expander("📍 查看原始输入数据", expanded=False):
            st.json(origin_data)  # ✅ 以JSON格式展示
    
    # 2. 显示完整数据表格
    st.markdown("#### 📊 完整数据表格")
    # ...
```

**效果**:
```
┌─────────────────────────────────────────┐
│ ### 📁 Excel 批量导入任务 (10 条记录)    │
├─────────────────────────────────────────┤
│ ▶ 📍 查看原始输入数据                    │
│   （点击展开）                            │
├─────────────────────────────────────────┤
│ #### 📊 完整数据表格                     │
│ [数据表格]                               │
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
│   "excel_data": {                       │
│     "姓名": "张三",                      │
│     "部门": "销售部",                    │
│     "工号": "EMP001"                    │
│   }                                     │
│ }                                       │
└─────────────────────────────────────────┘
```

---

## 🔄 执行流程

### 单个音频任务

```
用户提交单个音频URL
    ↓
batch_processor._process_single()
    ↓
构建 origin_data:
{
  "type": "single_audio",
  "audio_url": "https://...",
  "excel_data": null
}
    ↓
保存到 audio_results.origin_data_json
    ↓
UI展示时使用 st.json() 显示
```

---

### Excel导入任务

```
用户上传Excel文件
    ↓
csv_parser.extract_audio_list()
提取每行的 extra_data
    ↓
batch_processor._process_single()
遍历每个音频URL
    ↓
为每个音频构建 origin_data:
{
  "type": "excel_import",
  "audio_url": "https://...",
  "excel_data": {"姓名": "张三", ...}
}
    ↓
保存到 audio_results.origin_data_json
    ↓
UI展示时使用 st.json() 显示（可折叠）
```

---

## 💡 设计考虑

### 1. 为什么使用JSON格式？

- ✅ **灵活性**: 可以存储任意结构的数据
- ✅ **可扩展**: 未来可以添加更多字段
- ✅ **易解析**: Python和JavaScript都原生支持
- ✅ **数据库支持**: MySQL 5.7+ 原生支持JSON类型

---

### 2. 为什么区分single_audio和excel_import？

- ✅ **语义清晰**: 一眼看出任务类型
- ✅ **便于统计**: 可以按类型查询
- ✅ **前端展示**: 可以根据类型显示不同的UI

---

### 3. 为什么Excel导入只展示第一条的origin_data？

- ✅ **避免冗余**: 所有记录的origin_data结构相同
- ✅ **节省空间**: 不需要重复展示
- ✅ **示例作用**: 第一条足以说明数据结构

如需查看所有记录的origin_data，可以在数据表格中添加一列。

---

### 4. 为什么使用expander折叠？

- ✅ **节省空间**: 默认不占用太多页面空间
- ✅ **按需查看**: 用户需要时才展开
- ✅ **保持整洁**: 主要信息优先展示

---

## 📊 数据示例

### 示例1: 单个音频任务

**origin_data**:
```json
{
  "type": "single_audio",
  "audio_url": "https://cdn.example.com/recordings/call_20260519_001.wav",
  "excel_data": null
}
```

**展示**:
- 类型标识: single_audio
- 音频URL: 完整URL地址
- Excel数据: null（表示不是Excel导入）

---

### 示例2: Excel导入任务（带额外字段）

**Excel原始数据**:
| 姓名 | 部门 | 工号 | 音频URL |
|------|------|------|---------|
| 张三 | 销售部 | EMP001 | https://... |
| 李四 | 技术部 | EMP002 | https://... |

**origin_data（张三的记录）**:
```json
{
  "type": "excel_import",
  "audio_url": "https://cdn.example.com/recordings/zhangsan_call.wav",
  "excel_data": {
    "姓名": "张三",
    "部门": "销售部",
    "工号": "EMP001"
  }
}
```

**origin_data（李四的记录）**:
```json
{
  "type": "excel_import",
  "audio_url": "https://cdn.example.com/recordings/lisi_call.wav",
  "excel_data": {
    "姓名": "李四",
    "部门": "技术部",
    "工号": "EMP002"
  }
}
```

---

### 示例3: Excel导入任务（无额外字段）

**Excel原始数据**:
| 音频URL |
|---------|
| https://... |

**origin_data**:
```json
{
  "type": "excel_import",
  "audio_url": "https://cdn.example.com/recordings/call_001.wav",
  "excel_data": {}
}
```

---

## 🔧 数据库迁移

### 方式一：执行SQL脚本

```bash
mysql -u username -p database_name < migration_add_origin_data.sql
```

### 方式二：手动执行

```sql
USE voice_analysis;

ALTER TABLE audio_results 
ADD COLUMN origin_data_json JSON COMMENT '原始输入数据（单个音频：URL；Excel导入：原始JSON）' AFTER extra_data;
```

### 验证

```sql
DESCRIBE audio_results;
```

应该看到新字段：
```
+-------------------+------+------+-----+---------+
| Field             | Type | Null | Key | Default |
+-------------------+------+------+-----+---------+
| origin_data_json  | json | YES  |     | NULL    |
+-------------------+------+------+-----+---------+
```

---

## 🧪 测试

### 测试步骤

1. **执行数据库迁移**
   ```bash
   mysql -u tbhx01 -p voice_analysis < migration_add_origin_data.sql
   ```

2. **启动应用**
   ```bash
   streamlit run app.py
   ```

3. **测试单个音频任务**
   - 进入"🎵 单个音频"Tab
   - 输入音频URL
   - 点击"开始分析"
   - 等待完成
   - 进入"📊 仪表盘"
   - 点击"🔗"查看详情
   - 确认显示"原始输入数据"JSON

4. **测试Excel导入任务**
   - 准备Excel文件（包含额外字段）
   - 进入"📁 批量处理"Tab
   - 上传Excel文件
   - 开始批处理
   - 等待完成
   - 进入"📊 仪表盘"
   - 点击"🔗"查看详情
   - 确认显示"查看原始输入数据"expander
   - 点击展开，确认显示JSON

5. **验证数据库**
   ```sql
   SELECT audio_id, origin_data_json FROM audio_results LIMIT 5;
   ```

---

## ❓ 常见问题

### Q1: 旧数据怎么办？

A: 旧数据的 `origin_data_json` 为 NULL，不影响功能。新任务会自动填充该字段。

### Q2: 可以查询特定类型的任务吗？

A: 可以。使用MySQL的JSON函数：
```sql
-- 查询单个音频任务
SELECT * FROM audio_results 
WHERE JSON_EXTRACT(origin_data_json, '$.type') = 'single_audio';

-- 查询Excel导入任务
SELECT * FROM audio_results 
WHERE JSON_EXTRACT(origin_data_json, '$.type') = 'excel_import';
```

### Q3: origin_data和extra_data有什么区别？

A:
- **origin_data**: 记录**输入**数据（URL、Excel原始字段）
- **extra_data**: 记录**附加**数据（从CSV/Excel提取的额外信息）

两者有重叠，但侧重点不同。

### Q4: 可以删除这个字段吗？

A: 不建议。这个字段对于追溯数据来源非常重要。如果确实不需要，可以：
```sql
ALTER TABLE audio_results DROP COLUMN origin_data_json;
```

---

## 📁 修改的文件

### 1. [database.py](file:///Users/ylm/IdeaProjects/voice-analysis-web/database.py)
- 添加 `origin_data_json` 字段到AudioResult模型
- 更新 `to_dict()` 方法
- 更新 `save_audio_result()` 方法

### 2. [batch_processor.py](file:///Users/ylm/IdeaProjects/voice-analysis-web/batch_processor.py)
- 在 `_process_single()` 中构建 `origin_data`
- 区分 single_audio 和 excel_import 类型

### 3. [app.py](file:///Users/ylm/IdeaProjects/voice-analysis-web/app.py)
- 更新 `_show_single_audio_detail()` 显示origin_data
- 更新 `_show_excel_import_detail()` 显示origin_data（可折叠）

### 4. [migration_add_origin_data.sql](file:///Users/ylm/IdeaProjects/voice-analysis-web/migration_add_origin_data.sql)
- 数据库迁移脚本

---

## ✨ 总结

**origin_data_json字段优化已完成！**

现在的系统：
1. ✅ 数据库表添加了origin_data_json字段
2. ✅ ORM模型和保存逻辑已更新
3. ✅ 单个音频任务记录URL
4. ✅ Excel导入任务记录原始JSON
5. ✅ UI展示原始输入数据（JSON格式）
6. ✅ Excel导入使用expander折叠展示

系统具备了完整的原始输入数据追溯能力。🎉
