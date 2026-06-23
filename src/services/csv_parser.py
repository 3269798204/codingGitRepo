"""
CSV/Excel 解析器模块
支持通用列名识别，自动提取音频 URL
"""

import pandas as pd
import os
from typing import List, Dict, Optional
from pathlib import Path


class CSVParser:
    """CSV/Excel 文件解析器"""
    
    # 可能的音频 URL 列名关键词
    URL_KEYWORDS = [
        'url', 'audio', 'voice', 'file', 'path', '链接', '地址', 
        '音频', '录音', '通话', 'call', 'record'
    ]
    
    def __init__(self):
        self.supported_formats = ['.csv', '.xlsx', '.xls']
    
    def parse_file(self, file_path: str) -> pd.DataFrame:
        """
        解析 CSV/Excel 文件
        
        Args:
            file_path: 文件路径
        
        Returns:
            pd.DataFrame: 解析后的数据
        
        Raises:
            ValueError: 不支持的文件格式
            FileNotFoundError: 文件不存在
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        file_ext = Path(file_path).suffix.lower()
        
        if file_ext not in self.supported_formats:
            raise ValueError(f"不支持的文件格式: {file_ext}，支持: {self.supported_formats}")
        
        try:
            if file_ext == '.csv':
                df = pd.read_csv(file_path)
            elif file_ext in ['.xlsx', '.xls']:
                df = pd.read_excel(file_path, engine='openpyxl' if file_ext == '.xlsx' else 'xlrd')
            else:
                raise ValueError(f"不支持的格式: {file_ext}")
            
            print(f"✅ 成功解析文件: {file_path}")
            print(f"   行数: {len(df)}, 列数: {len(df.columns)}")
            print(f"   列名: {list(df.columns)}")
            
            return df
        
        except Exception as e:
            raise RuntimeError(f"解析文件失败: {e}")
    
    def detect_url_column(self, df: pd.DataFrame) -> Optional[str]:
        """
        智能检测音频 URL 列
        
        Args:
            df: DataFrame
        
        Returns:
            str: URL 列名，未找到返回 None
        """
        # 方法1：精确匹配列名
        for col in df.columns:
            col_lower = col.lower().strip()
            if col_lower in ['url', 'audio_url', 'voice_url', 'file_url', 'audio_path']:
                return col
        
        # 方法2：关键词匹配
        for col in df.columns:
            col_lower = col.lower().strip()
            if any(keyword in col_lower for keyword in self.URL_KEYWORDS):
                return col
        
        # 方法3：检查列内容是否为 URL
        for col in df.columns:
            if df[col].dtype == object:  # 字符串类型
                sample_values = df[col].dropna().head(10)
                url_count = sum(1 for val in sample_values if self._is_url(str(val)))
                
                if url_count > len(sample_values) * 0.5:  # 超过 50% 是 URL
                    print(f"💡 通过内容检测到 URL 列: {col}")
                    return col
        
        return None
    
    def _is_url(self, text: str) -> bool:
        """判断文本是否为 URL"""
        return text.startswith('http://') or text.startswith('https://') or text.startswith('/')
    
    def validate_urls(self, urls: List[str]) -> Dict[str, bool]:
        """
        验证 URL 有效性
        
        Args:
            urls: URL 列表
        
        Returns:
            dict: {url: is_valid}
        """
        results = {}
        
        for url in urls:
            if not url or pd.isna(url):
                results[url] = False
                continue
            
            url_str = str(url).strip()
            
            # 检查是否为 URL 或本地路径
            is_valid = (
                url_str.startswith('http://') or
                url_str.startswith('https://') or
                (url_str.startswith('/') and os.path.exists(url_str)) or
                (not url_str.startswith('/') and os.path.exists(url_str))
            )
            
            results[url_str] = is_valid
        
        return results
    
    def extract_audio_list(self, file_path: str) -> List[Dict]:
        """
        从文件中提取音频 URL 列表
        
        Args:
            file_path: 文件路径
        
        Returns:
            list: [{'url': str, 'row_data': dict}]
        """
        # 解析文件
        df = self.parse_file(file_path)
        
        # 检测 URL 列
        url_col = self.detect_url_column(df)
        
        if not url_col:
            raise ValueError("未检测到音频 URL 列，请确保文件包含 URL/audio/file 等列")
        
        print(f"📍 检测到 URL 列: '{url_col}'")
        
        # 提取 URL 和额外数据
        audio_list = []
        
        for idx, row in df.iterrows():
            url = row[url_col]
            
            if pd.isna(url) or not str(url).strip():
                continue
            
            # 提取其他列作为额外数据
            extra_data = {}
            for col in df.columns:
                if col != url_col and not pd.isna(row[col]):
                    extra_data[col] = str(row[col])
            
            audio_list.append({
                'url': str(url).strip(),
                'index': idx,
                'extra_data': extra_data
            })
        
        # 验证 URL
        urls = [item['url'] for item in audio_list]
        validation = self.validate_urls(urls)
        
        # 过滤无效 URL
        valid_list = [item for item in audio_list if validation.get(item['url'], False)]
        
        print(f"✅ 提取到 {len(valid_list)} 个有效音频（共 {len(audio_list)} 个）")
        
        return valid_list
    
    def get_file_preview(self, file_path: str, rows: int = 5) -> Dict:
        """
        获取文件预览
        
        Args:
            file_path: 文件路径
            rows: 预览行数
        
        Returns:
            dict: 预览信息
        """
        df = self.parse_file(file_path)
        
        url_col = self.detect_url_column(df)
        
        preview = {
            'total_rows': len(df),
            'total_columns': len(df.columns),
            'columns': list(df.columns),
            'url_column': url_col,
            'preview_data': df.head(rows).to_dict('records')
        }
        
        return preview


if __name__ == "__main__":
    # 测试
    parser = CSVParser()
    
    # 创建测试 CSV
    test_csv = "/tmp/test_audio.csv"
    with open(test_csv, 'w', encoding='utf-8') as f:
        f.write("id,audio_url,customer_id,call_time\n")
        f.write("1,https://example.com/call1.wav,CUST001,2024-01-01\n")
        f.write("2,https://example.com/call2.wav,CUST002,2024-01-02\n")
        f.write("3,https://example.com/call3.wav,CUST003,2024-01-03\n")
    
    # 测试解析
    preview = parser.get_file_preview(test_csv)
    print("\n文件预览:")
    print(f"总行数: {preview['total_rows']}")
    print(f"URL 列: {preview['url_column']}")
    print(f"前几行: {preview['preview_data']}")
    
    # 测试提取
    audio_list = parser.extract_audio_list(test_csv)
    print(f"\n提取结果: {len(audio_list)} 个音频")
    for item in audio_list[:2]:
        print(f"  - {item['url']}")
