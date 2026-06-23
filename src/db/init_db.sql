-- 语音识别分析系统 - 数据库初始化脚本

-- 创建数据库
CREATE DATABASE IF NOT EXISTS voice_analysis 
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

USE voice_analysis;

-- 1. 批处理任务表
CREATE TABLE IF NOT EXISTS batch_tasks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    task_id VARCHAR(64) UNIQUE NOT NULL COMMENT '任务ID (UUID)',
    task_name VARCHAR(255) NOT NULL COMMENT '任务名称',
    status ENUM('pending', 'running', 'paused', 'completed', 'failed', 'cancelled') DEFAULT 'pending' COMMENT '任务状态',
    total_count INT DEFAULT 0 COMMENT '总音频数',
    processed_count INT DEFAULT 0 COMMENT '已处理数',
    success_count INT DEFAULT 0 COMMENT '成功数',
    failed_count INT DEFAULT 0 COMMENT '失败数',
    progress FLOAT DEFAULT 0.0 COMMENT '进度百分比',
    config_json TEXT COMMENT '配置参数 (JSON)',
    error_message TEXT COMMENT '错误信息',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    started_at TIMESTAMP NULL COMMENT '开始时间',
    completed_at TIMESTAMP NULL COMMENT '完成时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_status (status),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='批处理任务表';

