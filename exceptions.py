"""استثناءات مخصصة لتطبيق بطاقات الهدايا"""

class PaymobError(Exception):
    """استثناء عام لأخطاء Paymob"""
    def __init__(self, message, error_code=None, response_data=None):
        self.message = message
        self.error_code = error_code
        self.response_data = response_data
        super().__init__(self.message)

class PaymobAuthenticationError(PaymobError):
    """خطأ في المصادقة مع Paymob"""
    pass

class PaymobOrderError(PaymobError):
    """خطأ في تسجيل الطلب"""
    pass

class PaymobPaymentKeyError(PaymobError):
    """خطأ في الحصول على مفتاح الدفع"""
    pass

class PaymobConfigurationError(PaymobError):
    """خطأ في إعدادات Paymob"""
    pass

class PaymobConnectionError(PaymobError):
    """خطأ في الاتصال بخدمة Paymob"""
    pass

class CardDataValidationError(Exception):
    """خطأ في التحقق من صحة بيانات البطاقة"""
    def __init__(self, field, message):
        self.field = field
        self.message = message
        super().__init__(f"خطأ في الحقل '{field}': {message}")

class UserDataError(Exception):
    """خطأ في بيانات المستخدم"""
    pass