-- 为 audio_results 表添加 origin_data_json 字段
-- 用于记录语音识别的原始输入数据

USE voice_analysis;

-- 添加 origin_data_json 字段
ALTER TABLE audio_results 
ADD COLUMN origin_data_json JSON COMMENT '原始输入数据（单个音频：URL；Excel导入：原始JSON）' AFTER extra_data;

-- 验证字段是否添加成功
DESCRIBE audio_results;