-- 2. 音频处理结果表
CREATE TABLE IF NOT EXISTS audio_results (
    id INT AUTO_INCREMENT PRIMARY KEY,
    task_id VARCHAR(64) NOT NULL COMMENT '任务ID',
    audio_id VARCHAR(64) UNIQUE NOT NULL COMMENT '音频ID',
    audio_url VARCHAR(2048) NOT NULL COMMENT '音频URL或路径',
    file_name VARCHAR(512) COMMENT '文件名',
    duration FLOAT COMMENT '音频时长（秒）',
    status ENUM('pending', 'processing', 'success', 'failed') DEFAULT 'pending' COMMENT '处理状态',
    
    -- ASR 结果
    full_text LONGTEXT COMMENT '完整识别文本',
    language VARCHAR(10) DEFAULT 'zh' COMMENT '识别语言',
    confidence FLOAT COMMENT '识别置信度',
    segments_json JSON COMMENT '分段结果 (JSON)',
    
    -- LLM 分析结果
    dialogue_summary TEXT COMMENT '对话摘要',
    has_abusive_language BOOLEAN DEFAULT FALSE COMMENT '是否包含辱骂',
    abusive_words_json JSON COMMENT '辱骂词列表 (JSON)',
    participants_json JSON COMMENT '参与者情绪分析 (JSON)',
    interaction_json JSON COMMENT '交互特征 (JSON)',
    
    -- 处理信息
    processing_time FLOAT COMMENT '处理耗时（秒）',
    asr_time FLOAT COMMENT 'ASR 耗时（秒）',
    llm_time FLOAT COMMENT 'LLM 耗时（秒）',
    realtime_factor FLOAT COMMENT '实时因子',
    
    -- 元数据
    extra_data JSON COMMENT '额外数据 (从 CSV 提取)',
    error_message TEXT COMMENT '错误信息',
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    INDEX idx_task_id (task_id),
    INDEX idx_status (status),
    INDEX idx_audio_id (audio_id),
    FOREIGN KEY (task_id) REFERENCES batch_tasks(task_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='音频处理结果表';

-- 3. 业务日志表
CREATE TABLE IF NOT EXISTS business_logs (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    log_level ENUM('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL') DEFAULT 'INFO' COMMENT '日志级别',
    module VARCHAR(64) COMMENT '模块名称',
    action VARCHAR(128) COMMENT '操作类型',
    message TEXT COMMENT '日志消息',
    task_id VARCHAR(64) COMMENT '关联任务ID',
    audio_id VARCHAR(64) COMMENT '关联音频ID',
    user_id VARCHAR(64) COMMENT '用户ID',
    ip_address VARCHAR(45) COMMENT 'IP地址',
    request_data JSON COMMENT '请求数据',
    response_data JSON COMMENT '响应数据',
    execution_time FLOAT COMMENT '执行时间（毫秒）',
    stack_trace TEXT COMMENT '堆栈跟踪（错误时）',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    
    INDEX idx_level (log_level),
    INDEX idx_module (module),
    INDEX idx_task_id (task_id),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='业务日志表';

-- 4. 统计报表缓存表
CREATE TABLE IF NOT EXISTS report_cache (
    id INT AUTO_INCREMENT PRIMARY KEY,
    report_type VARCHAR(64) NOT NULL COMMENT '报表类型',
    task_id VARCHAR(64) COMMENT '任务ID（NULL表示全局）',
    date_range_start DATE COMMENT '开始日期',
    date_range_end DATE COMMENT '结束日期',
    data_json JSON COMMENT '报表数据 (JSON)',
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '生成时间',
    expires_at TIMESTAMP COMMENT '过期时间',
    
    INDEX idx_report_type (report_type),
    INDEX idx_task_id (task_id),
    INDEX idx_expires_at (expires_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='统计报表缓存表';

-- 5. 断点续传检查点表
CREATE TABLE IF NOT EXISTS checkpoints (
    id INT AUTO_INCREMENT PRIMARY KEY,
    task_id VARCHAR(64) NOT NULL COMMENT '任务ID',
    checkpoint_key VARCHAR(128) NOT NULL COMMENT '检查点键',
    checkpoint_data JSON COMMENT '检查点数据',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    UNIQUE KEY uk_task_checkpoint (task_id, checkpoint_key),
    INDEX idx_task_id (task_id),
    FOREIGN KEY (task_id) REFERENCES batch_tasks(task_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='断点续传检查点表';

-- 6. 系统配置表
CREATE TABLE IF NOT EXISTS system_configs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    config_key VARCHAR(128) UNIQUE NOT NULL COMMENT '配置键',
    config_value TEXT NOT NULL COMMENT '配置值',
    config_type ENUM('string', 'int', 'float', 'bool', 'json') DEFAULT 'string' COMMENT '配置类型',
    description VARCHAR(512) COMMENT '配置描述',
    category VARCHAR(64) COMMENT '配置分类 (asr/llm/batch/system)',
    is_editable BOOLEAN DEFAULT TRUE COMMENT '是否可编辑',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    INDEX idx_category (category),
    INDEX idx_config_key (config_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='系统配置表';

-- 插入默认配置
INSERT INTO system_configs (config_key, config_value, config_type, description, category, is_editable) VALUES
('asr.model_size', 'small', 'string', 'ASR模型大小 (tiny/base/small/medium/large)', 'asr', TRUE),
('asr.beam_size', '3', 'int', 'Beam Size', 'asr', TRUE),
('asr.temperature', '0.0', 'float', '采样温度', 'asr', TRUE),
('asr.language', 'zh', 'string', '识别语言', 'asr', TRUE),
('asr.device', 'cpu', 'string', '计算设备 (cpu/cuda)', 'asr', FALSE),
('asr.compute_type', 'int8', 'string', '计算类型 (int8/float16/float32)', 'asr', FALSE),
('llm.api_key', '', 'string', 'LLM API密钥', 'llm', TRUE),
('llm.base_url', 'https://api.deepseek.com/v1', 'string', 'LLM API基础URL', 'llm', TRUE),
('llm.model', 'deepseek-chat', 'string', 'LLM模型名称', 'llm', TRUE),
('batch.max_workers', '2', 'int', '批处理最大并发数', 'batch', TRUE),
('batch.enable_checkpoint', 'true', 'bool', '启用断点续传', 'batch', TRUE),
('batch.enable_cache', 'true', 'bool', '启用结果缓存', 'batch', TRUE),
('system.app_title', '语音识别分析系统 v3.0', 'string', '应用标题', 'system', TRUE),
('system.debug_mode', 'false', 'bool', '调试模式', 'system', TRUE);

-- 7. 用户表
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(64) UNIQUE NOT NULL COMMENT '用户名',
    password_hash VARCHAR(128) NOT NULL COMMENT '密码哈希',
    salt VARCHAR(128) NOT NULL COMMENT '盐值',
    role VARCHAR(32) DEFAULT 'user' COMMENT '角色 (admin/user)',
    email VARCHAR(128) COMMENT '邮箱',
    is_active BOOLEAN DEFAULT TRUE COMMENT '是否激活',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    INDEX idx_username (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户表';

-- 8. 角色表
CREATE TABLE IF NOT EXISTS roles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    role_name VARCHAR(32) UNIQUE NOT NULL COMMENT '角色名称',
    permissions_json JSON COMMENT '权限列表 (JSON)',
    description VARCHAR(512) COMMENT '角色描述',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    INDEX idx_role_name (role_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='角色表';

-- 插入默认管理员账户（密码: admin123）
-- 注意：实际使用时请修改默认密码
INSERT INTO users (username, password_hash, salt, role, email) VALUES
('admin', 
 '122f137a81dc44e6ab559de0b98b43dc39169964e7ca35d6cc3962834c8732df',
 'default_salt_change_in_production',
 'admin',
 'admin@example.com');

-- 插入示例数据（可选）
INSERT INTO business_logs (log_level, module, action, message) VALUES
('INFO', 'system', 'startup', '语音识别分析系统启动'),
('INFO', 'database', 'init', '数据库初始化完成');
