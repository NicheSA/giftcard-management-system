import os
from dotenv import load_dotenv

# تحميل متغيرات البيئة
load_dotenv()

class PaymobConfig:
    """إعدادات Paymob لبوابة الدفع ومفاتيح API"""
    
    # مفاتيح API الأساسية
    API_KEY = os.getenv('PAYMOB_API_KEY')
    PUBLIC_KEY = os.getenv('PAYMOB_PUBLIC_KEY')
    IFRAME_ID = os.getenv('PAYMOB_IFRAME_ID')
    INTEGRATION_ID = os.getenv('PAYMOB_INTEGRATION_ID')
    HMAC_SECRET = os.getenv('PAYMOB_HMAC_SECRET')
    
    # عناوين URL الخاصة بـ Paymob السعودية
    BASE_URL = "https://ksa.paymob.com/api"
    AUTH_URL = f"{BASE_URL}/auth/tokens"
    ORDER_URL = f"{BASE_URL}/ecommerce/orders"
    PAYMENT_KEY_URL = f"{BASE_URL}/acceptance/payment_keys"
    IFRAME_BASE_URL = "https://ksa.paymob.com/api/acceptance/iframes"
    
    # عناوين URL للـ Intention API الجديد
    INTENTION_URL = "https://ksa.paymob.com/v1/intention/"
    UNIFIED_CHECKOUT_URL = "https://ksa.paymob.com/unifiedcheckout/"
    
    # عناوين Callback URLs
    PROCESSED_CALLBACK_URL = os.getenv('PAYMOB_PROCESSED_CALLBACK_URL')
    RESPONSE_CALLBACK_URL = os.getenv('PAYMOB_RESPONSE_CALLBACK_URL')
    SUCCESS_URL = os.getenv('PAYMOB_SUCCESS_URL')
    ERROR_URL = os.getenv('PAYMOB_ERROR_URL')
    CALLBACK_URL = os.getenv('PAYMOB_CALLBACK_URL')
    
    # إعدادات الأمان
    HMAC_SECRET = os.getenv('PAYMOB_HMAC_SECRET', '')
    
    # إعدادات الطلبات
    DEFAULT_CURRENCY = 'SAR'
    DEFAULT_COUNTRY = 'SA'
    DEFAULT_CITY = 'Riyadh'
    
    # مهلة انتهاء مفتاح الدفع (بالثواني)
    PAYMENT_KEY_EXPIRATION = 3600
    
    # التحقق من صحة الإعدادات
    @classmethod
    def validate(cls):
        """التحقق من وجود جميع الإعدادات المطلوبة"""
        required_settings = [
            ('API_KEY', cls.API_KEY),
            ('PUBLIC_KEY', cls.PUBLIC_KEY),
            ('IFRAME_ID', cls.IFRAME_ID),
            ('INTEGRATION_ID', cls.INTEGRATION_ID)
        ]
        
        missing_settings = []
        for name, value in required_settings:
            if not value:
                missing_settings.append(name)
        
        if missing_settings:
            raise ValueError(f"الإعدادات المطلوبة مفقودة: {', '.join(missing_settings)}")
        
        return True

class AppConfig:
    """إعدادات التطبيق العامة"""
    
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'your_secret_key_here_change_in_production')
    DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    HOST = os.getenv('FLASK_HOST', '127.0.0.1')
    PORT = int(os.getenv('FLASK_PORT', '8080'))
    
    # مجلد البيانات
    DATA_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
    
    # مجلد رفع الملفات
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
    
    # إعدادات الجلسة
    SESSION_TIMEOUT = 3600  # ساعة واحدة