import os
import json
import hashlib
from datetime import datetime
from config import AppConfig

class AdminManager:
    """مدير النظام الإداري للتحكم في المستخدمين والصلاحيات"""
    
    def __init__(self):
        self.admin_file = os.path.join(AppConfig.DATA_FOLDER, 'admins.json')
        self._ensure_admin_file_exists()
    
    def _ensure_admin_file_exists(self):
        """التأكد من وجود ملف المديرين وإنشاء مدير افتراضي"""
        if not os.path.exists(self.admin_file):
            default_admin = {
                'id': 1,
                'email': 'admin@giftcard.sa',
                'password': self._hash_password('admin123'),
                'name': 'مدير النظام',
                'role': 'super_admin',
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'is_active': True
            }
            self._save_admins([default_admin])
    
    def _hash_password(self, password):
        """تشفير كلمة المرور"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def _load_admins(self):
        """تحميل قائمة المديرين"""
        try:
            with open(self.admin_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    
    def _save_admins(self, admins):
        """حفظ قائمة المديرين"""
        with open(self.admin_file, 'w', encoding='utf-8') as f:
            json.dump(admins, f, ensure_ascii=False, indent=4)
    
    def authenticate_admin(self, email, password):
        """التحقق من صحة بيانات تسجيل دخول المدير"""
        admins = self._load_admins()
        hashed_password = self._hash_password(password)
        
        for admin in admins:
            if (admin['email'] == email and 
                admin['password'] == hashed_password and 
                admin['is_active']):
                return {
                    'id': admin['id'],
                    'email': admin['email'],
                    'name': admin['name'],
                    'role': admin['role']
                }
        return None
    
    def add_admin(self, email, password, name, role='admin'):
        """إضافة مدير جديد"""
        admins = self._load_admins()
        
        # التحقق من عدم وجود الإيميل مسبقاً
        for admin in admins:
            if admin['email'] == email:
                return {'success': False, 'error': 'الإيميل موجود مسبقاً'}
        
        # إنشاء معرف جديد
        new_id = max([admin['id'] for admin in admins], default=0) + 1
        
        new_admin = {
            'id': new_id,
            'email': email,
            'password': self._hash_password(password),
            'name': name,
            'role': role,
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'is_active': True
        }
        
        admins.append(new_admin)
        self._save_admins(admins)
        
        return {'success': True, 'admin_id': new_id}
    
    def get_all_admins(self):
        """الحصول على جميع المديرين"""
        admins = self._load_admins()
        # إزالة كلمات المرور من النتائج
        for admin in admins:
            admin.pop('password', None)
        return admins
    
    def update_admin_status(self, admin_id, is_active):
        """تحديث حالة المدير (تفعيل/إلغاء تفعيل)"""
        admins = self._load_admins()
        
        for admin in admins:
            if admin['id'] == admin_id:
                admin['is_active'] = is_active
                self._save_admins(admins)
                return {'success': True}
        
        return {'success': False, 'error': 'المدير غير موجود'}
    
    def delete_admin(self, admin_id):
        """حذف مدير"""
        admins = self._load_admins()
        
        # منع حذف المدير الرئيسي
        admin_to_delete = next((admin for admin in admins if admin['id'] == admin_id), None)
        if admin_to_delete and admin_to_delete['role'] == 'super_admin':
            return {'success': False, 'error': 'لا يمكن حذف المدير الرئيسي'}
        
        admins = [admin for admin in admins if admin['id'] != admin_id]
        self._save_admins(admins)
        
        return {'success': True}

# إنشاء مثيل عام
admin_manager = AdminManager()