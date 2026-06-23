"""
数据库迁移脚本：为 batch_tasks 表添加 user_id 字段
"""

import pymysql

def add_user_id_column():
    """为 batch_tasks 表添加 user_id 列"""
    
    # 数据库配置
    db_config = {
        'host': 'rm-2vcww6h31l270m9sm3o.mysql.cn-chengdu.rds.aliyuncs.com',
        'port': 3306,
        'user': 'tbhx01',
        'password': 'Aa@82320020',
        'database': 'voice_analysis',
        'charset': 'utf8mb4'
    }
    
    try:
        # 连接数据库
        connection = pymysql.connect(**db_config)
        
        cursor = connection.cursor()
        
        # 检查 user_id 列是否已存在
        check_column_sql = """
            SELECT COUNT(*) 
            FROM information_schema.columns 
            WHERE table_schema = %s 
            AND table_name = 'batch_tasks' 
            AND column_name = 'user_id'
        """
        
        cursor.execute(check_column_sql, (db_config['database'],))
        column_exists = cursor.fetchone()[0]
        
        if column_exists:
            print("✅ user_id 列已存在，无需添加")
            return
        
        # 添加 user_id 列
        alter_sql = """
            ALTER TABLE batch_tasks 
            ADD COLUMN user_id VARCHAR(64) DEFAULT NULL COMMENT '用户编号维度',
            ADD INDEX idx_user_id (user_id)
        """
        
        cursor.execute(alter_sql)
        connection.commit()
        
        print("✅ 成功添加 user_id 列到 batch_tasks 表")
        
    except Exception as e:
        print(f"❌ 添加 user_id 列失败: {str(e)}")
        if connection:
            connection.rollback()
        raise
    finally:
        if connection:
            connection.close()

if __name__ == "__main__":
    add_user_id_column()
