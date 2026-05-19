"""
统计报表生成器
生成情绪分布、性能监控等报表
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from database import db_manager


class ReportGenerator:
    """统计报表生成器"""
    
    def __init__(self):
        self.db = db_manager
    
    def generate_task_summary(self, task_id: str) -> Dict:
        """
        生成任务汇总报表
        
        Args:
            task_id: 任务 ID
        
        Returns:
            dict: 报表数据
        """
        # 查询任务信息
        task_info = self.db.get_task(task_id)
        
        if not task_info:
            return {'error': '任务不存在'}
        
        # 查询结果统计
        results = self.db.get_task_results(task_id, limit=10000)
        
        total = len(results)
        success = sum(1 for r in results if r['status'] == 'success')
        failed = sum(1 for r in results if r['status'] == 'failed')
        
        # 计算平均处理时间
        processing_times = [r['processing_time'] for r in results if r.get('processing_time')]
        avg_processing_time = sum(processing_times) / len(processing_times) if processing_times else 0
        
        # 计算平均音频时长
        durations = [r['duration'] for r in results if r.get('duration')]
        avg_duration = sum(durations) / len(durations) if durations else 0
        
        # 实时因子
        realtime_factors = [r['realtime_factor'] for r in results if r.get('realtime_factor')]
        avg_realtime_factor = sum(realtime_factors) / len(realtime_factors) if realtime_factors else 0
        
        report = {
            'task_id': task_id,
            'task_name': task_info['task_name'],
            'status': task_info['status'],
            'total_count': total,
            'success_count': success,
            'failed_count': failed,
            'success_rate': (success / total * 100) if total > 0 else 0,
            'avg_processing_time': round(avg_processing_time, 2),
            'avg_audio_duration': round(avg_duration, 2),
            'avg_realtime_factor': round(avg_realtime_factor, 2),
            'created_at': task_info['created_at'],
            'completed_at': task_info['completed_at']
        }
        
        # 缓存报表
        self.db.cache_report('task_summary', report, task_id=task_id)
        
        return report
    
    def generate_emotion_report(self, task_id: str) -> Dict:
        """
        生成情绪分布报表
        
        Args:
            task_id: 任务 ID
        
        Returns:
            dict: 情绪分布数据
        """
        results = self.db.get_task_results(task_id, status='success', limit=10000)
        
        # 统计情绪分布
        emotion_stats = {
            'positive': 0,
            'negative': 0,
            'neutral': 0,
            'anger': 0,
            'sadness': 0,
            'joy': 0,
            'fear': 0
        }
        
        abusive_count = 0
        total_with_analysis = 0
        
        for result in results:
            participants = result.get('participants', [])
            
            if not participants:
                continue
            
            total_with_analysis += 1
            
            # 统计客户情绪
            customer_emotions = []
            for p in participants:
                if p.get('role') == 'customer':
                    emotions = p.get('emotion_analysis', {}).get('primary_emotions', [])
                    customer_emotions.extend(emotions)
            
            # 统计辱骂
            if result.get('has_abusive_language'):
                abusive_count += 1
            
            # 累加情绪计数
            for emotion in customer_emotions:
                emotion_lower = emotion.lower()
                if emotion_lower in emotion_stats:
                    emotion_stats[emotion_lower] += 1
        
        # 计算百分比
        emotion_distribution = {}
        for emotion, count in emotion_stats.items():
            if count > 0:
                emotion_distribution[emotion] = {
                    'count': count,
                    'percentage': round((count / total_with_analysis * 100) if total_with_analysis > 0 else 0, 2)
                }
        
        report = {
            'task_id': task_id,
            'total_analyzed': total_with_analysis,
            'abusive_count': abusive_count,
            'abusive_rate': round((abusive_count / len(results) * 100) if results else 0, 2),
            'emotion_distribution': emotion_distribution
        }
        
        # 缓存报表
        self.db.cache_report('emotion_report', report, task_id=task_id)
        
        return report
    
    def generate_performance_report(self, task_id: str) -> Dict:
        """
        生成性能监控报表
        
        Args:
            task_id: 任务 ID
        
        Returns:
            dict: 性能数据
        """
        results = self.db.get_task_results(task_id, status='success', limit=10000)
        
        if not results:
            return {'error': '无数据'}
        
        # 处理时间统计
        processing_times = [r['processing_time'] for r in results if r.get('processing_time')]
        asr_times = [r['asr_time'] for r in results if r.get('asr_time')]
        llm_times = [r['llm_time'] for r in results if r.get('llm_time')]
        
        # 计算统计指标
        def calc_stats(times):
            if not times:
                return {}
            
            sorted_times = sorted(times)
            n = len(sorted_times)
            
            return {
                'min': round(min(times), 2),
                'max': round(max(times), 2),
                'avg': round(sum(times) / n, 2),
                'median': round(sorted_times[n // 2], 2),
                'p90': round(sorted_times[int(n * 0.9)], 2),
                'p95': round(sorted_times[int(n * 0.95)], 2)
            }
        
        report = {
            'task_id': task_id,
            'total_samples': len(results),
            'processing_time_stats': calc_stats(processing_times),
            'asr_time_stats': calc_stats(asr_times),
            'llm_time_stats': calc_stats(llm_times)
        }
        
        # 缓存报表
        self.db.cache_report('performance_report', report, task_id=task_id)
        
        return report
    
    def generate_quality_report(self, task_id: str) -> Dict:
        """
        生成质量评估报表
        
        Args:
            task_id: 任务 ID
        
        Returns:
            dict: 质量数据
        """
        results = self.db.get_task_results(task_id, status='success', limit=10000)
        
        if not results:
            return {'error': '无数据'}
        
        # 置信度分布
        confidences = [r['confidence'] for r in results if r.get('confidence')]
        
        high_confidence = sum(1 for c in confidences if c >= 0.9)
        medium_confidence = sum(1 for c in confidences if 0.7 <= c < 0.9)
        low_confidence = sum(1 for c in confidences if c < 0.7)
        
        # 文本长度分布
        text_lengths = [len(r.get('full_text', '')) for r in results]
        avg_text_length = sum(text_lengths) / len(text_lengths) if text_lengths else 0
        
        report = {
            'task_id': task_id,
            'total_samples': len(results),
            'confidence_distribution': {
                'high (>0.9)': {'count': high_confidence, 'percentage': round(high_confidence / len(confidences) * 100, 2)},
                'medium (0.7-0.9)': {'count': medium_confidence, 'percentage': round(medium_confidence / len(confidences) * 100, 2)},
                'low (<0.7)': {'count': low_confidence, 'percentage': round(low_confidence / len(confidences) * 100, 2)}
            },
            'avg_text_length': round(avg_text_length),
            'avg_confidence': round(sum(confidences) / len(confidences), 4) if confidences else 0
        }
        
        # 缓存报表
        self.db.cache_report('quality_report', report, task_id=task_id)
        
        return report
    
    def get_cached_report(self, report_type: str, task_id: str = None) -> Optional[Dict]:
        """获取缓存的报表"""
        return self.db.get_cached_report(report_type, task_id)
    
    def export_to_excel(self, task_id: str, output_path: str):
        """
        导出结果为 Excel
        
        Args:
            task_id: 任务 ID
            output_path: 输出文件路径
        """
        import pandas as pd
        
        results = self.db.get_task_results(task_id, limit=10000)
        
        if not results:
            raise ValueError("无数据可导出")
        
        # 转换为 DataFrame
        df_data = []
        for r in results:
            df_data.append({
                '音频ID': r.get('audio_id'),
                '音频URL': r.get('audio_url'),
                '状态': r.get('status'),
                '识别文本': r.get('full_text', '')[:200],  # 限制长度
                '对话摘要': r.get('dialogue_summary', ''),
                '是否辱骂': '是' if r.get('has_abusive_language') else '否',
                '处理时间(秒)': r.get('processing_time'),
                '音频时长(秒)': r.get('duration')
            })
        
        df = pd.DataFrame(df_data)
        
        # 导出到 Excel
        df.to_excel(output_path, index=False, engine='openpyxl')
        
        print(f"✅ 导出成功: {output_path}")


# 全局单例
report_generator = ReportGenerator()


if __name__ == "__main__":
    # 测试
    print("统计报表生成器初始化成功")
