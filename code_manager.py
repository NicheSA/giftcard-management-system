import sqlite3
import os
from datetime import datetime
import logging
import random
import string

logger = logging.getLogger(__name__)

class CodeManager:
    def __init__(self, db_path='giftcard_codes.db'):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """إنشاء جدول الأكواد إذا لم يكن موجوداً"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS codes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                price INTEGER NOT NULL,
                status TEXT DEFAULT 'available',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                used_at TIMESTAMP
            )
        ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("تم إنشاء قاعدة بيانات الأكواد بنجاح")
            
        except Exception as e:
            logger.error(f"خطأ في إنشاء قاعدة بيانات الأكواد: {str(e)}")
    
    def add_code(self, code, price):
        """إضافة كود جديد"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                "INSERT INTO codes (code, price) VALUES (?, ?)",
                (code.upper(), price)
            )
            
            conn.commit()
            code_id = cursor.lastrowid
            conn.close()
            
            logger.info(f"تم إضافة الكود {code} بنجاح")
            return code_id
            
        except sqlite3.IntegrityError:
            logger.warning(f"الكود {code} موجود مسبقاً")
            return None
        except Exception as e:
            logger.error(f"خطأ في إضافة الكود {code}: {str(e)}")
            return None
    
    def add_multiple_codes(self, base_code, price, quantity):
        """إضافة عدة أكواد بأرقام متسلسلة"""
        added_codes = []
        
        for i in range(quantity):
            if quantity == 1:
                code = base_code
            else:
                code = f"{base_code}{i+1:03d}"  # إضافة أرقام متسلسلة
            
            code_id = self.add_code(code, price)
            if code_id:
                added_codes.append(code)
        
        return added_codes
    
    def get_all_codes(self, price=None, status=None):
        """جلب جميع الأكواد مع إمكانية التصفية"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = "SELECT * FROM codes WHERE 1=1"
            params = []
            
            if price is not None:
                query += " AND price = ?"
                params.append(price)
            
            if status is not None:
                query += " AND status = ?"
                params.append(status)
            
            query += " ORDER BY created_at DESC"
            
            cursor.execute(query, params)
            codes = cursor.fetchall()
            conn.close()
            
            # تحويل التواريخ من strings إلى datetime objects
            result = []
            for code in codes:
                code_dict = dict(code)
                # تحويل created_at
                if code_dict.get('created_at'):
                    try:
                        code_dict['created_at'] = datetime.strptime(code_dict['created_at'], '%Y-%m-%d %H:%M:%S')
                    except:
                        code_dict['created_at'] = None
                # تحويل used_at
                if code_dict.get('used_at'):
                    try:
                        code_dict['used_at'] = datetime.strptime(code_dict['used_at'], '%Y-%m-%d %H:%M:%S')
                    except:
                        code_dict['used_at'] = None
                result.append(code_dict)
            
            return result
            
        except Exception as e:
            logger.error(f"خطأ في جلب الأكواد: {str(e)}")
            return []
    
    def get_available_code(self, price):
        """جلب كود متاح بقيمة محددة"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT * FROM codes WHERE price = ? AND status = 'available' ORDER BY created_at ASC LIMIT 1",
                (price,)
            )
            
            code = cursor.fetchone()
            conn.close()
            
            return dict(code) if code else None
            
        except Exception as e:
            logger.error(f"خطأ في جلب كود متاح: {str(e)}")
            return None
    
    def mark_code_as_used(self, code_id, card_id=None):
        """تحديد كود كمستخدم"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                "UPDATE codes SET status = 'used', used_at = CURRENT_TIMESTAMP WHERE id = ?",
                (code_id,)
            )
            
            conn.commit()
            conn.close()
            
            return cursor.rowcount > 0
            
        except Exception as e:
            logger.error(f"خطأ في تحديد الكود {code_id} كمستخدم: {str(e)}")
            return False
    
    def delete_code(self, code_id):
        """حذف كود (فقط إذا لم يتم استخدامه)"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                "DELETE FROM codes WHERE id = ? AND status = 'available'",
                (code_id,)
            )
            
            conn.commit()
            affected_rows = cursor.rowcount
            conn.close()
            
            if affected_rows > 0:
                logger.info(f"تم حذف الكود {code_id}")
                return True
            else:
                logger.warning(f"لم يتم حذف الكود {code_id} (قد يكون مستخدماً أو غير موجود)")
                return False
                
        except Exception as e:
            logger.error(f"خطأ في حذف الكود {code_id}: {str(e)}")
            return False
    
    def generate_random_code(self, length=8):
        """توليد كود عشوائي"""
        characters = string.ascii_uppercase + string.digits
        return ''.join(random.choice(characters) for _ in range(length))
    
    def set_code_method(self, method):
        """تحديد طريقة اختيار الأكواد"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO settings (key, value) 
                VALUES ('code_method', ?)
            ''', (method,))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"خطأ في تحديد طريقة الأكواد: {str(e)}")
    
    def get_code_method(self):
        """جلب طريقة اختيار الأكواد الحالية"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT value FROM settings WHERE key = "code_method"')
            result = cursor.fetchone()
            conn.close()
            return result[0] if result else 'random'
        except Exception as e:
            logger.error(f"خطأ في جلب طريقة الأكواد: {str(e)}")
            return 'random'
    
    def get_code_for_card(self, price, method='random'):
        """جلب كود للبطاقة حسب الطريقة المحددة"""
        if method == 'system':
            # استخدام أكواد النظام
            available_code = self.get_available_code(price)
            if available_code:
                return available_code['code']
            else:
                # إذا لم توجد أكواد متاحة، استخدم التوليد العشوائي
                logger.warning(f"لا توجد أكواد متاحة بقيمة {price}، سيتم استخدام التوليد العشوائي")
                return self.generate_random_code()
        else:
            # التوليد العشوائي
            return self.generate_random_code()
    
    def get_codes_stats(self):
        """جلب إحصائيات الأكواد"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # إجمالي الأكواد
            cursor.execute("SELECT COUNT(*) FROM codes")
            total_codes = cursor.fetchone()[0]
            
            # الأكواد المستخدمة
            cursor.execute("SELECT COUNT(*) FROM codes WHERE status = 'used'")
            used_codes = cursor.fetchone()[0]
            
            # الأكواد المتاحة
            available_codes = total_codes - used_codes
            
            # الأكواد حسب القيمة
            cursor.execute("""
                SELECT price, 
                       COUNT(*) as total,
                       SUM(CASE WHEN status = 'used' THEN 1 ELSE 0 END) as used,
                       SUM(CASE WHEN status = 'available' THEN 1 ELSE 0 END) as available
                FROM codes 
                GROUP BY price 
                ORDER BY price
            """)
            
            codes_by_price = cursor.fetchall()
            conn.close()
            
            return {
                'total_codes': total_codes,
                'used_codes': used_codes,
                'available_codes': available_codes,
                'codes_by_price': codes_by_price
            }
            
        except Exception as e:
            logger.error(f"خطأ في جلب إحصائيات الأكواد: {str(e)}")
            return {
                'total_codes': 0,
                'used_codes': 0,
                'available_codes': 0,
                'codes_by_price': []
            }
    
    def import_codes_from_csv(self, csv_content):
        """استيراد أكواد من محتوى CSV"""
        added_codes = []
        errors = []
        
        lines = csv_content.strip().split('\n')
        
        for i, line in enumerate(lines, 1):
            line = line.strip()
            if not line:
                continue
            
            # تقسيم السطر
            parts = line.split(',')
            if len(parts) != 2:
                errors.append(f'السطر {i}: تنسيق غير صحيح (يجب أن يحتوي على كود وقيمة مفصولين بفاصلة)')
                continue
            
            code = parts[0].strip().upper()
            try:
                price = int(parts[1].strip())
            except ValueError:
                errors.append(f'السطر {i}: السعر غير صحيح')
                continue
            
            if not code:
                errors.append(f'السطر {i}: الكود فارغ')
                continue
            
            code_id = self.add_code(code, price)
            if code_id:
                added_codes.append(code)
            else:
                errors.append(f'السطر {i}: الكود {code} موجود مسبقاً')
        
        return added_codes, errors