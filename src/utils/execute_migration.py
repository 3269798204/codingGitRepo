#!/usr/bin/env python3
"""
执行数据库迁移脚本
添加 origin_data_json 字段到 audio_results 表
"""

import pymysql
import os, sys
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from src.core.config import config

def execute_migration():
    """执行数据库迁移"""
    
    print("=" * 60)
    print("🚀 开始执行数据库迁移")
    print("=" * 60)
    
    # 数据库连接配置
    db_config = {
        'host': config.database.host,
        'port': config.database.port,
        'user': config.database.user,
        'password': config.database.password,
        'database': config.database.database,
        'charset': 'utf8mb4'
    }
    
    connection = None
    try:
        # 连接数据库
        print(f"\n📡 连接到数据库: {db_config['host']}:{db_config['port']}")
        connection = pymysql.connect(**db_config)
        cursor = connection.cursor()
        
        print("✅ 数据库连接成功\n")
        
        # 检查字段是否已存在
        print("🔍 检查 origin_data_json 字段是否存在...")
        cursor.execute("""
            SELECT COUNT(*) 
            FROM information_schema.COLUMNS 
            WHERE TABLE_SCHEMA = %s 
              AND TABLE_NAME = 'audio_results' 
              AND COLUMN_NAME = 'origin_data_json'
        """, (db_config['database'],))
        
        exists = cursor.fetchone()[0]
        
        if exists > 0:
            print("⚠️  字段 origin_data_json 已存在，跳过添加\n")
        else:
            # 执行ALTER TABLE
            print("➕ 添加 origin_data_json 字段...")
            alter_sql = """
                ALTER TABLE audio_results 
                ADD COLUMN origin_data_json JSON COMMENT '原始输入数据（单个音频：URL；Excel导入：原始JSON）' AFTER extra_data
            """
            cursor.execute(alter_sql)
            connection.commit()
            print("✅ 字段添加成功\n")
        
        # 验证字段
        print("🔍 验证字段结构...")
        cursor.execute("DESCRIBE audio_results")
        columns = cursor.fetchall()
        
        print("\n📋 audio_results 表结构:")
        print("-" * 60)
        for col in columns:
            field_name = col[0]
            field_type = col[1]
            nullable = col[2]
            key = col[3]
            default = col[4]
            extra = col[5]
            
            if field_name == 'origin_data_json':
                print(f"  ✅ {field_name:25} {field_type:15} {nullable:5} {key:5} {str(default):10} {extra}")
            elif field_name in ['extra_data', 'error_message']:
                print(f"     {field_name:25} {field_type:15} {nullable:5} {key:5} {str(default):10} {extra}")
        
        print("-" * 60)
        
        # 统计现有数据
        print("\n📊 统计数据...")
        cursor.execute("SELECT COUNT(*) FROM audio_results")
        total_count = cursor.fetchone()[0]
        print(f"   总记录数: {total_count}")
        
        cursor.execute("SELECT COUNT(*) FROM audio_results WHERE origin_data_json IS NULL")
        null_count = cursor.fetchone()[0]
        print(f"   origin_data_json 为 NULL: {null_count}")
        
        if total_count > 0 and null_count == total_count:
            print("   ℹ️  所有现有记录的 origin_data_json 为 NULL（这是正常的）")
            print("   ℹ️  新任务会自动填充该字段")
        
        print("\n" + "=" * 60)
        print("✅ 数据库迁移完成！")
        print("=" * 60)
        
    except pymysql.Error as e:
        print(f"\n❌ 数据库错误: {e}")
        if connection:
            connection.rollback()
        return False
    
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        if connection:
            cursor.close()
            connection.close()
            print("\n🔒 数据库连接已关闭")
    
    return True


if __name__ == "__main__":
    success = execute_migration()
    exit(0 if success else 1)
