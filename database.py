"""
数据库操作模块
使用 SQLAlchemy ORM 管理 MySQL 数据库
"""

import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, Text, DateTime, Enum, JSON, Index, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from contextlib import contextmanager

from config import config

Base = declarative_base()


# ==================== ORM 模型定义 ====================

class BatchTask(Base):
    """批处理任务表"""
    __tablename__ = 'batch_tasks'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(64), unique=True, nullable=False, index=True)
    task_name = Column(String(255), nullable=False)
    status = Column(Enum('pending', 'running', 'paused', 'completed', 'failed', 'cancelled'), 
                   default='pending', index=True)
    total_count = Column(Integer, default=0)
    processed_count = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    progress = Column(Float, default=0.0)
    config_json = Column(Text)
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    def to_dict(self):
        return {
            'task_id': self.task_id,
            'task_name': self.task_name,
            'status': self.status,
            'total_count': self.total_count,
            'processed_count': self.processed_count,
            'success_count': self.success_count,
            'failed_count': self.failed_count,
            'progress': self.progress,
            'config': json.loads(self.config_json) if self.config_json else {},
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
        }


class AudioResult(Base):
    """音频处理结果表"""
    __tablename__ = 'audio_results'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(64), ForeignKey('batch_tasks.task_id', ondelete='CASCADE'), nullable=False, index=True)
    audio_id = Column(String(64), unique=True, nullable=False, index=True)
    audio_url = Column(String(2048), nullable=False)
    file_name = Column(String(512))
    duration = Column(Float)
    status = Column(Enum('pending', 'processing', 'success', 'failed'), default='pending', index=True)
    
    # ASR 结果
    full_text = Column(Text)
    language = Column(String(10), default='zh')
    confidence = Column(Float)
    segments_json = Column(JSON)
    
    # LLM 分析结果
    dialogue_summary = Column(Text)
    has_abusive_language = Column(Boolean, default=False)
    abusive_words_json = Column(JSON)
    participants_json = Column(JSON)
    interaction_json = Column(JSON)
    
    # 处理信息
    processing_time = Column(Float)
    asr_time = Column(Float)
    llm_time = Column(Float)
    realtime_factor = Column(Float)
    
    # 元数据
    extra_data = Column(JSON)
    error_message = Column(Text)
    
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    def to_dict(self):
        return {
            'audio_id': self.audio_id,
            'audio_url': self.audio_url,
            'file_name': self.file_name,
            'duration': self.duration,
            'status': self.status,
            'full_text': self.full_text,
            'language': self.language,
            'confidence': self.confidence,
            'dialogue_summary': self.dialogue_summary,
            'has_abusive_language': self.has_abusive_language,
            'abusive_words': json.loads(self.abusive_words_json) if self.abusive_words_json else [],
            'processing_time': self.processing_time,
            'error_message': self.error_message,
        }


class BusinessLog(Base):
    """业务日志表"""
    __tablename__ = 'business_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    log_level = Column(Enum('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'), default='INFO', index=True)
    module = Column(String(64), index=True)
    action = Column(String(128))
    message = Column(Text)
    task_id = Column(String(64), index=True)
    audio_id = Column(String(64))
    user_id = Column(String(64))
    ip_address = Column(String(45))
    request_data = Column(JSON)
    response_data = Column(JSON)
    execution_time = Column(Float)
    stack_trace = Column(Text)
    created_at = Column(DateTime, default=datetime.now, index=True)


class ReportCache(Base):
    """统计报表缓存表"""
    __tablename__ = 'report_cache'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    report_type = Column(String(64), nullable=False, index=True)
    task_id = Column(String(64), index=True)
    date_range_start = Column(DateTime)
    date_range_end = Column(DateTime)
    data_json = Column(JSON)
    generated_at = Column(DateTime, default=datetime.now)
    expires_at = Column(DateTime)


class Checkpoint(Base):
    """断点续传检查点表"""
    __tablename__ = 'checkpoints'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(64), ForeignKey('batch_tasks.task_id', ondelete='CASCADE'), nullable=False, index=True)
    checkpoint_key = Column(String(128), nullable=False)
    checkpoint_data = Column(JSON)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


# ==================== 数据库管理器 ====================

