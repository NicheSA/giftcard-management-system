import requests
import json
import logging
from typing import Dict, Any, Optional
from config import PaymobConfig
from exceptions import (
    PaymobAuthenticationError,
    PaymobOrderError,
    PaymobPaymentKeyError,
    PaymobConfigurationError,
    PaymobConnectionError
)
from validators import CardDataValidator

# إعداد نظام السجلات
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PaymobIntentionClient:
    """عميل Paymob الجديد باستخدام Intention API"""
    
    def __init__(self):
        """تهيئة عميل Paymob الجديد"""
        try:
            PaymobConfig.validate()
        except ValueError as e:
            raise PaymobConfigurationError(str(e))
        
        self.config = PaymobConfig
        
        # إعداد جلسة HTTP
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'GiftCard-App/1.0'
        })
        
        logger.info("تم تهيئة عميل Paymob Intention API بنجاح")
    
    def _make_request(self, method: str, url: str, **kwargs) -> requests.Response:
        """إجراء طلب HTTP مع معالجة الأخطاء"""
        try:
            response = self.session.request(method, url, timeout=30, **kwargs)
            logger.debug(f"{method} {url} - Status: {response.status_code}")
            return response
        except requests.exceptions.Timeout:
            raise PaymobConnectionError("انتهت مهلة الاتصال مع Paymob")
        except requests.exceptions.ConnectionError:
            raise PaymobConnectionError("فشل الاتصال مع Paymob")
        except requests.exceptions.RequestException as e:
            raise PaymobConnectionError(f"خطأ في الطلب: {str(e)}")
    
    def create_intention(self, card_data: Dict[str, Any]) -> Dict[str, Any]:
        """إنشاء intention جديد للدفع باستخدام API الجديد"""
        try:
            logger.info("بدء إنشاء intention للدفع")
            
            # التحقق من صحة البيانات
            validated_data = CardDataValidator.validate_card_data(card_data)
            logger.info("تم التحقق من صحة البيانات")
            
            # تحويل قيمة البطاقة إلى هللة (المبلغ بالهللة)
            amount = int(validated_data['card_value'] * 100)
            
            # إعداد البيانات حسب الكود PHP الناجح
            data = {
                "amount": amount,
                "currency": "SAR",
                "payment_methods": [int(self.config.INTEGRATION_ID)],
                "items": [
                    {
                        "name": f"بطاقة هدية {validated_data['card_type']}",
                        "amount": amount,
                        "description": f"بطاقة رقمية من {validated_data['sender_name']} إلى {validated_data['recipient_name']}",
                        "quantity": 1
                    }
                ],
                "billing_data": {
                    "apartment": "1",
                    "first_name": validated_data['sender_name'],
                    "last_name": "Customer",
                    "street": "Main St",
                    "building": "123",
                    "phone_number": validated_data['user_phone'],
                    "country": "KSA",
                    "email": validated_data.get('user_email', 'customer@example.com'),
                    "floor": "1",
                    "state": "Riyadh"
                },
                "customer": {
                    "first_name": validated_data['sender_name'],
                    "last_name": "Customer",
                    "email": validated_data.get('user_email', 'customer@example.com')
                },
                "notification_url": self.config.PROCESSED_CALLBACK_URL,
                "redirection_url": self.config.RESPONSE_CALLBACK_URL,
                "extras": {"custom_data": validated_data.get('order_id', 123)}
            }
            
            # إعداد headers مع Authorization
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Token {self.config.API_KEY}"
            }
            
            # إرسال الطلب إلى Intention API
            intention_url = "https://ksa.paymob.com/v1/intention/"
            logger.info(f"إرسال طلب إلى: {intention_url}")
            
            response = self._make_request(
                'POST', 
                intention_url, 
                json=data, 
                headers=headers
            )
            
            if response.status_code not in [200, 201]:
                error_data = response.json() if response.text else {}
                error_message = error_data.get('detail', 'خطأ غير معروف في إنشاء الدفع')
                logger.error(f"فشل إنشاء intention: {error_message}")
                logger.error(f"Response: {response.text}")
                raise PaymobOrderError(
                    f"فشل إنشاء intention: {error_message}",
                    error_code=response.status_code,
                    response_data=error_data
                )
            
            result = response.json()
            logger.info(f"تم إنشاء intention بنجاح: {result}")
            
            # التحقق من وجود client_secret
            if "client_secret" not in result:
                logger.error(f"لم يتم العثور على client_secret في الاستجابة: {result}")
                raise PaymobOrderError("لم يتم الحصول على client_secret")
            
            client_secret = result["client_secret"]
            
            # إنشاء رابط الدفع
            checkout_url = f"https://ksa.paymob.com/unifiedcheckout/?publicKey={self.config.PUBLIC_KEY}&clientSecret={client_secret}"
            
            logger.info(f"تم إنشاء رابط الدفع بنجاح")
            
            return {
                'success': True,
                'client_secret': client_secret,
                'checkout_url': checkout_url,
                'amount': amount,
                'card_data': validated_data,
                'intention_response': result
            }
            
        except (PaymobAuthenticationError, PaymobOrderError, PaymobPaymentKeyError, 
                PaymobConfigurationError, PaymobConnectionError) as e:
            logger.error(f"خطأ Paymob: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'error_type': 'paymob_error'
            }
        except Exception as e:
            logger.error(f"خطأ عام في معالجة الدفع: {str(e)}")
            return {
                'success': False,
                'error': f'خطأ غير متوقع: {str(e)}',
                'error_type': 'general_error'
            }
    
    def test_connection(self) -> bool:
        """اختبار الاتصال مع Paymob Intention API"""
        try:
            logger.info("اختبار الاتصال مع Paymob Intention API")
            
            # إنشاء intention تجريبي
            test_data = {
                'card_type': 'تهنئة',  # استخدام نوع مدعوم
                'card_value': 50.0,  # 50 ريال - قيمة مدعومة
                'sender_name': 'اختبار',
                'recipient_name': 'اختبار',
                'user_phone': '+966500000000',
                'user_email': 'test@example.com'
            }
            
            result = self.create_intention(test_data)
            
            if result['success']:
                logger.info("نجح اختبار الاتصال مع Intention API!")
                return True
            else:
                logger.error(f"فشل اختبار الاتصال: {result['error']}")
                return False
                
        except Exception as e:
            logger.error(f"فشل اختبار الاتصال: {str(e)}")
            return False

# إنشاء مثيل عام للاستخدام
paymob_intention_client = PaymobIntentionClient()

# وظائف للتوافق مع الكود الحالي
def process_payment_intention(card_data):
    """معالجة الدفع باستخدام Intention API"""
    return paymob_intention_client.create_intention(card_data)

def test_intention_connection():
    """اختبار الاتصال مع Intention API"""
    return paymob_intention_client.test_connection()

if __name__ == "__main__":
    # تشغيل اختبار الاتصال عند تشغيل الملف مباشرة
    test_intention_connection()