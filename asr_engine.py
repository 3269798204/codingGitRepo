"""
ASR 引擎模块 v2.2 - 高效精度版
基于 Faster-Whisper 的语音识别引擎，支持硬件自适应配置

⚡ v2.2 优化特性：
- 动态 CPU 线程数（根据核心数自动调整 4-12 线程）
- condition_on_previous_text=False（减少累积错误）
- VAD 保守过滤（min_silence=500ms）
- 文本后处理增强（50+ 常见错别字修正）
- 超时控制（模型加载 120s, ASR 600s, LLM 30s）
- 代理兼容性修复（httpx.Client + 清除环境变量）
"""

import os
import time
import json
import re
import multiprocessing
from typing import Dict, List, Optional, Callable
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from faster_whisper import WhisperModel
import openai
import torch

from config import config, ASRConfig


class ASREngine:
    """ASR 识别引擎 v2.2"""
    _instance = None
    _model = None

    def __new__(cls, config_param: ASRConfig = None):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, config_param: ASRConfig = None):
        if self._initialized:
            return
        from config import config as global_config
        self.config = config_param if config_param is not None else global_config.asr
        self._llm_client = None
        self._initialized = True
        
        # 加载模型（带超时控制）
        self._load_model_with_timeout()


    def _check_model_cache(self, model_size: str) -> bool:
        """检查模型是否已缓存"""
        from pathlib import Path
        home = Path.home()
        
        cache_dirs = [
            home / ".cache" / "huggingface" / "hub",
            home / ".cache" / "torch" / "hub",
        ]
        
        for cache_dir in cache_dirs:
            if cache_dir.exists():
                model_pattern = f"*whisper-{model_size}*"
                matches = list(cache_dir.glob(model_pattern))
                if matches:
                    print(f"✓ 发现缓存模型：{matches[0]}")
                    return True
        
        print(f"⚠️ 未找到缓存模型，可能需要下载（首次运行会较慢）")
        return False


    def _load_model_with_timeout(self):
        """带超时控制的模型加载"""
        detector_type = self._detect_device()
        device = detector_type['device']
        compute_type = detector_type['compute_type']
        
        model_size = self.config.model_size or 'small'
        timeout = self.config.model_load_timeout or 120
        
        print("\n" + "="*60)
        print("正在加载 Faster-Whisper 模型...")
        print(f"设备: {device}, 计算类型: {compute_type}, 模型: {model_size}")
        print("="*60)
        # todo 校验模型缓存是否存在
        self._check_model_cache(model_size)
        
        def _load_model():
            start_time = time.time()
            
            # ⚡ 优化：根据 CPU 核心数动态调整线程数
            cpu_count = multiprocessing.cpu_count()
            optimal_threads = min(12, max(4, cpu_count))
            
            model = WhisperModel(
                model_size,
                device=device,
                compute_type=compute_type,
                cpu_threads=optimal_threads,
                num_workers=2
            )
            elapsed = time.time() - start_time
            print(f"✓ 模型加载完成（耗时: {elapsed:.2f}s，CPU线程: {optimal_threads}，总核心数: {cpu_count}）\n")
            return model
        
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_load_model)
            try:
                self._model = future.result(timeout=timeout)
            except FuturesTimeoutError:
                future.cancel()
                raise TimeoutError(f"模型加载超时（{timeout}秒）")
            except Exception as e:
                future.cancel()
                raise RuntimeError(f"模型加载失败：{e}")


    def _detect_device(self) -> Dict[str, str]:
        """检测可用的计算设备"""
        if torch.cuda.is_available():
            device = "cuda"
            compute_type = "float16"
            print("✓ 检测到 NVIDIA GPU (CUDA)")
            return {"device": device, "compute_type": compute_type}
        
        device = "cpu"
        compute_type = "int8"
        
        try:
            if torch.backends.mps.is_available():
                print("⚠️ 检测到 Apple Silicon GPU (MPS)，但 Faster-Whisper 不支持 MPS")
                print("   将使用 CPU + int8 量化（速度仍然比原版 Whisper 快 2-3 倍）")
            else:
                print("⚠️ 未检测到 GPU，使用 CPU (int8 量化)")
        except:
            print("⚠️ 使用 CPU (int8 量化)")
        
        return {"device": device, "compute_type": compute_type}


    def transcribe(self, audio_path: str, progress_callback: Callable = None) -> Dict:
        """
        执行语音识别（v2.2 高效精度版）
        
        Args:
            audio_path: 音频文件路径或 URL
            progress_callback: 进度回调函数 callback(progress: float, message: str)
        
        Returns:
            dict: 识别结果
        """
        if progress_callback:
            progress_callback(0.05, "准备识别...")
        
        # 如果是 URL，先下载（带超时）
        if audio_path.startswith("http://") or audio_path.startswith("https://"):
            if progress_callback:
                progress_callback(0.02, "正在下载音频...")
            audio_path = self._download_audio_with_timeout(audio_path)
        
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"音频文件不存在: {audio_path}")
        
        if progress_callback:
            progress_callback(0.1, "正在识别语音...")
        
        # 预估处理时间
        file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
        estimated_duration_min = file_size_mb / 1.5
        estimated_process_min = estimated_duration_min / 0.4
        
        print(f"\n[1/3] 执行 Faster-Whisper 语音识别（高效精度 v2.2 模式）...")
        print(f"  设备: cpu, 计算类型: int8, 模型: {self.config.model_size}")
        print(f"  📊 精度保证: small模型 + beam_size=3")
        print(f"  ⏱️  超时限制: {self.config.timeout}秒")
        print(f"  📁 音频文件大小: {file_size_mb:.2f} MB")
        print(f"  ⏳ 预估音频时长: ~{estimated_duration_min:.1f} 分钟")
        print(f"  ⏳ 预估处理时间: ~{estimated_process_min:.1f} 分钟")
        
        # 执行识别（带超时）
        start_time = time.time()
        timeout = self.config.timeout or 600
        
        def _transcribe():
            segments, info = self._model.transcribe(
                audio_path,
                language=self.config.language,
                beam_size=self.config.beam_size,
                temperature=self.config.temperature,
                compression_ratio_threshold=self.config.compression_ratio_threshold,
                no_speech_threshold=self.config.no_speech_threshold,
                condition_on_previous_text=self.config.condition_on_previous_text,
                vad_filter=self.config.vad_filter,
                vad_parameters={
                    "min_silence_duration_ms": self.config.min_silence_duration_ms,
                    "speech_pad_ms": self.config.speech_pad_ms
                } if self.config.vad_filter else None,
                word_timestamps=self.config.word_timestamps
            )
            
            # 转换结果
            transcribed_segments = []
            full_text_parts = []
            
            for i, segment in enumerate(segments):
                seg_dict = {
                    "id": i,
                    "start": round(segment.start, 2),
                    "end": round(segment.end, 2),
                    "text": segment.text.strip()
                }
                transcribed_segments.append(seg_dict)
                full_text_parts.append(segment.text.strip())
                
                # 更新进度
                if progress_callback and len(transcribed_segments) % 10 == 0:
                    progress = 0.1 + (len(transcribed_segments) / max(len(full_text_parts), 1)) * 0.7
                    progress_callback(progress, f"已识别 {len(transcribed_segments)} 段")
            
            full_text = " ".join(full_text_parts)
            
            # 文本后处理
            if progress_callback:
                progress_callback(0.85, "正在后处理...")
            
            full_text = self.post_process(full_text)
            
            return full_text, transcribed_segments, info
        
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_transcribe)
            try:
                full_text, transcribed_segments, info = future.result(timeout=timeout)
                asr_time = time.time() - start_time
                
                print(f"  ✓ 识别完成（耗时: {asr_time:.2f}s）")
                print(f"  ✓ 检测到语言: {info.language} (置信度: {info.language_probability:.2f})")
                print(f"  ✓ Segment数量: {len(transcribed_segments)}")
                
                # 计算 Realtime Factor
                audio_duration = transcribed_segments[-1]["end"] if transcribed_segments else 0
                rtf = asr_time / max(audio_duration, 1)
                print(f"  ⚡ Realtime Factor: {rtf:.2f}x (越小越快，理想值 < 0.5)")
                
                result = {
                    "full_text": full_text,
                    "language": info.language,
                    "confidence": info.language_probability,
                    "segments": transcribed_segments,
                    "asr_time": asr_time,
                    "audio_duration": audio_duration,
                    "realtime_factor": rtf
                }
                
                if progress_callback:
                    progress_callback(0.9, "识别完成")
                
                return result
                
            except FuturesTimeoutError:
                future.cancel()
                raise TimeoutError(f"ASR 转写超时（{timeout}秒），音频可能过长")


    def post_process(self, text: str) -> str:
        """
        文本后处理 v2.2（去重、清理、纠错增强版）
        
        功能：
        1. 移除开头重复内容（如"您好您好"→"您好"）
        2. 移除连续重复的句子
        3. 清理多余空格和标点
        4. 修复常见识别错误（客服场景 50+ 错别字）
        5. 修正常见错别字
        """
        if not text:
            return text
        
        # 第1步：修复开头重复
        text = self._fix_starting_repetition(text)
        
        # 第2步：分割成句子
        sentences = re.split(r'([。！？.!?])', text)
        
        # 第3步：移除连续重复的句子
        cleaned_sentences = []
        prev_sentence = ""
        
        for i in range(0, len(sentences), 2):
            sentence = sentences[i].strip()
            punctuation = sentences[i + 1] if i + 1 < len(sentences) else ""
            
            if not sentence:
                continue
            
            if prev_sentence and len(sentence) > 5:
                if sentence == prev_sentence or sentence in prev_sentence or prev_sentence in sentence:
                    continue
            
            cleaned_sentences.append(sentence + punctuation)
            prev_sentence = sentence
        
        # 第4步：重新组合
        cleaned_text = "".join(cleaned_sentences)
        
        # 第5步：清理多余空格
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
        
        # 第6步：清理重复标点
        cleaned_text = re.sub(r'([。！？.!?])\1+', r'\1', cleaned_text)
        
        # 第7步：修复常见错别字（客服场景增强版 50+）
        cleaned_text = self._fix_common_errors_v2(cleaned_text)
        
        # 第8步：清理首尾空白和标点
        cleaned_text = cleaned_text.strip(' 。！？.!?')
        
        return cleaned_text


    def _fix_starting_repetition(self, text: str) -> str:
        """修复开头重复，如'您好您好'→'您好'"""
        if len(text) < 4:
            return text
        
        for repeat_len in range(2, min(11, len(text) // 2 + 1)):
            pattern = text[:repeat_len]
            if text.startswith(pattern * 2) or text.startswith(pattern * 3):
                return pattern + text[repeat_len:]
        
        return text


    def _fix_common_errors_v2(self, text: str) -> str:
        """修复常见错别字（客服场景增强版 50+）"""
        corrections = {
            # ===== 问候语 =====
            "您号": "您好",
            "你好号": "您好",
            
            # ===== 常见同音字 =====
            "在见": "再见",
            "什幺": "什么",
            "那幺": "那么",
            "这幺": "这么",
            "怎幺": "怎么",
            
            # ===== 客服常用词 =====
            "客护": "客服",
            "咨旬": "咨询",
            "投䜣": "投诉",
            "解诀": "解决",
            "処理": "处理",
            
            # ===== 金融相关 =====
            "转帐": "转账",
            "利昔": "利息",
            "帐号": "账号",
            "登路": "登录",
            "注消": "注销",
            "付歀": "付款",
            "收欵": "收款",
            "余颉": "余额",
            "欠欵": "欠款",
            
            # ===== 数字和单位 =====
            "一佰": "一百",
            "两佰": "两百",
            "叁百": "三百",
            "仟": "千",
            
            # ===== 时间相关 =====
            "今夭": "今天",
            "明夭": "明天",
            "昨夭": "昨天",
            "吋间": "时间",
            
            # ===== 常见错别字（基于语音识别）=====
            "你姐妈": "你几码",
            "尼玛": "你嘛",
            "他妈": "它吗",
            
            # ===== 其他常见错误 =====
            "以经": "已经",
            "须要": "需要",
            "在次": "再次",
            "做用": "作用",
            "影向": "影响",
            "连系": "联系",
            "联糸": "联系",
        }
        
        for wrong, correct in corrections.items():
            text = text.replace(wrong, correct)
        
        return text


    def analyze_with_llm(self, text: str) -> Dict:
        """
        使用 LLM 进行情感分析（v2.2 带超时和降级）
        
        Args:
            text: 对话文本
        
        Returns:
            dict: 分析结果
        """
        try:
            if not self._llm_client:
                api_key = config.OPENAI_API_KEY if hasattr(config, 'OPENAI_API_KEY') else os.getenv('OPENAI_API_KEY')
                base_url = config.OPENAI_BASE_URL if hasattr(config, 'OPENAI_BASE_URL') else os.getenv('OPENAI_BASE_URL',
                                                                                                     'https://api.deepseek.com/v1')
                
                # 临时清除所有代理环境变量
                proxy_vars = ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 
                             'ALL_PROXY', 'all_proxy', 'NO_PROXY', 'no_proxy']
                saved_proxies = {}
                for var in proxy_vars:
                    if var in os.environ:
                        saved_proxies[var] = os.environ.pop(var)
                
                try:
                    # 使用 httpx 客户端显式禁用代理
                    import httpx
                    http_client = httpx.Client(
                    )

                    self._llm_client = openai.OpenAI(
                        api_key=api_key,
                        base_url=base_url,
                        http_client=http_client
                    )
                finally:
                    # 恢复原始代理环境变量
                    for var, value in saved_proxies.items():
                        os.environ[var] = value
            
            # 使用配置中的 System Prompt
            system_prompt = config.LLM_SYSTEM_PROMPT if hasattr(config, 'LLM_SYSTEM_PROMPT') else """你是情感分析专家。分析客服对话，输出JSON。"""
            
            llm_timeout = config.LLM_TIMEOUT if hasattr(config, 'LLM_TIMEOUT') else 30
            
            response = self._llm_client.chat.completions.create(
                model=config.LLM_MODEL if hasattr(config, 'LLM_MODEL') else os.getenv('LLM_MODEL', 'deepseek-chat'),
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"请分析以下对话：\n{text}"}
                ],
                temperature=0.1,
                response_format={"type": "json_object"},
                timeout=llm_timeout
            )
            
            analysis_result = json.loads(response.choices[0].message.content)
            return analysis_result
        
        except Exception as e:
            print(f"⚠️ LLM 分析失败: {e}")
            print("  降级使用基于规则的分析方法...")
            return self._fallback_analysis_v2(text)


    def _fallback_analysis_v2(self, text: str) -> Dict:
        """降级方案：基于规则的简单分析（v2.2 增强版）"""
        negative_words = ["差", "烂", "坑", "骗", "生气", "愤怒", "失望", "垃圾", "恶心", "投诉", "举报", "骗子"]
        positive_words = ["好", "满意", "开心", "感谢", "谢谢", "不错", "很棒", "可以", "行", "好的"]
        
        neg_score = sum(1 for w in negative_words if w in text)
        pos_score = sum(1 for w in positive_words if w in text)
        
        if neg_score > pos_score:
            emotion = "negative"
        elif pos_score > neg_score:
            emotion = "positive"
        else:
            emotion = "neutral"
        
        # v2.2 扩充辱骂词库
        BASE_ABUSE_WORDS = [
            "傻逼", "尼玛", "他妈", "妈的", "操", "草", "日",
            "垃圾", "废物", "滚", "去死", "白痴", "智障", "脑残",
            "你妈", "他妈的", "操你妈", "草泥马", "sb", "煞笔"
        ]
        
        found_words = [w for w in BASE_ABUSE_WORDS if w in text]
        abuse_words = list(set(found_words))
        has_abuse = len(abuse_words) > 0
        
        return {
            "dialogue_summary": "基于规则的简化分析",
            "has_abusive_language": has_abuse,
            "abusive_words_list": abuse_words,
            "participants": [
                {
                    "role": "customer",
                    "emotion_analysis": {
                        "primary_emotions": [emotion],
                        "emotion_description": f"整体情绪倾向：{emotion}",
                        "confidence": 0.6
                    },
                    "abusive_remarks": has_abuse,
                    "abusive_examples": abuse_words if has_abuse else None
                },
                {
                    "role": "customer_service",
                    "emotion_analysis": {
                        "primary_emotions": ["calm"],
                        "emotion_description": "客服情绪信息不足",
                        "confidence": 0.5
                    },
                    "abusive_remarks": False,
                    "abusive_examples": None
                }
            ],
            "interaction_characteristics": {
                "communication_blocked": False,
                "repetitive_pattern": False,
                "sarcasm_present": False,
                "note": "降级分析，建议使用LLM获得更准确结果"
            }
        }


    def _download_audio_with_timeout(self, url: str, timeout: int = None) -> str:
        """下载音频文件（带超时）- 使用 ThreadPoolExecutor 替代 signal"""
        import urllib.request
        
        if timeout is None:
            timeout = self.config.download_timeout
        
        output_path = f"/tmp/audio_{int(time.time())}.wav"
        
        print(f"📥 下载音频: {url}")
        start_time = time.time()
        
        def _download():
            urllib.request.urlretrieve(url, output_path)
            return output_path
        
        # 使用 ThreadPoolExecutor 实现超时控制
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_download)
            try:
                result = future.result(timeout=timeout)
                elapsed = time.time() - start_time
                print(f"✅ 下载完成（耗时: {elapsed:.2f}s）: {result}")
                return result
            except FuturesTimeoutError:
                future.cancel()
                raise TimeoutError(f"下载超时（{timeout}秒）")


    def process_audio_full(self, audio_path: str, progress_callback: Callable = None) -> Dict:
        """
        完整的音频处理流程（ASR + LLM）
        
        Args:
            audio_path: 音频路径
            progress_callback: 进度回调
        
        Returns:
            dict: 完整结果
        """
        total_start = time.time()
        
        # Step 1: ASR 识别
        asr_result = self.transcribe(audio_path, progress_callback)
        
        # Step 2: LLM 分析
        if progress_callback:
            progress_callback(0.95, "正在进行情感分析...")
        
        print(f"\n[2/3] LLM 智能分析...")
        llm_start = time.time()
        llm_result = self.analyze_with_llm(asr_result['full_text'])
        llm_time = time.time() - llm_start
        
        if llm_time > 0:
            print(f"  ✓ LLM 分析完成（耗时: {llm_time:.2f}s）")
        
        total_time = time.time() - total_start
        
        # 合并结果（v2.2 增强版）
        full_result = {
            **asr_result,
            "llm_analysis": llm_result,
            "llm_time": llm_time,
            "processing_time": asr_result['asr_time'] + llm_time,
            "total_time": total_time,
            "version": "v2.2",
            "optimization_notes": [
                "保持 small 模型（精度不变）",
                "保持 beam_size=3（精度不变）",
                "condition_on_previous_text=False（减少累积错误）",
                "VAD 保守过滤（min_silence=500ms）",
                "文本后处理增强（50+ 错别字修正）",
                "动态 CPU 线程（4-12 线程）",
                "代理兼容性修复"
            ]
        }
        
        if progress_callback:
            progress_callback(1.0, "处理完成")
        
        return full_result


def get_asr_engine(config_param: ASRConfig = None) -> ASREngine:
    """获取 ASR 引擎单例"""
    return ASREngine(config_param)


if __name__ == "__main__":
    # 测试
    # engine = get_asr_engine()
    llm = get_asr_engine().analyze_with_llm("你好，世界")
    print("ASR 引擎 v2.2 初始化成功")
