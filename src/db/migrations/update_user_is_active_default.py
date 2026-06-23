"""
数据库迁移脚本：更新用户表 is_active 字段默认值为 False
"""

import pymysql

def update_user_is_active_default():
    """更新用户表 is_active 字段默认值为 False"""
    
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
        
        # 检查 is_active 列的当前默认值
        check_default_sql = """
            SELECT COLUMN_DEFAULT 
            FROM information_schema.columns 
            WHERE table_schema = %s 
            AND table_name = 'users' 
            AND column_name = 'is_active'
        """
        
        cursor.execute(check_default_sql, (db_config['database'],))
        current_default = cursor.fetchone()[0]
        
        print(f"当前 is_active 列默认值: {current_default}")
        
        # 如果默认值不是 0 或 False，则更新
        if current_default not in (0, '0', False, 'False'):
            # 更新默认值为 0 (False)
            alter_sql = """
                ALTER TABLE users 
                MODIFY COLUMN is_active BOOLEAN DEFAULT FALSE COMMENT '用户是否激活'
            """
            
            cursor.execute(alter_sql)
            connection.commit()
            
            print("✅ 成功更新 is_active 列默认值为 FALSE")
        else:
            print("✅ is_active 列默认值已经是 FALSE，无需更新")
        
    except Exception as e:
        print(f"❌ 更新 is_active 列默认值失败: {str(e)}")
        if connection:
            connection.rollback()
        raise
    finally:
        if connection:
            connection.close()

if __name__ == "__main__":
    update_user_is_active_default()
