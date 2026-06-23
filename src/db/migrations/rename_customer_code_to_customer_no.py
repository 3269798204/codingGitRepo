"""
数据库迁移脚本：将 audio_results 表的 customer_code 列重命名为 customer_no
"""

import pymysql

def rename_customer_code_to_customer_no():
    """将 audio_results 表的 customer_code 列重命名为 customer_no"""
    
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
        
        # 检查 customer_code 列是否存在
        check_column_sql = """
            SELECT COLUMN_NAME 
            FROM information_schema.columns 
            WHERE table_schema = %s 
            AND table_name = 'audio_results' 
            AND column_name = 'customer_code'
        """
        
        cursor.execute(check_column_sql, (db_config['database'],))
        customer_code_exists = cursor.fetchone()
        
        # 检查 customer_no 列是否已存在
        check_customer_no_sql = """
            SELECT COLUMN_NAME 
            FROM information_schema.columns 
            WHERE table_schema = %s 
            AND table_name = 'audio_results' 
            AND column_name = 'customer_no'
        """
        
        cursor.execute(check_customer_no_sql, (db_config['database'],))
        customer_no_exists = cursor.fetchone()
        
        print(f"customer_code 列存在: {customer_code_exists is not None}")
        print(f"customer_no 列存在: {customer_no_exists is not None}")
        
        # 如果 customer_code 存在且 customer_no 不存在，则重命名
        if customer_code_exists and not customer_no_exists:
            alter_sql = """
                ALTER TABLE audio_results 
                CHANGE COLUMN customer_code customer_no VARCHAR(256) COMMENT '客户编号'
            """
            
            cursor.execute(alter_sql)
            connection.commit()
            
            print("✅ 成功将 customer_code 列重命名为 customer_no")
        elif customer_no_exists:
            print("✅ customer_no 列已存在，无需重命名")
        else:
            print("⚠️ customer_code 列不存在，无法重命名")
        
    except Exception as e:
        print(f"❌ 重命名列失败: {str(e)}")
        if connection:
            connection.rollback()
        raise
    finally:
        if connection:
            connection.close()

if __name__ == "__main__":
    rename_customer_code_to_customer_no()
