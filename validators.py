"""وحدة التحقق من صحة البيانات"""

import re
from typing import Dict, Any, List
from exceptions import CardDataValidationError, UserDataError

class CardDataValidator:
    """فئة للتحقق من صحة بيانات البطاقة"""
    
    @classmethod
    def get_supported_card_types(cls):
        """الحصول على أنواع البطاقات المدعومة من قاعدة البيانات"""
        try:
            from product_manager import ProductManager
            product_manager = ProductManager()
            products = product_manager.get_all_products()
            return list(set(product['name'] for product in products))
        except:
            # في حالة فشل الوصول لقاعدة البيانات، استخدم القائمة الافتراضية
            return ['زواج', 'تخرج', 'تهنئة']
    
    @classmethod
    def get_supported_card_values(cls):
        """الحصول على قيم البطاقات المدعومة من قاعدة البيانات"""
        try:
            from product_manager import ProductManager
            product_manager = ProductManager()
            products = product_manager.get_all_products()
            return list(set(product['price'] for product in products))
        except:
            # في حالة فشل الوصول لقاعدة البيانات، استخدم القائمة الافتراضية
            return [50, 100, 150]
    
    @classmethod
    def validate_card_type(cls, card_type: str) -> bool:
        """التحقق من نوع البطاقة"""
        if not card_type or not isinstance(card_type, str):
            raise CardDataValidationError('card_type', 'نوع البطاقة مطلوب')
        
        supported_types = cls.get_supported_card_types()
        if card_type.strip() not in supported_types:
            raise CardDataValidationError(
                'card_type', 
                f'نوع البطاقة غير مدعوم. الأنواع المدعومة: {", ".join(supported_types)}'
            )
        
        return True
    
    @classmethod
    def validate_card_value(cls, card_value: Any) -> bool:
        """التحقق من قيمة البطاقة"""
        if not card_value:
            raise CardDataValidationError('card_value', 'قيمة البطاقة مطلوبة')
        
        try:
            value = float(card_value)
        except (ValueError, TypeError):
            raise CardDataValidationError('card_value', 'قيمة البطاقة يجب أن تكون رقماً')
        
        if value <= 0:
            raise CardDataValidationError('card_value', 'قيمة البطاقة يجب أن تكون أكبر من صفر')
        
        supported_values = cls.get_supported_card_values()
        if value not in supported_values:
            raise CardDataValidationError(
                'card_value',
                f'قيمة البطاقة غير مدعومة. القيم المدعومة: {", ".join(map(str, supported_values))} ريال'
            )
        
        return True
    
    @classmethod
    def validate_sender_name(cls, sender_name: str) -> bool:
        """التحقق من اسم المرسل"""
        if not sender_name or not isinstance(sender_name, str):
            raise CardDataValidationError('sender_name', 'اسم المرسل مطلوب')
        
        sender_name = sender_name.strip()
        if len(sender_name) < 2:
            raise CardDataValidationError('sender_name', 'اسم المرسل يجب أن يكون حرفين على الأقل')
        
        if len(sender_name) > 50:
            raise CardDataValidationError('sender_name', 'اسم المرسل يجب أن يكون أقل من 50 حرف')
        
        # التحقق من وجود أحرف صالحة فقط (عربي وإنجليزي ومسافات)
        if not re.match(r'^[\u0600-\u06FFa-zA-Z\s]+$', sender_name):
            raise CardDataValidationError('sender_name', 'اسم المرسل يجب أن يحتوي على أحرف عربية أو إنجليزية فقط')
        
        return True
    
    @classmethod
    def validate_recipient_name(cls, recipient_name: str) -> bool:
        """التحقق من اسم المستقبل"""
        if not recipient_name or not isinstance(recipient_name, str):
            raise CardDataValidationError('recipient_name', 'اسم المستقبل مطلوب')
        
        recipient_name = recipient_name.strip()
        if len(recipient_name) < 2:
            raise CardDataValidationError('recipient_name', 'اسم المستقبل يجب أن يكون حرفين على الأقل')
        
        if len(recipient_name) > 50:
            raise CardDataValidationError('recipient_name', 'اسم المستقبل يجب أن يكون أقل من 50 حرف')
        
        # التحقق من وجود أحرف صالحة فقط (عربي وإنجليزي ومسافات)
        if not re.match(r'^[\u0600-\u06FFa-zA-Z\s]+$', recipient_name):
            raise CardDataValidationError('recipient_name', 'اسم المستقبل يجب أن يحتوي على أحرف عربية أو إنجليزية فقط')
        
        return True
    
    @classmethod
    def validate_phone_number(cls, phone: str) -> bool:
        """التحقق من رقم الجوال السعودي"""
        if not phone or not isinstance(phone, str):
            raise CardDataValidationError('user_phone', 'رقم الجوال مطلوب')
        
        # إزالة المسافات والرموز
        phone = re.sub(r'[\s\-\(\)\+]', '', phone)
        
        # التحقق من صيغة الرقم السعودي
        saudi_phone_pattern = r'^(\+966|966|0)?5[0-9]{8}$'
        
        if not re.match(saudi_phone_pattern, phone):
            raise CardDataValidationError(
                'user_phone', 
                'رقم الجوال غير صحيح. يجب أن يكون رقم جوال سعودي صالح (مثال: 0501234567)'
            )
        
        return True
    
    @classmethod
    def validate_email(cls, email: str) -> bool:
        """التحقق من البريد الإلكتروني (اختياري)"""
        if not email:
            return True  # البريد الإلكتروني اختياري
        
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        if not re.match(email_pattern, email):
            raise CardDataValidationError('user_email', 'البريد الإلكتروني غير صحيح')
        
        return True
    
    @classmethod
    def validate_card_data(cls, card_data: Dict[str, Any]) -> Dict[str, Any]:
        """التحقق من جميع بيانات البطاقة"""
        if not isinstance(card_data, dict):
            raise CardDataValidationError('card_data', 'بيانات البطاقة يجب أن تكون من نوع dict')
        
        # التحقق من الحقول المطلوبة
        required_fields = ['card_type', 'card_value', 'sender_name', 'recipient_name', 'user_phone']
        
        for field in required_fields:
            if field not in card_data:
                raise CardDataValidationError(field, f'الحقل {field} مطلوب')
        
        # التحقق من كل حقل
        cls.validate_card_type(card_data['card_type'])
        cls.validate_card_value(card_data['card_value'])
        cls.validate_sender_name(card_data['sender_name'])
        cls.validate_recipient_name(card_data['recipient_name'])
        cls.validate_phone_number(card_data['user_phone'])
        
        # التحقق من البريد الإلكتروني إذا كان موجوداً
        if 'user_email' in card_data:
            cls.validate_email(card_data['user_email'])
        
        # تنظيف البيانات
        cleaned_data = {
            'card_type': card_data['card_type'].strip(),
            'card_value': float(card_data['card_value']),
            'sender_name': card_data['sender_name'].strip(),
            'recipient_name': card_data['recipient_name'].strip(),
            'user_phone': re.sub(r'[\s\-\(\)\+]', '', card_data['user_phone']),
            'user_email': card_data.get('user_email', '').strip() if card_data.get('user_email') else None
        }
        
        return cleaned_data

class UserDataValidator:
    """فئة للتحقق من صحة بيانات المستخدم"""
    
    @classmethod
    def validate_login_data(cls, name: str, phone: str) -> Dict[str, str]:
        """التحقق من بيانات تسجيل الدخول"""
        if not name or not isinstance(name, str):
            raise UserDataError('الاسم مطلوب')
        
        name = name.strip()
        if len(name) < 2:
            raise UserDataError('الاسم يجب أن يكون حرفين على الأقل')
        
        if len(name) > 50:
            raise UserDataError('الاسم يجب أن يكون أقل من 50 حرف')
        
        # التحقق من رقم الجوال
        CardDataValidator.validate_phone_number(phone)
        
        return {
            'name': name,
            'phone': re.sub(r'[\s\-\(\)\+]', '', phone)
        }