"""
批处理引擎模块
多线程并行处理，CPU/GPU 资源协调
"""

import os
import time
import uuid
from typing import List, Dict, Callable, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

import os, sys
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from src.core.config import config, BatchConfig
from src.db.database import db_manager
from src.asr.asr_engine import get_asr_engine
from src.services.csv_parser import CSVParser
from src.api.middleware.idempotency import idempotency_manager


class BatchProcessor:
    """批处理引擎"""
    
    def __init__(self, batch_config: BatchConfig = None):
        self.config = batch_config or config.batch
        self.asr_engine = get_asr_engine()
        self.csv_parser = CSVParser()
        
        # 任务状态管理
        self._tasks = {}  # {task_id: task_info}
        self._lock = Lock()
        
        # 检测硬件，确定最大并发数
        from src.asr.hardware_detector import get_detector
        detector = get_detector()
        rec_config = detector.get_recommended_config()
        self.max_workers = rec_config['max_workers']
        
        print(f"🔧 批处理引擎初始化")
        print(f"   最大并发数: {self.max_workers}")
        print(f"   断点续传: {'启用' if self.config.enable_checkpoint else '禁用'}")
        print(f"   缓存: {'启用' if self.config.enable_cache else '禁用'}")
    
    def start_batch(self, task_name: str, audio_urls: List[str], 
                   extra_data_list: List[Dict] = None,
                   progress_callback: Callable = None, task_config: Dict = None, user_id: str = None) -> str:
        """
        启动批处理任务
        
        Args:
            task_name: 任务名称
            audio_urls: 音频 URL 列表
            extra_data_list: 额外数据列表（与 audio_urls 对应）
            progress_callback: 进度回调 callback(task_id, progress, message)
            task_config: 任务配置（如文件路径等）
            user_id: 用户编号（users.username）
        
        Returns:
            str: 任务 ID
        """
        if extra_data_list is None:
            extra_data_list = [{} for _ in audio_urls]
        elif len(extra_data_list) != len(audio_urls):
            raise ValueError("音频 URL 与额外数据数量不匹配，请检查输入文件")

        seen_audio_ids = set()
        filtered_urls = []
        filtered_extra = []
        intercepted_urls = []

        for url, extra in zip(audio_urls, extra_data_list):
            audio_id = self._generate_audio_id(url)

            if audio_id in seen_audio_ids:
                intercepted_urls.append(url)
                continue
            seen_audio_ids.add(audio_id)

            existing_result = db_manager.get_audio_result(audio_id)
            if existing_result and existing_result.get('status') == 'success':
                intercepted_urls.append(url)
                continue

            filtered_urls.append(url)
            filtered_extra.append(extra)

        if not filtered_urls:
            if intercepted_urls:
                db_manager.log_business_action(
                    'INFO',
                    'batch',
                    'duplicate_intercept',
                    f'任务 {task_name} 被重复拦截，未创建新任务（{len(intercepted_urls)} 个重复音频）'
                )
            raise ValueError("⚠️ 本次请求中的音频均已识别，无需重复提交")

        if intercepted_urls:
            db_manager.log_business_action(
                'INFO',
                'batch',
                'duplicate_filtered',
                f'任务 {task_name} 过滤重复音频 {len(intercepted_urls)} 个'
            )

        audio_urls = filtered_urls
        extra_data_list = filtered_extra

        # 客户编码取值逻辑为 audio_result.customer_no，不在任务创建时提取
        # 任务创建时不预先提取客户编码，而是在音频结果保存时从 audio_result.customer_no 获取

        # 后端幂等性检查 - 基于任务名称和音频URL生成唯一token
        request_data = {
            'task_name': task_name,
            'audio_urls': sorted(audio_urls),  # 排序以确保相同请求生成相同token
            'extra_data_count': len(extra_data_list)
        }
        token = idempotency_manager.generate_token(request_data)
        
        if not idempotency_manager.check_and_set(token):
            raise ValueError("⚠️ 相同的批处理请求正在处理中，请勿重复提交！")
        
        task_id = str(uuid.uuid4())
        total_count = len(audio_urls)
        
        # 创建任务记录
        task_metadata = {}
        # 客户编码取值逻辑为 audio_result.customer_no，不在任务配置中存储
        # 任务配置中不预先设置客户编码，而是在音频结果保存时从 audio_result.customer_no 获取
        
        # 合并外部传入的任务配置（如文件路径等）
        if task_config:
            task_metadata.update(task_config)

        db_manager.create_task(task_id, task_name, total_count, config_dict=task_metadata, user_id=user_id)
        db_manager.update_task_status(task_id, 'running')
        db_manager.log_business_action('INFO', 'batch', 'start', 
                                      f'任务启动: {task_name}, 共 {total_count} 个音频',
                                      task_id=task_id)
        
        # 启动后台线程异步运行批处理逻辑，不阻塞当前请求，保证系统响应流畅
        import threading
        threading.Thread(
            target=self._run_batch,
            args=(task_id, task_name, total_count, audio_urls, extra_data_list, progress_callback),
            daemon=True
        ).start()
        
        return task_id
    
    def continue_task(self, task_id: str, progress_callback: Optional[Callable] = None) -> str:
        """继续执行未完成的任务
        
        Args:
            task_id: 任务ID
            progress_callback: 进度回调函数
            
        Returns:
            str: 任务ID
            
        Raises:
            ValueError: 任务不存在或已完成
        """
        # 获取任务信息
        task = db_manager.get_task(task_id)
        if not task:
            raise ValueError(f"任务 {task_id} 不存在")
        
        task_status = task.get('status')
        if task_status in ['completed', 'cancelled']:
            raise ValueError(f"任务 {task_id} 已{task_status}，无法继续执行")
        
        # 获取任务的音频结果，找出未完成的记录
        results = db_manager.get_task_results(task_id, limit=1000)
        
        if not results:
            raise ValueError(f"任务 {task_id} 没有可执行的记录")
        
        # 找出未完成的记录
        unfinished_results = [r for r in results if r.get('status') not in ['success', 'completed']]
        
        if not unfinished_results:
            # 所有记录都已完成，更新任务状态为完成
            db_manager.update_task_status(task_id, 'completed')
            raise ValueError(f"任务 {task_id} 所有记录已完成")
        
        # 重新启动后台线程处理未完成的记录
        import threading
        threading.Thread(
            target=self._continue_batch,
            args=(task_id, task.get('task_name'), task.get('total_count'), unfinished_results, progress_callback),
            daemon=True
        ).start()
        
        return task_id
    
    def _continue_batch(self, task_id: str, task_name: str, total_count: int, 
                      unfinished_results: List[Dict], progress_callback: Optional[Callable] = None):
        """后台线程继续执行未完成的批处理逻辑"""
        try:
            # 更新任务状态为运行中
            db_manager.update_task_status(task_id, 'running')
            db_manager.log_business_action('INFO', 'batch', 'continue', 
                                          f'任务继续执行: {task_name}, 待处理 {len(unfinished_results)} 个记录',
                                          task_id=task_id)
            
            # 保存任务信息
            with self._lock:
                self._tasks[task_id] = {
                    'task_id': task_id,
                    'task_name': task_name,
                    'total_count': total_count,
                    'processed_count': total_count - len(unfinished_results),
                    'success_count': 0,
                    'failed_count': 0,
                    'remaining_results': unfinished_results,
                    'status': 'running',
                    'start_time': time.time()
                }
            
            # 启动线程池处理
            executor = ThreadPoolExecutor(max_workers=self.max_workers)
            futures = {}
            
            for i, result in enumerate(unfinished_results):
                # 从结果中提取原始数据
                origin_data = result.get('origin_data', {})
                audio_url = origin_data.get('audio_url') if origin_data else result.get('audio_url')
                extra_data = result.get('extra_data', {})
                
                if not audio_url:
                    print(f"⚠️ 跳过无音频URL的记录: {result.get('audio_id')}")
                    continue
                
                future = executor.submit(
                    self._process_single_with_retry,
                    task_id, audio_url, extra_data, i + 1, len(unfinished_results)
                )
                futures[future] = (audio_url, i)
            
            # 监控进度
            completed_count = total_count - len(unfinished_results)
            
            for future in as_completed(futures):
                audio_url, idx = futures[future]
                
                try:
                    result = future.result()
                    
                    with self._lock:
                        if task_id not in self._tasks:
                            break
                        self._tasks[task_id]['processed_count'] += 1
                        
                        if result['status'] == 'success':
                            self._tasks[task_id]['success_count'] += 1
                        else:
                            self._tasks[task_id]['failed_count'] += 1
                        
                        completed_count = self._tasks[task_id]['processed_count']
                        
                        # 更新数据库
                        db_manager.update_task_progress(
                            task_id,
                            completed_count,
                            self._tasks[task_id]['success_count'],
                            self._tasks[task_id]['failed_count']
                        )
                    
                    # 回调进度
                    if progress_callback:
                        progress = (completed_count / total_count) * 100
                        progress_callback(task_id, progress, 
                                        f"已完成 {completed_count}/{total_count}")
                
                except Exception as e:
                    print(f"❌ 处理失败: {audio_url}, 错误: {e}")
                    
                    with self._lock:
                        if task_id in self._tasks:
                            self._tasks[task_id]['processed_count'] += 1
                            self._tasks[task_id]['failed_count'] += 1
                            
                            db_manager.update_task_progress(
                                task_id,
                                self._tasks[task_id]['processed_count'],
                                self._tasks[task_id]['success_count'],
                                self._tasks[task_id]['failed_count']
                            )
            
            # 任务完成
            final_status = 'completed' if self._tasks[task_id]['failed_count'] == 0 else 'partial'
            db_manager.update_task_status(task_id, final_status)
            db_manager.log_business_action('INFO', 'batch', 'complete', 
                                          f'任务完成: {task_name}, 成功 {self._tasks[task_id]["success_count"]}, 失败 {self._tasks[task_id]["failed_count"]}',
                                          task_id=task_id)
            
            # 清理任务信息
            with self._lock:
                if task_id in self._tasks:
                    del self._tasks[task_id]
                    
        except Exception as e:
            print(f"❌ 任务继续执行失败: {e}")
            db_manager.update_task_status(task_id, 'failed')
            db_manager.log_business_action('ERROR', 'batch', 'continue_failed', 
                                          f'任务继续执行失败: {task_name}, 错误: {str(e)}',
                                          task_id=task_id)
            
            # 清理任务信息
            with self._lock:
                if task_id in self._tasks:
                    del self._tasks[task_id]

    def _run_batch(self, task_id: str, task_name: str, total_count: int, 
                  audio_urls: List[str], extra_data_list: List[Dict], 
                  progress_callback: Optional[Callable] = None):
        """后台线程异步运行批处理逻辑"""
        try:
            # 检查断点续传
            processed_ids = []
            if self.config.enable_checkpoint:
                checkpoint = db_manager.load_checkpoint(task_id, 'processed_ids')
                if checkpoint:
                    processed_ids = checkpoint
                    print(f"♻️  从断点恢复，已处理 {len(processed_ids)} 个音频")
            
            # 过滤已处理的音频
            remaining_urls = []
            remaining_extra = []
            
            for url, extra in zip(audio_urls, extra_data_list):
                audio_id = self._generate_audio_id(url)
                if audio_id not in processed_ids:
                    remaining_urls.append(url)
                    remaining_extra.append(extra)
            
            print(f"📋 待处理音频: {len(remaining_urls)} 个")
            
            # 保存任务信息
            with self._lock:
                self._tasks[task_id] = {
                    'task_id': task_id,
                    'task_name': task_name,
                    'total_count': total_count,
                    'processed_count': len(processed_ids),
                    'success_count': 0,
                    'failed_count': 0,
                    'remaining_urls': remaining_urls,
                    'remaining_extra': remaining_extra,
                    'status': 'running',
                    'start_time': time.time()
                }
            
            # 启动线程池处理
            executor = ThreadPoolExecutor(max_workers=self.max_workers)
            futures = {}
            
            for i, (url, extra) in enumerate(zip(remaining_urls, remaining_extra)):
                future = executor.submit(
                    self._process_single_with_retry,
                    task_id, url, extra, i + 1, len(remaining_urls)
                )
                futures[future] = (url, i)
            
            # 监控进度
            completed_count = len(processed_ids)
            
            for future in as_completed(futures):
                url, idx = futures[future]
                
                try:
                    result = future.result()
                    
                    with self._lock:
                        if task_id not in self._tasks:
                            break
                        self._tasks[task_id]['processed_count'] += 1
                        
                        if result['status'] == 'success':
                            self._tasks[task_id]['success_count'] += 1
                        else:
                            self._tasks[task_id]['failed_count'] += 1
                        
                        completed_count = self._tasks[task_id]['processed_count']
                        
                        # 更新数据库
                        db_manager.update_task_progress(
                            task_id,
                            completed_count,
                            self._tasks[task_id]['success_count'],
                            self._tasks[task_id]['failed_count']
                        )
                        
                        # 保存检查点
                        if self.config.enable_checkpoint:
                            audio_id = self._generate_audio_id(url)
                            processed_ids.append(audio_id)
                            db_manager.save_checkpoint(task_id, 'processed_ids', processed_ids)
                    
                    # 回调进度
                    if progress_callback:
                        progress = (completed_count / total_count) * 100
                        progress_callback(task_id, progress, 
                                        f"已完成 {completed_count}/{total_count}")
                
                except Exception as e:
                    print(f"❌ 处理失败: {url}, 错误: {e}")
                    
                    with self._lock:
                        if task_id in self._tasks:
                            self._tasks[task_id]['processed_count'] += 1
                            self._tasks[task_id]['failed_count'] += 1
                            
                            db_manager.update_task_progress(
                                task_id,
                                self._tasks[task_id]['processed_count'],
                                self._tasks[task_id]['success_count'],
                                self._tasks[task_id]['failed_count']
                            )
            
            # 任务完成
            executor.shutdown(wait=True)
            
            with self._lock:
                if task_id in self._tasks:
                    self._tasks[task_id]['status'] = 'completed'
            
            db_manager.update_task_status(task_id, 'completed')
            db_manager.clear_checkpoint(task_id)
            
            db_manager.log_business_action('INFO', 'batch', 'complete',
                                          f'任务完成: {task_name}',
                                          task_id=task_id)
            
            print(f"✅ 任务完成: {task_name}")
            if task_id in self._tasks:
                print(f"   总计: {total_count}, 成功: {self._tasks[task_id]['success_count']}, "
                      f"失败: {self._tasks[task_id]['failed_count']}")
            
        except Exception as e:
            # 批处理异常，标记任务失败
            import traceback
            error_msg = f"批处理失败: {str(e)}"
            
            with self._lock:
                if task_id in self._tasks:
                    self._tasks[task_id]['status'] = 'failed'
            
            db_manager.update_task_status(task_id, 'failed', error_message=error_msg)
            db_manager.log_business_action('ERROR', 'batch', 'process_failed',
                                          f'{error_msg}\n{traceback.format_exc()}',
                                          task_id=task_id,
                                          stack_trace=traceback.format_exc())
            
            print(f"❌ 任务失败: {task_name}, 错误: {e}")
    
    def _process_single_with_retry(self, task_id: str, audio_url: str, 
                                   extra_data: dict, index: int, total: int) -> Dict:
        """
        处理单个音频（带重试）
        
        Args:
            task_id: 任务 ID
            audio_url: 音频 URL
            extra_data: 额外数据
            index: 序号
            total: 总数
        
        Returns:
            dict: 处理结果
        """
        max_retries = 2
        last_error = None
        
        for attempt in range(max_retries + 1):
            try:
                result = self._process_single(task_id, audio_url, extra_data, index, total)
                return result
            
            except Exception as e:
                last_error = e
                import traceback
                error_msg = f"⚠️  尝试 {attempt + 1}/{max_retries + 1} 失败: {audio_url}, 错误: {e}"
                print(error_msg)
                db_manager.log_business_action('WARNING', 'batch', 'retry_attempt', 
                                              f'{error_msg}\n{traceback.format_exc()}',
                                              task_id=task_id,
                                              audio_id=self._generate_audio_id(audio_url))
                
                if attempt < max_retries:
                    time.sleep(2)  # 等待 2 秒后重试
        
        # 所有重试都失败
        error_result = {
            'task_id': task_id,
            'audio_id': self._generate_audio_id(audio_url),
            'audio_url': audio_url,
            'status': 'failed',
            'error_message': str(last_error),
            'extra_data': extra_data
        }

        db_manager.log_business_action('ERROR', 'batch', 'process_failed',
                                      f'处理失败: {audio_url}, 错误: {last_error}',
                                      task_id=task_id,
                                      audio_id=error_result['audio_id'])
        
        return error_result
    
    def _process_single(self, task_id: str, audio_url: str, 
                       extra_data: dict, index: int, total: int) -> Dict:
        """
        处理单个音频
        
        Args:
            task_id: 任务 ID
            audio_url: 音频 URL
            extra_data: 额外数据
            index: 序号
            total: 总数
        
        Returns:
            dict: 处理结果
        """
        audio_id = self._generate_audio_id(audio_url)
        
        print(f"[{index}/{total}] 处理: {audio_url}")
        
        # 检查缓存
        if self.config.enable_cache:
            cached = db_manager.get_audio_result(audio_id)
            if cached and cached['status'] == 'success':
                print(f"💾 使用缓存结果")
                return cached
        
        # 执行 ASR + LLM 分析
        start_time = time.time()
        
        def progress_cb(progress, message):
            pass  # 批处理中不需要详细进度
        
        result = self.asr_engine.process_audio_full(audio_url, progress_cb)
        
        processing_time = time.time() - start_time
        
        # 构建结果
        result_dict = {
            'task_id': task_id,
            'audio_id': audio_id,
            'audio_url': audio_url,
            'file_name': os.path.basename(audio_url),
            'duration': result.get('audio_duration'),
            'status': 'success',
            'full_text': result.get('full_text'),
            'language': result.get('language'),
            'confidence': result.get('confidence'),
            'segments': result.get('segments', []),
            'dialogue_summary': result.get('llm_analysis', {}).get('dialogue_summary'),
            'has_abusive_language': result.get('llm_analysis', {}).get('has_abusive_language', False),
            'abusive_words': result.get('llm_analysis', {}).get('abusive_words_list', []),
            'participants': result.get('llm_analysis', {}).get('participants', []),
            'interaction': result.get('llm_analysis', {}).get('interaction_characteristics', {}),
            'processing_time': processing_time,
            'asr_time': result.get('asr_time'),
            'llm_time': result.get('llm_time'),
            'realtime_factor': result.get('realtime_factor'),
            'extra_data': extra_data,
            # 记录原始输入数据
            'origin_data': {
                'type': 'single_audio' if not extra_data else 'excel_import',
                'audio_url': audio_url,
                'excel_data': extra_data if extra_data else None
            }
        }
        
        # 保存到数据库
        db_manager.save_audio_result(result_dict)
        
        db_manager.log_business_action('INFO', 'batch', 'process_success',
                                      f'处理成功: {audio_url}',
                                      task_id=task_id,
                                      audio_id=audio_id,
                                      execution_time=processing_time * 1000)
        
        print(f"✅ 完成: {audio_url} (耗时: {processing_time:.1f}s)")
        
        return result_dict
    
    def pause_task(self, task_id: str):
        """暂停任务"""
        with self._lock:
            if task_id in self._tasks:
                self._tasks[task_id]['status'] = 'paused'
                db_manager.update_task_status(task_id, 'paused')
                print(f"⏸️  任务暂停: {task_id}")
    
    def resume_task(self, task_id: str, progress_callback: Callable = None):
        """恢复任务（从断点继续）"""
        task_info = db_manager.get_task(task_id)
        
        if not task_info:
            raise ValueError(f"任务不存在: {task_id}")
        
        if task_info['status'] not in ['paused', 'failed']:
            raise ValueError(f"任务状态不允许恢复: {task_info['status']}")
        
        print(f"▶️  恢复任务: {task_id}")
        
        # 重新获取未处理的音频
        # TODO: 需要从原始数据源重新获取
        # 这里简化处理，实际应该存储原始音频列表
        
        db_manager.update_task_status(task_id, 'running')
    
    def get_progress(self, task_id: str) -> Dict:
        """
        获取任务进度
        
        Args:
            task_id: 任务 ID
        
        Returns:
            dict: 进度信息
        """
        task_info = db_manager.get_task(task_id)
        
        if not task_info:
            return {'error': '任务不存在'}
        
        return task_info
    
    def _generate_audio_id(self, audio_url: str) -> str:
        """生成音频 ID"""
        import hashlib
        return hashlib.md5(audio_url.encode()).hexdigest()


if __name__ == "__main__":
    # 测试
    processor = BatchProcessor()
    print("批处理引擎初始化成功")