"""
任务详情HTML页面生成器
生成独立的HTML页面展示任务详情，支持浏览器直接访问
"""

import os
from datetime import datetime
from typing import Dict, List
from database import db_manager
from config import config


class TaskDetailPageGenerator:
    """任务详情HTML页面生成器"""
    
    def __init__(self):
        self.output_dir = config.base_dir / "results" / "task_details"
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_task_detail_html(self, task_id: str) -> str:
        """
        生成任务详情的HTML页面
        
        Args:
            task_id: 任务ID
            
        Returns:
            HTML文件路径
        """
        # 获取任务数据
        task_data = db_manager.get_task_with_results(task_id)
        
        if not task_data:
            return self._generate_error_page(task_id, "任务不存在")
        
        # 判断任务类型
        results = task_data.get('results', [])
        is_single_audio = len(results) == 1
        
        # 生成HTML
        if is_single_audio:
            html_content = self._generate_single_audio_html(task_data, results[0])
        else:
            html_content = self._generate_batch_html(task_data, results)
        
        # 保存HTML文件
        filename = f"{task_id}.html"
        filepath = self.output_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return str(filepath)
    
    def _generate_single_audio_html(self, task_data: Dict, result: Dict) -> str:
        """生成单个音频的HTML页面"""
        
        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>任务详情 - {task_data['task_name']}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            min-height: 100vh;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
        }}
        
        .header h1 {{
            font-size: 28px;
            margin-bottom: 10px;
        }}
        
        .header .task-id {{
            font-size: 14px;
            opacity: 0.9;
        }}
        
        .content {{
            padding: 30px;
        }}
        
        .info-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .info-card {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #667eea;
        }}
        
        .info-card .label {{
            font-size: 12px;
            color: #6c757d;
            text-transform: uppercase;
            margin-bottom: 5px;
        }}
        
        .info-card .value {{
            font-size: 24px;
            font-weight: bold;
            color: #495057;
        }}
        
        .section {{
            margin-bottom: 30px;
        }}
        
        .section-title {{
            font-size: 20px;
            color: #495057;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 2px solid #e9ecef;
        }}
        
        .text-content {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            line-height: 1.8;
            white-space: pre-wrap;
            word-wrap: break-word;
        }}
        
        .analysis-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
        }}
        
        .analysis-item {{
            background: #fff;
            border: 1px solid #dee2e6;
            padding: 15px;
            border-radius: 8px;
        }}
        
        .analysis-item .label {{
            font-size: 14px;
            color: #6c757d;
            margin-bottom: 5px;
        }}
        
        .analysis-item .value {{
            font-size: 18px;
            font-weight: 600;
            color: #495057;
        }}
        
        .badge {{
            display: inline-block;
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 14px;
            font-weight: 600;
        }}
        
        .badge-success {{
            background: #d4edda;
            color: #155724;
        }}
        
        .badge-warning {{
            background: #fff3cd;
            color: #856404;
        }}
        
        .badge-danger {{
            background: #f8d7da;
            color: #721c24;
        }}
        
        .footer {{
            text-align: center;
            padding: 20px;
            color: #6c757d;
            font-size: 14px;
            border-top: 1px solid #e9ecef;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎵 单个音频分析结果</h1>
            <div class="task-id">任务ID: {task_data['task_id']}</div>
        </div>
        
        <div class="content">
            <div class="info-grid">
                <div class="info-card">
                    <div class="label">任务名称</div>
                    <div class="value" style="font-size: 16px;">{task_data['task_name']}</div>
                </div>
                <div class="info-card">
                    <div class="label">状态</div>
                    <div class="value">{self._get_status_badge(task_data['status'])}</div>
                </div>
                <div class="info-card">
                    <div class="label">创建时间</div>
                    <div class="value" style="font-size: 16px;">{task_data['created_at']}</div>
                </div>
            </div>
            
            <div class="section">
                <h2 class="section-title">📊 基本信息</h2>
                <div class="analysis-grid">
                    <div class="analysis-item">
                        <div class="label">音频时长</div>
                        <div class="value">{result.get('duration', 0):.1f} 秒</div>
                    </div>
                    <div class="analysis-item">
                        <div class="label">处理时间</div>
                        <div class="value">{result.get('processing_time', 0):.1f} 秒</div>
                    </div>
                    <div class="analysis-item">
                        <div class="label">实时因子</div>
                        <div class="value">{result.get('realtime_factor', 0):.2f}x</div>
                    </div>
                    <div class="analysis-item">
                        <div class="label">置信度</div>
                        <div class="value">{result.get('confidence', 0):.2%}</div>
                    </div>
                    <div class="analysis-item">
                        <div class="label">语言</div>
                        <div class="value">{result.get('language', 'zh')}</div>
                    </div>
                    <div class="analysis-item">
                        <div class="label">是否包含辱骂</div>
                        <div class="value">
                            {self._get_abusive_badge(result.get('has_abusive_language', False))}
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="section">
                <h2 class="section-title">📝 语音识别内容</h2>
                <div class="text-content">{result.get('full_text', '')}</div>
            </div>
            
            {self._generate_ai_analysis_section(result)}
            
            <div class="section">
                <h2 class="section-title">🔗 音频信息</h2>
                <div class="text-content" style="word-break: break-all;">{result.get('audio_url', 'N/A')}</div>
            </div>
        </div>
        
        <div class="footer">
            <p>语音识别分析系统 v3.0 | 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
    </div>
</body>
</html>"""
        
        return html
    
    def _generate_batch_html(self, task_data: Dict, results: List[Dict]) -> str:
        """生成批量任务的HTML页面"""
        
        # 构建表格行
        table_rows = ""
        for i, result in enumerate(results, 1):
            status_badge = self._get_status_badge(result.get('status', 'unknown'))
            abusive_badge = self._get_abusive_badge(result.get('has_abusive_language', False))
            
            table_rows += f"""
            <tr>
                <td>{i}</td>
                <td style="max-width: 300px; word-wrap: break-word;">{result.get('file_name', 'N/A')}</td>
                <td style="max-width: 400px; word-wrap: break-word;">{result.get('full_text', '')[:200]}...</td>
                <td>{result.get('duration', 0):.1f}s</td>
                <td>{result.get('confidence', 0):.2%}</td>
                <td>{abusive_badge}</td>
                <td>{status_badge}</td>
            </tr>
            """
        
        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>任务详情 - {task_data['task_name']}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            min-height: 100vh;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
        }}
        
        .header h1 {{
            font-size: 28px;
            margin-bottom: 10px;
        }}
        
        .header .task-id {{
            font-size: 14px;
            opacity: 0.9;
        }}
        
        .content {{
            padding: 30px;
        }}
        
        .info-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .info-card {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #667eea;
        }}
        
        .info-card .label {{
            font-size: 12px;
            color: #6c757d;
            text-transform: uppercase;
            margin-bottom: 5px;
        }}
        
        .info-card .value {{
            font-size: 24px;
            font-weight: bold;
            color: #495057;
        }}
        
        .section {{
            margin-bottom: 30px;
        }}
        
        .section-title {{
            font-size: 20px;
            color: #495057;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 2px solid #e9ecef;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            background: white;
            border-radius: 8px;
            overflow: hidden;
        }}
        
        thead {{
            background: #667eea;
            color: white;
        }}
        
        th {{
            padding: 15px;
            text-align: left;
            font-weight: 600;
        }}
        
        td {{
            padding: 12px 15px;
            border-bottom: 1px solid #e9ecef;
        }}
        
        tbody tr:hover {{
            background: #f8f9fa;
        }}
        
        .badge {{
            display: inline-block;
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 14px;
            font-weight: 600;
        }}
        
        .badge-success {{
            background: #d4edda;
            color: #155724;
        }}
        
        .badge-warning {{
            background: #fff3cd;
            color: #856404;
        }}
        
        .badge-danger {{
            background: #f8d7da;
            color: #721c24;
        }}
        
        .footer {{
            text-align: center;
            padding: 20px;
            color: #6c757d;
            font-size: 14px;
            border-top: 1px solid #e9ecef;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📁 Excel 批量处理结果</h1>
            <div class="task-id">任务ID: {task_data['task_id']}</div>
        </div>
        
        <div class="content">
            <div class="info-grid">
                <div class="info-card">
                    <div class="label">任务名称</div>
                    <div class="value" style="font-size: 16px;">{task_data['task_name']}</div>
                </div>
                <div class="info-card">
                    <div class="label">状态</div>
                    <div class="value">{self._get_status_badge(task_data['status'])}</div>
                </div>
                <div class="info-card">
                    <div class="label">总数</div>
                    <div class="value">{task_data['total_count']}</div>
                </div>
                <div class="info-card">
                    <div class="label">进度</div>
                    <div class="value">{task_data['progress']:.1f}%</div>
                </div>
                <div class="info-card">
                    <div class="label">创建时间</div>
                    <div class="value" style="font-size: 16px;">{task_data['created_at']}</div>
                </div>
            </div>
            
            <div class="section">
                <h2 class="section-title">📋 处理结果列表</h2>
                <table>
                    <thead>
                        <tr>
                            <th>#</th>
                            <th>文件名</th>
                            <th>识别文本（预览）</th>
                            <th>时长</th>
                            <th>置信度</th>
                            <th>是否辱骂</th>
                            <th>状态</th>
                        </tr>
                    </thead>
                    <tbody>
                        {table_rows}
                    </tbody>
                </table>
            </div>
        </div>
        
        <div class="footer">
            <p>语音识别分析系统 v3.0 | 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
    </div>
</body>
</html>"""
        
        return html
    
    def _generate_error_page(self, task_id: str, error_message: str) -> str:
        """生成错误页面"""
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>错误 - 任务不存在</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            margin: 0;
        }}
        .error-container {{
            background: white;
            padding: 40px;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
            text-align: center;
        }}
        h1 {{
            color: #dc3545;
            margin-bottom: 20px;
        }}
        p {{
            color: #6c757d;
            margin-bottom: 10px;
        }}
    </style>
