# 语音识别 Web UI 系统 - 安装指南

## ⚠️ 重要提示

**faster-whisper 版本要求**: >= 1.0.0（不要使用 0.10.0）

原因：
- `faster-whisper==0.10.0` 强制依赖 `av==11.*`
- `av==11.*` 与 FFmpeg 8.x 不兼容（API 变更）
- `faster-whisper>=1.0.0` 支持 `av>=11`，包括 av 12.x

---

## 📋 前置条件

### 1. Python 版本

```bash
python3 --version
# 要求: Python >= 3.9
```

### 2. 系统依赖（macOS）

```bash
# 安装 Homebrew（如果未安装）
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 禁用 Homebrew 自动更新（可选）
echo 'export HOMEBREW_NO_AUTO_UPDATE=1' >> ~/.zshrc
source ~/.zshrc

# 安装 FFmpeg 和 pkg-config
brew install pkg-config ffmpeg
```

---

## 🚀 安装步骤

### 步骤 1: 安装 Python 依赖

```bash
cd /Users/ylm/IdeaProjects/voice-analysis-web

# 方式 1: 使用 requirements.txt（推荐）
pip3 install -r requirements.txt --user

# 方式 2: 手动安装核心依赖
pip3 install "faster-whisper>=1.0.0" --user
pip3 install streamlit fastapi sqlalchemy pandas --user
```

### 步骤 2: 验证安装

```bash
# 检查 faster-whisper 版本
python3 -c "import faster_whisper; print(faster_whisper.__version__)"
# 应该输出: 1.2.1 或更高

# 检查 av 版本
python3 -c "import av; print(av.__version__)"
# 应该输出: 12.0.0 或更高

# 测试导入所有模块
cd /Users/ylm/IdeaProjects/voice-analysis-web
python3 -c "from config import config; print('✅ config.py OK')"
python3 -c "from hardware_detector import get_detector; print('✅ hardware_detector.py OK')"
python3 -c "from database import db_manager; print('✅ database.py OK')"
python3 -c "from asr_engine import get_asr_engine; print('✅ asr_engine.py OK')"
```

### 步骤 3: 初始化数据库

```bash
# 连接 MySQL
mysql -u root -p

# 执行初始化脚本
source init_db.sql

# 验证表是否创建成功
USE voice_analysis;
SHOW TABLES;
# 应该显示 5 个表: batch_tasks, audio_results, business_logs, report_cache, checkpoints
```

### 步骤 4: 配置环境变量

创建 `.env` 文件：

```bash
cat > .env << EOF
# 数据库配置
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=voice_analysis

# LLM API 配置（可选，用于情感分析）
OPENAI_API_KEY=sk-your-api-key
OPENAI_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat

# 服务器配置
STREAMLIT_PORT=8501
FASTAPI_PORT=8000
EOF

# 编辑 .env 文件，设置正确的数据库密码
nano .env
```

---

## ✅ 启动应用

### 方式 1: 仅启动 Web UI

```bash
streamlit run app.py
```

访问: http://localhost:8501

### 方式 2: 同时启动 API 和 UI

```bash
# 终端 1: 启动 FastAPI
uvicorn api:app --host 0.0.0.0 --port 8000 &

# 终端 2: 启动 Streamlit
streamlit run app.py
```

---

## 🔧 常见问题

### Q1: 安装时出现 "pkg-config is required" 错误

**解决方案**:
```bash
brew install pkg-config ffmpeg
```

---

### Q2: av 编译失败（AV_OPT_TYPE_CHANNEL_LAYOUT 错误）

**原因**: `faster-whisper==0.10.0` 与 FFmpeg 8.x 不兼容

**解决方案**:
```bash
# 卸载旧版本
pip3 uninstall faster-whisper av

# 安装新版本
pip3 install "faster-whisper>=1.0.0" --user
```

---

### Q3: 找不到 MySQL 数据库

**解决方案**:
```bash
# 检查 MySQL 是否运行
brew services list | grep mysql

# 启动 MySQL
brew services start mysql

# 重新执行初始化脚本
mysql -u root -p < init_db.sql
```

---

### Q4: Streamlit 端口被占用

**解决方案**:
```bash
# 查看占用端口的进程
lsof -i :8501

# 杀死进程
kill -9 <PID>

# 或使用其他端口
streamlit run app.py --server.port 8502
```

---

### Q5: 模型下载失败（网络问题）

**解决方案**: 使用国内镜像

```bash
# 设置 Hugging Face 镜像
export HF_ENDPOINT=https://hf-mirror.com

# 然后运行应用
streamlit run app.py
```

或在代码中设置：

```python
import os
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
```

---

## 📊 已安装的依赖版本

| 包名 | 版本 | 说明 |
|------|------|------|
| faster-whisper | 1.2.1+ | ASR 引擎 |
| av | 12.0.0+ | 音频处理（兼容 FFmpeg 8.x） |
| torch | 2.0.0+ | PyTorch |
| streamlit | 1.31.0 | Web UI |
| fastapi | 0.109.0 | RESTful API |
| sqlalchemy | 2.0.25 | ORM |
| pandas | 2.2.0 | 数据处理 |
| openai | 1.12.0 | LLM API |

---

## 🎯 下一步

安装完成后，您可以：

1. **测试单个音频分析**
   - 打开 Web UI
   - 切换到「单个音频」Tab
   - 粘贴音频 URL
   - 点击「开始分析」

2. **测试批量处理**
   - 准备 CSV 文件（包含音频 URL 列）
   - 上传文件
   - 开始批处理

3. **查看统计报表**
   - 等待任务完成
   - 切换到「统计报表」Tab
   - 生成报表

---

## 📞 技术支持

如遇到问题，请提供：
1. 错误日志
2. Python 版本
3. 操作系统版本
4. 已安装的依赖版本

---

**最后更新**: 2024-01-15  
**适用版本**: voice-analysis-web v3.0.0