class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self, db_url: str = None):
        self.db_url = db_url or config.database.url
        self.engine = create_engine(
            self.db_url,
            poolclass=QueuePool,
            pool_size=config.database.pool_size,
            max_overflow=10,
            pool_timeout=30,
            pool_recycle=3600,
            echo=False  # 设置为 True 可打印 SQL 语句
        )
        self.SessionLocal = sessionmaker(bind=self.engine)
        
        # 创建表
        Base.metadata.create_all(bind=self.engine)
    
    @contextmanager
    def get_session(self) -> Session:
        """获取数据库会话（上下文管理器）"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    # ==================== 任务管理 ====================
    
    def create_task(self, task_id: str, task_name: str, total_count: int, config_dict: dict = None) -> str:
        """创建批处理任务"""
        with self.get_session() as session:
            task = BatchTask(
                task_id=task_id,
                task_name=task_name,
                total_count=total_count,
                config_json=json.dumps(config_dict or {}, ensure_ascii=False)
            )
            session.add(task)
            return task_id
    
    def update_task_status(self, task_id: str, status: str, error_message: str = None):
        """更新任务状态"""
        with self.get_session() as session:
            task = session.query(BatchTask).filter_by(task_id=task_id).first()
            if task:
                task.status = status
                if error_message:
                    task.error_message = error_message
                if status == 'running' and not task.started_at:
                    task.started_at = datetime.now()
                if status in ['completed', 'failed', 'cancelled']:
                    task.completed_at = datetime.now()
    
    def update_task_progress(self, task_id: str, processed_count: int, success_count: int, failed_count: int):
        """更新任务进度"""
        with self.get_session() as session:
            task = session.query(BatchTask).filter_by(task_id=task_id).first()
            if task:
                task.processed_count = processed_count
                task.success_count = success_count
                task.failed_count = failed_count
                if task.total_count > 0:
                    task.progress = (processed_count / task.total_count) * 100
    
    def get_task(self, task_id: str) -> Optional[Dict]:
        """查询任务"""
        with self.get_session() as session:
            task = session.query(BatchTask).filter_by(task_id=task_id).first()
            return task.to_dict() if task else None
    
    def list_tasks(self, status: str = None, limit: int = 50) -> List[Dict]:
        """查询任务列表"""
        with self.get_session() as session:
            query = session.query(BatchTask)
            if status:
                query = query.filter_by(status=status)
            tasks = query.order_by(BatchTask.created_at.desc()).limit(limit).all()
            return [task.to_dict() for task in tasks]
    
    # ==================== 音频结果管理 ====================
    
    def save_audio_result(self, result_dict: dict):
        """保存音频处理结果"""
        with self.get_session() as session:
            audio_result = AudioResult(
                task_id=result_dict['task_id'],
                audio_id=result_dict['audio_id'],
                audio_url=result_dict['audio_url'],
                file_name=result_dict.get('file_name'),
                duration=result_dict.get('duration'),
                status=result_dict.get('status', 'success'),
                full_text=result_dict.get('full_text'),
                language=result_dict.get('language', 'zh'),
                confidence=result_dict.get('confidence'),
                segments_json=json.dumps(result_dict.get('segments', []), ensure_ascii=False) if result_dict.get('segments') else None,
                dialogue_summary=result_dict.get('dialogue_summary'),
                has_abusive_language=result_dict.get('has_abusive_language', False),
                abusive_words_json=json.dumps(result_dict.get('abusive_words', []), ensure_ascii=False) if result_dict.get('abusive_words') else None,
                participants_json=json.dumps(result_dict.get('participants', []), ensure_ascii=False) if result_dict.get('participants') else None,
                interaction_json=json.dumps(result_dict.get('interaction', {}), ensure_ascii=False) if result_dict.get('interaction') else None,
                processing_time=result_dict.get('processing_time'),
                asr_time=result_dict.get('asr_time'),
                llm_time=result_dict.get('llm_time'),
                realtime_factor=result_dict.get('realtime_factor'),
                extra_data=json.dumps(result_dict.get('extra_data', {}), ensure_ascii=False) if result_dict.get('extra_data') else None,
                error_message=result_dict.get('error_message')
            )
            session.add(audio_result)
    
    def get_audio_result(self, audio_id: str) -> Optional[Dict]:
        """查询音频结果"""
        with self.get_session() as session:
            result = session.query(AudioResult).filter_by(audio_id=audio_id).first()
            return result.to_dict() if result else None
    
    def get_task_results(self, task_id: str, status: str = None, limit: int = 100) -> List[Dict]:
        """查询任务的音频结果"""
        with self.get_session() as session:
            query = session.query(AudioResult).filter_by(task_id=task_id)
            if status:
                query = query.filter_by(status=status)
            results = query.order_by(AudioResult.created_at.desc()).limit(limit).all()
            return [r.to_dict() for r in results]
    
    # ==================== 日志管理 ====================
    
    def log_business_action(self, level: str, module: str, action: str, message: str, 
                           task_id: str = None, audio_id: str = None, **kwargs):
        """记录业务日志"""
        with self.get_session() as session:
            log = BusinessLog(
                log_level=level,
                module=module,
                action=action,
                message=message,
                task_id=task_id,
                audio_id=audio_id,
                **kwargs
            )
            session.add(log)
    
    def query_logs(self, task_id: str = None, level: str = None, limit: int = 100) -> List[Dict]:
        """查询业务日志"""
        with self.get_session() as session:
            query = session.query(BusinessLog)
            if task_id:
                query = query.filter_by(task_id=task_id)
            if level:
                query = query.filter_by(log_level=level)
            logs = query.order_by(BusinessLog.created_at.desc()).limit(limit).all()
            return [{
                'id': log.id,
                'level': log.log_level,
                'module': log.module,
                'action': log.action,
                'message': log.message,
                'created_at': log.created_at.isoformat()
            } for log in logs]
    
    # ==================== 检查点管理 ====================
    
    def save_checkpoint(self, task_id: str, checkpoint_key: str, checkpoint_data: dict):
        """保存检查点"""
        with self.get_session() as session:
            checkpoint = session.query(Checkpoint).filter_by(
                task_id=task_id, 
                checkpoint_key=checkpoint_key
            ).first()
            
            if checkpoint:
                checkpoint.checkpoint_data = json.dumps(checkpoint_data, ensure_ascii=False)
            else:
                checkpoint = Checkpoint(
                    task_id=task_id,
                    checkpoint_key=checkpoint_key,
                    checkpoint_data=json.dumps(checkpoint_data, ensure_ascii=False)
                )
                session.add(checkpoint)
    
    def load_checkpoint(self, task_id: str, checkpoint_key: str) -> Optional[dict]:
        """加载检查点"""
        with self.get_session() as session:
            checkpoint = session.query(Checkpoint).filter_by(
                task_id=task_id,
                checkpoint_key=checkpoint_key
            ).first()
            
            if checkpoint and checkpoint.checkpoint_data:
                return json.loads(checkpoint.checkpoint_data)
            return None
    
    def clear_checkpoint(self, task_id: str, checkpoint_key: str = None):
        """清除检查点"""
        with self.get_session() as session:
            query = session.query(Checkpoint).filter_by(task_id=task_id)
            if checkpoint_key:
                query = query.filter_by(checkpoint_key=checkpoint_key)
            query.delete()
    
    # ==================== 报表管理 ====================
    
    def cache_report(self, report_type: str, data: dict, task_id: str = None, expire_hours: int = 24):
        """缓存报表"""
        with self.get_session() as session:
            report = ReportCache(
                report_type=report_type,
                task_id=task_id,
                data_json=json.dumps(data, ensure_ascii=False),
                expires_at=datetime.now() + timedelta(hours=expire_hours)
            )
            session.add(report)
    
    def get_cached_report(self, report_type: str, task_id: str = None) -> Optional[dict]:
        """获取缓存的报表"""
        with self.get_session() as session:
            query = session.query(ReportCache).filter_by(report_type=report_type)
            if task_id:
                query = query.filter_by(task_id=task_id)
            else:
                query = query.filter(ReportCache.task_id.is_(None))
            
            report = query.filter(
                ReportCache.expires_at > datetime.now()
            ).order_by(ReportCache.generated_at.desc()).first()
            
            if report and report.data_json:
                return json.loads(report.data_json)
            return None


# 全局数据库实例
db_manager = DatabaseManager()


if __name__ == "__main__":
    # 测试
    print("数据库初始化成功")
    print(f"数据库 URL: {config.database.url}")