</head>
<body>
    <div class="error-container">
        <h1>❌ 错误</h1>
        <p><strong>任务ID:</strong> {task_id}</p>
        <p>{error_message}</p>
    </div>
</body>
</html>"""
    
    def _get_status_badge(self, status: str) -> str:
        """获取状态徽章HTML"""
        status_map = {
            'completed': ('✅ 已完成', 'badge-success'),
            'running': ('🔄 运行中', 'badge-warning'),
            'failed': ('❌ 失败', 'badge-danger'),
            'pending': ('⏳ 等待中', 'badge-warning'),
        }
        
        text, css_class = status_map.get(status, ('❓ 未知', 'badge-warning'))
        return f'<span class="badge {css_class}">{text}</span>'
    
    def _get_abusive_badge(self, has_abusive: bool) -> str:
        """获取辱骂检测徽章HTML"""
        if has_abusive:
            return '<span class="badge badge-danger">是 ⚠️</span>'
        else:
            return '<span class="badge badge-success">否 ✅</span>'
    
    def _generate_ai_analysis_section(self, result: Dict) -> str:
        """生成AI分析部分HTML"""
        if not result.get('dialogue_summary'):
            return ''
        
        abusive_words = result.get('abusive_words', [])
        abusive_words_html = ""
        if abusive_words:
            words_list = ", ".join(abusive_words)
            abusive_words_html = f"""
            <div class="analysis-item">
                <div class="label">辱骂词汇</div>
                <div class="value" style="font-size: 14px; color: #dc3545;">{words_list}</div>
            </div>
            """
        
        return f"""
        <div class="section">
            <h2 class="section-title">🤖 AI 分析</h2>
            <div class="analysis-grid">
                <div class="analysis-item" style="grid-column: 1 / -1;">
                    <div class="label">对话摘要</div>
                    <div class="value" style="font-size: 16px; line-height: 1.6;">{result.get('dialogue_summary', '')}</div>
                </div>
                {abusive_words_html}
            </div>
        </div>
        """


# 全局实例
page_generator = TaskDetailPageGenerator()


if __name__ == "__main__":
    # 测试
    import sys
    
    if len(sys.argv) > 1:
        task_id = sys.argv[1]
        filepath = page_generator.generate_task_detail_html(task_id)
        print(f"✅ HTML页面已生成: {filepath}")
    else:
        print("用法: python task_detail_page.py <task_id>")
