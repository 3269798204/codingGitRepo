#!/usr/bin/env python3
"""
修复admin用户密码哈希值
"""

import hashlib
import sys
from database import db_manager

def fix_admin_password():
    """修复admin用户的密码哈希"""
    
    # 计算正确的哈希值
    password = 'admin123'
    salt = 'default_salt_change_in_production'
    correct_hash = hashlib.sha256((password + salt).encode('utf-8')).hexdigest()
    
    print("=" * 60)
    print("🔧 修复admin用户密码哈希")
    print("=" * 60)
    print()
    
    # 检查admin用户是否存在
    admin_user = db_manager.get_user_by_username('admin')
    
    if not admin_user:
        print("❌ admin用户不存在，请先运行 init_db.sql")
        return False
    
    print(f"✅ 找到admin用户:")
    print(f"   用户名: {admin_user['username']}")
    print(f"   当前哈希: {admin_user['password_hash']}")
    print(f"   当前salt: {admin_user['salt']}")
    print()
    
    # 检查是否需要修复
    if admin_user['password_hash'] == correct_hash:
        print("✅ 密码哈希值已正确，无需修复")
        return True
    
    print(f"⚠️  检测到密码哈希值错误")
    print(f"   正确的哈希值: {correct_hash}")
    print()
    
    # 更新数据库
    try:
        from sqlalchemy import text
        
        with db_manager.engine.connect() as conn:
            update_sql = text("""
                UPDATE users 
                SET password_hash = :hash_value,
                    salt = :salt_value
                WHERE username = 'admin'
            """)
            
            result = conn.execute(update_sql, {
                'hash_value': correct_hash,
                'salt_value': salt
            })
            conn.commit()
        
        print("✅ 密码哈希值已更新")
        print()
        
        # 验证修复
        updated_user = db_manager.get_user_by_username('admin')
        if updated_user and updated_user['password_hash'] == correct_hash:
            print("✅ 验证成功！admin用户密码已修复")
            print()
            print("登录信息:")
            print(f"   用户名: admin")
            print(f"   密码: admin123")
            print()
            return True
        else:
            print("❌ 验证失败，请手动检查数据库")
            return False
            
    except Exception as e:
        print(f"❌ 更新失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = fix_admin_password()
    sys.exit(0 if success else 1)
