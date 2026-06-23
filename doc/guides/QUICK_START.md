# 快速启动指南

## 🚀 5分钟快速开始

### 前置要求

- Python 3.9+
- MySQL 5.7+ 或 8.0+
- pip 包管理器

---

## 步骤1: 安装依赖

```bash
cd /Users/ylm/IdeaProjects/voice-analysis-web
pip install -r requirements.txt
```

---

## 步骤2: 配置数据库

### 2.1 创建数据库

```bash
mysql -u root -p
```

在MySQL命令行中执行：

```sql
CREATE DATABASE IF NOT EXISTS voice_analysis 
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;
```

### 2.2 初始化表结构

```bash
mysql -u root -p voice_analysis < init_db.sql
```

或者在MySQL命令行中：

```sql
USE voice_analysis;
source init_db.sql;
```

### 2.3 验证数据

```sql
-- 检查配置表
SELECT COUNT(*) FROM system_configs;

-- 检查用户表
SELECT username, role FROM users;
```

应该看到：
- `system_configs`: 16条记录
- `users`: 1条记录（admin账户）

---

## 步骤3: 配置应用

编辑 `config.py`，确保数据库连接正确：

```python
class DatabaseConfig:
    url = "mysql+pymysql://root:your_password@localhost:3306/voice_analysis"
    # ... 其他配置
```

**重要**: 将 `your_password` 替换为你的MySQL root密码。

---

## 步骤4: 启动应用

```bash
streamlit run app.py
```

首次启动时，你会看到：

```
============================================================
🎯 开始预加载 Whisper 模型...
============================================================
🚀 正在加载 Whisper 模型: small
   设备: cpu
   计算类型: int8
✅ 模型加载成功: small
============================================================
✅ 模型预加载完成！
============================================================
```

---

## 步骤5: 登录系统

浏览器会自动打开 `http://localhost:8501`

### 默认管理员账户

- **用户名**: `admin`
- **密码**: `admin123`

⚠️ **重要**: 首次登录后请立即修改密码！

---

## 步骤6: 创建新用户（可选）

1. 点击登录页面的"注册"按钮
2. 填写用户名和密码
3. 点击"注册"
4. 使用新账户登录

---

## 功能测试

### 测试1: 单个音频分析

1. 切换到"🎵 单个音频"Tab
2. 输入音频URL或本地路径
3. 点击"开始分析"
4. 查看识别结果和AI分析

### 测试2: 批量处理

1. 准备CSV文件，包含音频URL列
2. 切换到"📁 批量处理"Tab
3. 上传CSV文件
4. 输入任务名称
5. 点击"开始批处理"
6. 在"📊 仪表盘"查看进度

### 测试3: 查看结果详情

1. 切换到"📊 仪表盘"Tab
2. 找到已完成的任务
3. 点击"📄 详情"按钮
4. 查看完整的识别内容和分析报告

### 测试4: 系统配置

1. 切换到"⚙️ 系统配置"Tab
2. 选择不同的配置分类
3. 修改配置值（如beam_size）
4. 点击"💾 保存"

### 测试5: 用户管理（仅管理员）

1. 以admin身份登录
2. 切换到"⚙️ 系统配置"Tab
3. 滚动到底部查看"👥 用户管理"
4. 查看所有用户列表

---

## 常见问题

### Q1: 模型下载很慢怎么办？

A: Faster-Whisper首次运行时会下载模型，可以：
- 使用国内镜像加速
- 预先下载模型到缓存目录
- 选择较小的模型（tiny/base）

### Q2: 内存不足怎么办？

A: 调整模型大小：
1. 在侧边栏选择更小的模型（tiny/base）
2. 或在系统配置中修改 `asr.model_size`
3. 重启应用

### Q3: GPU未被检测到？

A: 检查CUDA安装：
```bash
nvidia-smi
```

确保安装了正确的CUDA版本和驱动。

### Q4: 忘记密码怎么办？

A: 在MySQL中重置密码：

```sql
USE voice_analysis;

-- 重置admin密码为 admin123
UPDATE users 
SET password_hash = '8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918',
    salt = 'default_salt_change_in_production'
WHERE username = 'admin';
```

### Q5: 如何修改默认端口？

A: 创建 `.streamlit/config.toml`：

```toml
[server]
port = 8502
```

---

## 性能调优

### CPU模式优化

在侧边栏调整：
- 模型大小: `base` 或 `small`
- Beam Size: `2-3`
- 并发数: `2-4`

### GPU模式优化

如果有NVIDIA GPU：
1. 确保CUDA已安装
2. 在系统配置中设置：
   - `asr.device`: `cuda`
   - `asr.compute_type`: `float16`
3. 增加并发数: `4-8`

---

## 下一步

- 📖 阅读 [README.md](file:///Users/ylm/IdeaProjects/voice-analysis-web/README.md) 了解完整功能
- 📋 查看 [OPTIMIZATION_SUMMARY.md](file:///Users/ylm/IdeaProjects/voice-analysis-web/OPTIMIZATION_SUMMARY.md) 了解优化详情
- 🔧 参考 [INSTALL.md](file:///Users/ylm/IdeaProjects/voice-analysis-web/INSTALL.md) 进行高级配置

---

## 技术支持

如有问题，请检查：
1. `logs/app.log` - 应用日志
2. `logs/error.log` - 错误日志
3. 浏览器控制台 - 前端错误

---

**祝使用愉快！** 🎉
