from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import os
import json
import random
import logging
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.utils import secure_filename

# استيراد الوحدات المحسنة
from config import AppConfig
from paymob_intention_client import paymob_intention_client, process_payment_intention
from validators import CardDataValidator, UserDataValidator, UserDataError
from exceptions import CardDataValidationError, PaymobError
from product_manager import ProductManager
from admin_manager import AdminManager
from card_manager import CardManager
from code_manager import CodeManager

# إعداد نظام السجلات
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = AppConfig.SECRET_KEY
app.config['UPLOAD_FOLDER'] = AppConfig.UPLOAD_FOLDER

# إضافة Security Headers
@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    return response

# تأكد من وجود مجلد للبيانات
DATA_FOLDER = AppConfig.DATA_FOLDER
os.makedirs(DATA_FOLDER, exist_ok=True)

# تأكد من وجود مجلد رفع الملفات
os.makedirs(AppConfig.UPLOAD_FOLDER, exist_ok=True)
os.makedirs(os.path.join(AppConfig.UPLOAD_FOLDER, 'backgrounds'), exist_ok=True)

# إنشاء مدير الإدارة ومدير البطاقات ومدير المنتجات ومدير الأكواد
admin_manager = AdminManager()
card_manager = CardManager()
product_manager = ProductManager()
code_manager = CodeManager()

@app.route('/')
def index():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    try:
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        
        # التحقق من صحة البيانات
        validated_data = UserDataValidator.validate_login_data(name, phone)
        
        # حفظ بيانات المستخدم في الجلسة
        session['user_name'] = validated_data['name']
        session['user_phone'] = validated_data['phone']
        
        logger.info(f"تسجيل دخول ناجح للمستخدم: {validated_data['name']}")
        return redirect(url_for('home'))
        
    except UserDataError as e:
        logger.warning(f"خطأ في بيانات تسجيل الدخول: {str(e)}")
        return render_template('login.html', error=str(e))
    except Exception as e:
        logger.error(f"خطأ غير متوقع في تسجيل الدخول: {str(e)}")
        return render_template('login.html', error='حدث خطأ غير متوقع. يرجى المحاولة مرة أخرى')

@app.route('/home')
def home():
    if 'user_name' not in session:
        return redirect(url_for('index'))
    
    # استرجاع البطاقات السابقة للمستخدم إن وجدت
    user_cards = get_user_cards(session['user_phone'])
    
    return render_template('home.html', user_name=session['user_name'], cards=user_cards)

@app.route('/products')
def products():
    if 'user_name' not in session:
        return redirect(url_for('index'))
    
    try:
        # جلب المنتجات من ProductManager
        products = product_manager.get_all_products()
        
        # تجميع المنتجات حسب النوع
        products_by_type = {}
        for product in products:
            product_type = product['name']
            if product_type not in products_by_type:
                products_by_type[product_type] = []
            products_by_type[product_type].append(product)
        
        return render_template('products.html', products_by_type=products_by_type)
    except Exception as e:
        logger.error(f"خطأ في تحميل المنتجات: {str(e)}")
        return render_template('products.html', products_by_type={})

@app.route('/new_card')
def new_card():
    if 'user_name' not in session:
        return redirect(url_for('index'))
    
    return render_template('card_form.html')

@app.route('/card_form_with_data')
def card_form_with_data():
    if 'user_name' not in session:
        return redirect(url_for('index'))
    
    return render_template('card_form.html')

@app.route('/save_card', methods=['POST'])
def save_card():
    if 'user_name' not in session:
        return redirect(url_for('index'))
    
    try:
        # استلام معرف المنتج
        product_id = request.form.get('product_id', '').strip()
        if not product_id:
            flash('معرف المنتج مطلوب', 'error')
            return redirect(url_for('new_card'))
        
        # الحصول على بيانات المنتج من قاعدة البيانات
        product = product_manager.get_product_by_id(product_id)
        if not product:
            flash('المنتج غير موجود', 'error')
            return redirect(url_for('products'))
        
        # معالجة خلفية البطاقة - استخدام صورة الخلفية من المنتج أو اللون الافتراضي
        background_color = product.get('background_color', '#bd887e')
        background_image = product.get('background_image', '')
        
        # استلام بيانات البطاقة
        form_data = {
            'card_type': product['name'],  # استخدام اسم المنتج كنوع البطاقة
            'card_value': str(product['price']),  # استخدام سعر المنتج
            'sender_name': request.form.get('from_name', '').strip(),
            'recipient_name': request.form.get('to_name', '').strip(),
            'user_phone': session['user_phone']
        }
        
        # إضافة الرسالة (اختيارية)
        message = request.form.get('message', '').strip()
        
        # التحقق من صحة البيانات
        validated_data = CardDataValidator.validate_card_data(form_data)
        
        # تحديد الكود بناءً على طريقة الكود المحددة
        code_method = code_manager.get_code_method()
        card_code = None
        code_record = None
        
        if code_method == 'system':
            # استخدام كود من النظام (متاح فقط)
            available_code = code_manager.get_available_code(int(validated_data['card_value']))
            if available_code:
                # التحقق مرة أخرى من توفر الكود قبل الاستخدام
                code_validation = code_manager.validate_code_availability(available_code['code'])
                if code_validation:
                    card_code = available_code['code']
                    code_record = available_code
                    logger.info(f"تم استخدام كود من النظام: {card_code}")
                else:
                    logger.warning(f"الكود {available_code['code']} لم يعد متاحاً، سيتم توليد كود عشوائي")
                    card_code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
            else:
                # إذا لم يوجد كود متاح، استخدم كود عشوائي
                card_code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
                logger.warning(f"لا يوجد كود متاح في النظام للقيمة {validated_data['card_value']}, تم توليد كود عشوائي: {card_code}")
        else:
            # توليد كود عشوائي مكون من 6 أرقام
            card_code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        
        # تحديث حالة الكود إلى مستخدم فوراً إذا كان من النظام
        if code_method == 'system' and code_record:
            success = code_manager.mark_code_as_used(code_record['id'])
            if success:
                logger.info(f"تم تحديث حالة الكود {card_code} إلى مستخدم")
            else:
                logger.error(f"فشل في تحديث حالة الكود {card_code}")
        
        # إنشاء بطاقة جديدة
        card_data = {
            'id': datetime.now().strftime('%Y%m%d%H%M%S'),
            'card_type': validated_data['card_type'],
            'card_value': validated_data['card_value'],
            'sender_name': validated_data['sender_name'],
            'recipient_name': validated_data['recipient_name'],
            'message': message,
            'random_code': card_code,
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'user_phone': validated_data['user_phone'],
            'payment_status': 'pending',
            'code_method': code_method,
            'code_record_id': code_record['id'] if code_record else None,
            'background_color': background_color,
            'background_image': background_image,
            'logo_image': product.get('logo_image')
        }
        
        # حفظ بيانات البطاقة في الجلسة للاستخدام في صفحة الدفع
        session['card_data'] = card_data
        
        logger.info(f"تم إنشاء بطاقة جديدة: {card_data['id']}")
        
        # توجيه المستخدم إلى صفحة الدفع
        return redirect(url_for('payment'))
        
    except CardDataValidationError as e:
        logger.warning(f"خطأ في بيانات البطاقة: {str(e)}")
        return render_template('card_form.html', error=str(e))
    except Exception as e:
        logger.error(f"خطأ غير متوقع في حفظ البطاقة: {str(e)}")
        return render_template('card_form.html', error='حدث خطأ غير متوقع. يرجى المحاولة مرة أخرى')

@app.route('/payment')
def payment():
    if 'user_name' not in session or 'card_data' not in session:
        return redirect(url_for('index'))
    
    try:
        card_data = session['card_data']
        
        # إعداد بيانات الدفع
        payment_data = {
            'card_type': card_data['card_type'],
            'card_value': card_data['card_value'],
            'sender_name': card_data['sender_name'],  # استخدام الاسم المحدث
            'recipient_name': card_data['recipient_name'],  # استخدام الاسم المحدث
            'user_phone': card_data['user_phone'],
            'user_email': session.get('user_email', 'customer@example.com'),
            'message': card_data.get('message', '')
        }
        
        # معالجة الدفع باستخدام Intention API الجديد
        payment_result = process_payment_intention(payment_data)
        
        if not payment_result['success']:
            logger.error(f"فشل في إعداد الدفع: {payment_result['error']}")
            return render_template('card_form.html', error=f"حدث خطأ أثناء إعداد الدفع: {payment_result['error']}")
        
        # حفظ معلومات الدفع في الجلسة
        session['payment_info'] = {
            'client_secret': payment_result['client_secret'],
            'amount': payment_result['amount'],
            'checkout_url': payment_result['checkout_url']
        }
        
        logger.info(f"تم إعداد الدفع بنجاح باستخدام Intention API")
        
        # توجيه المستخدم مباشرة إلى صفحة الدفع الموحدة
        return redirect(payment_result['checkout_url'])
        
    except PaymobError as e:
        logger.error(f"خطأ في Paymob: {str(e)}")
        return render_template('card_form.html', error=f"حدث خطأ أثناء إعداد الدفع: {str(e)}")
    except Exception as e:
        logger.error(f"خطأ غير متوقع في الدفع: {str(e)}")
        return render_template('card_form.html', error='حدث خطأ غير متوقع. يرجى المحاولة مرة أخرى')

@app.route('/payment/success/intention')
def payment_success_intention():
    """صفحة نجاح الدفع - يتم توجيه المستخدم إليها بعد الدفع الناجح باستخدام Intention API"""
    try:
        # التحقق من وجود معلومات الدفع في الجلسة
        payment_info = session.get('payment_info')
        card_data = session.get('card_data')
        
        if not payment_info:
            logger.warning("لا توجد معلومات دفع في الجلسة")
            return redirect(url_for('index'))
        
        # إذا كانت بيانات البطاقة موجودة، احفظها
        card_id = None
        if card_data and card_data.get('payment_status') != 'completed':
            # تحديث حالة الدفع
            card_data['payment_status'] = 'completed'
            card_data['transaction_id'] = payment_info.get('client_secret', '')
            
            # حفظ البطاقة في قاعدة البيانات
            save_card_data(card_data)
            
            # حفظ معرف البطاقة
            card_id = card_data['id']
            
            # إزالة بيانات البطاقة من الجلسة
            session.pop('card_data', None)
            
            logger.info(f"تم حفظ البطاقة بنجاح: {card_data['id']}")
        
        logger.info("تم الوصول إلى صفحة نجاح الدفع باستخدام Intention API")
        
        # عرض صفحة النجاح
        return render_template('payment_success_intention.html', payment_info=payment_info, card_id=card_id)
        
    except Exception as e:
        logger.error(f"خطأ في صفحة نجاح الدفع: {str(e)}")
        return redirect(url_for('index'))

@app.route('/payment/error')
def payment_error():
    """صفحة خطأ الدفع - يتم توجيه المستخدم إليها في حالة فشل الدفع"""
    try:
        error_message = request.args.get('error', 'حدث خطأ أثناء عملية الدفع')
        logger.warning(f"تم الوصول إلى صفحة خطأ الدفع: {error_message}")
        
        return render_template('card_form.html', error=error_message)
        
    except Exception as e:
        logger.error(f"خطأ في صفحة خطأ الدفع: {str(e)}")
        return redirect(url_for('index'))

@app.route('/payment/callback', methods=['POST', 'GET'])
def payment_callback():
    """معالجة callback من Paymob Intention API"""
    try:
        logger.info(f"تم استلام callback من Paymob: {request.method}")
        logger.info(f"البيانات المستلمة: {request.get_json() if request.is_json else request.form.to_dict()}")
        
        # يمكن إضافة منطق معالجة إضافي هنا حسب الحاجة
        # مثل تحديث حالة الطلب في قاعدة البيانات
        
        return {'status': 'success'}, 200
        
    except Exception as e:
        logger.error(f"خطأ في معالجة callback: {str(e)}")
        return {'status': 'error', 'message': str(e)}, 500

@app.route('/payment/callback/processed', methods=['POST'])
def payment_processed_callback():
    """معالجة استجابة الدفع من Paymob (استدعاء خلفي) - محدث للاستخدام مع Intention API"""
    try:
        # الحصول على البيانات من Paymob
        data = request.get_json() or request.form.to_dict()
        
        if not data:
            logger.warning("تم استلام callback فارغ من Paymob")
            return jsonify({'status': 'error', 'message': 'No data received'}), 400
        
        # معالجة حالة الدفع
        payment_status = data.get('success', False)
        order_id = data.get('order', {}).get('id', 'unknown')
        
        logger.info(f"تم استلام callback للطلب: {order_id} - الحالة: {payment_status}")
        
        if payment_status:
            logger.info(f"تم الدفع بنجاح للطلب: {order_id}")
            # هنا يمكن تحديث قاعدة البيانات أو إرسال إشعارات
        else:
            logger.warning(f"فشل الدفع للطلب: {order_id}")
        
        return jsonify({'status': 'success'}), 200
            
    except Exception as e:
        logger.error(f"خطأ في معالجة callback: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500

@app.route('/payment/callback/response', methods=['GET'])
def payment_response_callback():
    """معالجة استجابة الدفع من Paymob (إعادة توجيه المستخدم)"""
    # التحقق من وجود بيانات البطاقة في الجلسة
    if 'card_data' not in session:
        return redirect(url_for('home'))
    
    # الحصول على معلمات الاستجابة
    success = request.args.get('success')
    transaction_id = request.args.get('id')
    
    if success == 'true':
        # استرجاع بيانات البطاقة من الجلسة
        card_data = session['card_data']
        
        # تحديث حالة الدفع
        card_data['payment_status'] = 'completed'
        card_data['transaction_id'] = transaction_id
        
        # حفظ البطاقة في قاعدة البيانات
        save_card_data(card_data)
        
        # إزالة بيانات البطاقة ومعلومات الدفع من الجلسة
        card_id = card_data['id']
        session.pop('card_data', None)
        session.pop('payment_info', None)
        
        # عرض صفحة نجاح الدفع
        return render_template('payment_success.html', 
                              card_data=card_data, 
                              card_id=card_id,
                              transaction_id=transaction_id,
                              transaction_date=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    else:
        # في حالة فشل الدفع، إعادة توجيه المستخدم إلى صفحة النموذج مع رسالة خطأ
        return render_template('card_form.html', error='فشلت عملية الدفع. يرجى المحاولة مرة أخرى.')

@app.route('/payment/success/<card_id>')
def payment_success(card_id):
    """صفحة نجاح الدفع"""
    if 'user_name' not in session:
        return redirect(url_for('index'))
    
    # استرجاع بيانات البطاقة
    card = get_card_by_id(card_id)
    
    if not card:
        return redirect(url_for('home'))
    
    return render_template('payment_success.html', 
                          card_data=card, 
                          card_id=card_id,
                          transaction_id=card.get('transaction_id', 'غير متوفر'),
                          transaction_date=card.get('created_at', datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

@app.route('/view_card/<card_id>')
def view_card(card_id):
    if 'user_name' not in session:
        return redirect(url_for('index'))
    
    # استرجاع بيانات البطاقة
    card = get_card_by_id(card_id)
    
    if not card:
        return redirect(url_for('home'))
    
    # إنشاء CSP hashes للسكريبت والستايل المضمنين
    import hashlib
    import base64
    
    # حساب hash للسكريبت المضمن (مبسط)
    script_content = '''
        function downloadCard() {
            const cardElement = document.querySelector('.gift-card');
            
            if (typeof html2canvas === 'undefined') {
                alert('المكتبة غير متاحة');
                return;
            }
            
            // تحويل البطاقة إلى صورة باستخدام html2canvas
            html2canvas(cardElement, {
                backgroundColor: null,
                scale: 2, // جودة أعلى
                logging: false,
                useCORS: true
            }).then(function(canvas) {
                // تحويل الكانفاس إلى رابط تحميل
                const dataURL = canvas.toDataURL('image/png');
                
                // إنشاء رابط تحميل وتنفيذه
                const downloadLink = document.createElement('a');
                downloadLink.href = dataURL;
                downloadLink.download = 'بطاقة_إهداء.png';
                downloadLink.click();
            });
        }
        
        function shareCard() {
            const cardUrl = window.location.href;
            
            if (navigator.share) {
                navigator.share({
                    title: 'بطاقة إهداء',
                    url: cardUrl
                });
            } else {
                navigator.clipboard.writeText(cardUrl).then(() => {
                    alert('تم نسخ الرابط!');
                }).catch(() => {
                    prompt('انسخ الرابط:', cardUrl);
                });
            }
        }
    '''
    
    script_hash = base64.b64encode(hashlib.sha256(script_content.encode('utf-8')).digest()).decode('utf-8')
    
    # حساب hash للستايل المضمن
    style_content = '''
        .saved-card-info {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 12px;
            margin-bottom: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            border-left: 4px solid #667eea;
        }
        
        .saved-card-info h3 {
            margin: 0 0 15px 0;
            color: #333;
            text-align: center;
        }
        
        .card-details {
            display: grid;
            gap: 10px;
        }
        
        .card-details p {
            margin: 0;
            padding: 8px 12px;
            background: white;
            border-radius: 6px;
            border: 1px solid #e9ecef;
        }
        
        .card-details strong {
            color: #495057;
        }
        
        .card-details span {
            color: #667eea;
            font-weight: 600;
        }
        
        .card-preview-section {
            background: white;
            padding: 20px;
            border-radius: 12px;
            margin-bottom: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        
        .card-preview-section h3 {
            margin: 0 0 20px 0;
            color: #333;
            text-align: center;
        }
    '''
    
    style_hash = base64.b64encode(hashlib.sha256(style_content.encode('utf-8')).digest()).decode('utf-8')
    
    return render_template('card_view.html', card=card, csp_script_hash=script_hash, csp_style_hash=style_hash)

@app.route('/test/card-design')
def test_card_design():
    """صفحة اختبار تصميم البطاقات مع إمكانية اختيار البطاقة الفردية"""
    try:
        # الحصول على جميع البطاقات المتاحة (النشطة فقط)
        all_products = product_manager.get_all_products()
        
        # فلترة البطاقات النشطة فقط وإضافة معلومات إضافية
        active_products = []
        for product in all_products:
            if product.get('is_active', True) and not product.get('deleted_at'):
                active_products.append({
                    'id': product['id'],
                    'name': product['name'],
                    'price': product['price'],
                    'background_color': product['background_color'],
                    'logo_image': product.get('logo_image', ''),
                    'display_name': f"{product['name']} - {product['price']} ريال"
                })
        
        # الحصول على طريقة الكود الحالية
        code_method = code_manager.get_code_method()
        
        return render_template('card_design_test.html', 
                             product_types=active_products, 
                             code_method=code_method)
    
    except Exception as e:
        logger.error(f"خطأ في تحميل صفحة اختبار التصميم: {str(e)}")
        # في حالة الخطأ، عرض أنواع افتراضية
        default_types = [
            {'name': 'زواج', 'background_color': '#ff6b6b', 'logo_image': ''},
            {'name': 'مولود', 'background_color': '#4ecdc4', 'logo_image': ''},
            {'name': 'تخرج', 'background_color': '#f39c12', 'logo_image': ''},
            {'name': 'عيد ميلاد', 'background_color': '#e74c3c', 'logo_image': ''}
        ]
        return render_template('card_design_test.html', 
                             product_types=default_types, 
                             code_method='random')

@app.route('/api/get-preview-code/<int:price>')
def get_preview_code(price):
    """جلب كود للمعاينة حسب طريقة الكود المحددة"""
    try:
        code_method = code_manager.get_code_method()
        
        if code_method == 'system':
            # استخدام كود من النظام
            available_code = code_manager.get_available_code(price)
            if available_code:
                return jsonify({
                    'success': True,
                    'code': available_code['code'],
                    'method': 'system',
                    'message': 'تم جلب كود من النظام'
                })
            else:
                # إذا لم يوجد كود متاح، استخدم كود عشوائي
                random_code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
                return jsonify({
                    'success': True,
                    'code': random_code,
                    'method': 'random_fallback',
                    'message': 'لا يوجد كود متاح في النظام، تم توليد كود عشوائي'
                })
        else:
            # توليد كود عشوائي
            random_code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
            return jsonify({
                'success': True,
                'code': random_code,
                'method': 'random',
                'message': 'تم توليد كود عشوائي'
            })
            
    except Exception as e:
        logger.error(f"خطأ في جلب كود المعاينة: {str(e)}")
        # في حالة الخطأ، إرجاع كود عشوائي
        random_code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        return jsonify({
            'success': False,
            'code': random_code,
            'method': 'error_fallback',
            'message': 'حدث خطأ، تم توليد كود عشوائي'
        })

@app.route('/test/payment-success')
def test_payment_success():
    """مسار مؤقت لاختبار صفحة نجاح الدفع بدون المرور بعملية الدفع"""
    # بيانات تجريبية للبطاقة
    test_card_data = {
        'id': 'test_123',
        'card_type': 'نون',
        'card_value': '100',
        'to_name': 'أحمد محمد',
        'from_name': 'سارة أحمد',
        'message': 'كل عام وأنت بخير! أتمنى لك عاماً مليئاً بالسعادة والنجاح.',
        'random_code': '789456',
        'transaction_id': 'TXN_TEST_123456',
        'created_at': '2024-01-15 14:30:00',
        'payment_status': 'completed'
    }
    
    return render_template('payment_success.html', 
                          card_data=test_card_data, 
                          card_id='test_123',
                          transaction_id='TXN_TEST_123456',
                          transaction_date='2024-01-15 14:30:00')

# وظائف مساعدة للتعامل مع البيانات
def get_user_cards(phone):
    """استرجاع بطاقات المستخدم"""
    cards = []
    try:
        cards_file = os.path.join(DATA_FOLDER, f'{phone}_cards.json')
        if os.path.exists(cards_file):
            with open(cards_file, 'r', encoding='utf-8') as f:
                cards = json.load(f)
        logger.info(f"تم استرجاع {len(cards)} بطاقة للمستخدم: {phone}")
    except Exception as e:
        logger.error(f"خطأ في تحميل البطاقات للمستخدم {phone}: {str(e)}")
    return cards

def save_card_data(card_data):
    """حفظ بيانات البطاقة"""
    try:
        phone = card_data['user_phone']
        cards_file = os.path.join(DATA_FOLDER, f'{phone}_cards.json')
        
        # استرجاع البطاقات الحالية
        cards = []
        if os.path.exists(cards_file):
            with open(cards_file, 'r', encoding='utf-8') as f:
                cards = json.load(f)
        
        # إضافة البطاقة الجديدة
        cards.append(card_data)
        
        # حفظ البيانات
        with open(cards_file, 'w', encoding='utf-8') as f:
            json.dump(cards, f, ensure_ascii=False, indent=4)
            
        # ملاحظة: تم تحديث حالة الكود مسبقاً عند إنشاء البطاقة
            
        logger.info(f"تم حفظ البطاقة بنجاح: {card_data['id']}")
            
    except Exception as e:
        logger.error(f"خطأ في حفظ البطاقة: {str(e)}")
        raise

def get_card_by_id(card_id):
    """البحث عن بطاقة بواسطة المعرف"""
    try:
        # البحث في جميع ملفات البطاقات
        for filename in os.listdir(DATA_FOLDER):
            if filename.endswith('_cards.json'):
                file_path = os.path.join(DATA_FOLDER, filename)
                with open(file_path, 'r', encoding='utf-8') as f:
                    cards = json.load(f)
                    for card in cards:
                        if card['id'] == card_id:
                            logger.info(f"تم العثور على البطاقة: {card_id}")
                            return card
        logger.warning(f"لم يتم العثور على البطاقة: {card_id}")
    except Exception as e:
        logger.error(f"خطأ في البحث عن البطاقة {card_id}: {str(e)}")
    return None

# ==================== روتات الداشبورد الإداري ====================

@app.route('/admin')
def admin_login():
    """صفحة تسجيل دخول الإدارة"""
    return render_template('admin_login.html')

@app.route('/admin/login', methods=['POST'])
def admin_login_post():
    """معالجة تسجيل دخول الإدارة"""
    try:
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        
        if not email or not password:
            return render_template('admin_login.html', error='يرجى إدخال البريد الإلكتروني وكلمة المرور')
        
        # التحقق من بيانات الإدارة
        admin = admin_manager.authenticate_admin(email, password)
        
        if admin:
            session['admin_id'] = admin['id']
            session['admin_email'] = admin['email']
            session['admin_role'] = admin['role']
            session['is_admin'] = True
            
            logger.info(f"تسجيل دخول إداري ناجح: {email}")
            return redirect(url_for('admin_dashboard'))
        else:
            return render_template('admin_login.html', error='بيانات تسجيل الدخول غير صحيحة')
            
    except Exception as e:
        logger.error(f"خطأ في تسجيل دخول الإدارة: {str(e)}")
        return render_template('admin_login.html', error='حدث خطأ غير متوقع')

@app.route('/admin/dashboard')
def admin_dashboard():
    """الداشبورد الرئيسي للإدارة"""
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
    
    try:
        # إحصائيات البطاقات
        stats = card_manager.get_card_statistics()
        
        # البطاقات الحديثة
        recent_cards = card_manager.get_all_cards(limit=5)
        
        return render_template('admin_dashboard.html', 
                             stats=stats, 
                             recent_cards=recent_cards,
                             admin_email=session.get('admin_email'))
                             
    except Exception as e:
        logger.error(f"خطأ في الداشبورد الإداري: {str(e)}")
        return render_template('admin_dashboard.html', error='حدث خطأ في تحميل البيانات')

@app.route('/admin/cards')
def admin_cards():
    """صفحة إدارة البطاقات"""
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
    
    try:
        # فلاتر البحث
        status_filter = request.args.get('status', '')
        type_filter = request.args.get('type', '')
        search_query = request.args.get('search', '')
        page = int(request.args.get('page', 1))
        
        # الحصول على البطاقات مع الفلاتر
        cards = card_manager.get_all_cards(
            status_filter=status_filter if status_filter else None,
            type_filter=type_filter if type_filter else None,
            search_query=search_query if search_query else None,
            page=page
        )
        
        return render_template('admin_cards.html', 
                             cards=cards,
                             current_page=page,
                             status_filter=status_filter,
                             type_filter=type_filter,
                             search_query=search_query)
                             
    except Exception as e:
        logger.error(f"خطأ في صفحة إدارة البطاقات: {str(e)}")
        return render_template('admin_cards.html', error='حدث خطأ في تحميل البطاقات')

@app.route('/admin/add_card')
def admin_add_card():
    """صفحة إضافة بطاقة جديدة"""
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
    
    return render_template('admin_add_card.html')

@app.route('/admin/add_card', methods=['POST'])
def admin_add_card_post():
    """معالجة إضافة بطاقة جديدة"""
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
    
    try:
        # استلام بيانات البطاقة
        card_data = {
            'recipient_name': request.form.get('recipient_name', '').strip(),
            'recipient_phone': request.form.get('recipient_phone', '').strip(),
            'card_type': request.form.get('card_type', '').strip(),
            'card_value': request.form.get('card_value', '').strip(),
            'message': request.form.get('message', '').strip(),
            'background_color': request.form.get('background_color', '#667eea').strip()
        }
        
        # معالجة رفع الشعار
        logo_filename = None
        if 'logo_image' in request.files:
            logo_file = request.files['logo_image']
            if logo_file and logo_file.filename != '':
                # التحقق من نوع الملف
                allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'svg'}
                if '.' in logo_file.filename and logo_file.filename.rsplit('.', 1)[1].lower() in allowed_extensions:
                    # إنشاء مجلد الشعارات إذا لم يكن موجوداً
                    import os
                    logos_dir = os.path.join('static', 'uploads', 'logos')
                    os.makedirs(logos_dir, exist_ok=True)
                    
                    # حفظ الملف
                    import uuid
                    file_extension = logo_file.filename.rsplit('.', 1)[1].lower()
                    logo_filename = f"{uuid.uuid4().hex}.{file_extension}"
                    logo_path = os.path.join(logos_dir, logo_filename)
                    logo_file.save(logo_path)
                    
                    card_data['logo_image'] = logo_filename
        
        # التحقق من البيانات
        if not all([card_data['recipient_name'], card_data['recipient_phone'], 
                   card_data['card_type'], card_data['card_value']]):
            return render_template('admin_add_card.html', 
                                 error='يرجى ملء جميع الحقول المطلوبة')
        
        # إنشاء البطاقة
        card_id = card_manager.create_card(
            recipient_name=card_data['recipient_name'],
            recipient_phone=card_data['recipient_phone'],
            card_type=card_data['card_type'],
            card_value=int(card_data['card_value']),
            message=card_data['message'],
            background_color=card_data['background_color'],
            logo_image=card_data.get('logo_image'),
            created_by_admin=session.get('admin_email')
        )
        
        logger.info(f"تم إنشاء بطاقة جديدة بواسطة الإدارة: {card_id}")
        flash('تم إنشاء البطاقة بنجاح', 'success')
        return redirect(url_for('admin_cards'))
        
    except Exception as e:
        logger.error(f"خطأ في إضافة بطاقة جديدة: {str(e)}")
        return render_template('admin_add_card.html', 
                             error='حدث خطأ في إنشاء البطاقة')

@app.route('/admin/users')
def admin_users():
    """صفحة إدارة المستخدمين"""
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
    
    # التحقق من صلاحيات الإدارة العليا
    if session.get('admin_role') != 'super_admin':
        flash('ليس لديك صلاحية للوصول إلى هذه الصفحة', 'error')
        return redirect(url_for('admin_dashboard'))
    
    try:
        admins = admin_manager.get_all_admins()
        return render_template('admin_users.html', admins=admins)
        
    except Exception as e:
        logger.error(f"خطأ في صفحة إدارة المستخدمين: {str(e)}")
        return render_template('admin_users.html', error='حدث خطأ في تحميل المستخدمين')

@app.route('/admin/add_user', methods=['POST'])
def admin_add_user():
    """إضافة مستخدم إداري جديد"""
    if not session.get('is_admin') or session.get('admin_role') != 'super_admin':
        return redirect(url_for('admin_login'))
    
    try:
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        role = request.form.get('role', '').strip()
        
        if not all([email, password, role]):
            flash('يرجى ملء جميع الحقول', 'error')
            return redirect(url_for('admin_users'))
        
        # إضافة المستخدم
        admin_manager.add_admin(email, password, role)
        
        logger.info(f"تم إضافة مستخدم إداري جديد: {email}")
        flash('تم إضافة المستخدم بنجاح', 'success')
        
    except Exception as e:
        logger.error(f"خطأ في إضافة مستخدم: {str(e)}")
        flash('حدث خطأ في إضافة المستخدم', 'error')
    
    return redirect(url_for('admin_users'))

@app.route('/admin/toggle_user/<admin_id>', methods=['POST'])
def admin_toggle_user(admin_id):
    """تفعيل/إلغاء تفعيل مستخدم"""
    if not session.get('is_admin') or session.get('admin_role') != 'super_admin':
        return redirect(url_for('admin_login'))
    
    try:
        admin_manager.toggle_admin_status(admin_id)
        flash('تم تحديث حالة المستخدم', 'success')
        
    except Exception as e:
        logger.error(f"خطأ في تحديث حالة المستخدم: {str(e)}")
        flash('حدث خطأ في تحديث حالة المستخدم', 'error')
    
    return redirect(url_for('admin_users'))

@app.route('/admin/delete_user/<admin_id>', methods=['POST'])
def admin_delete_user(admin_id):
    """حذف مستخدم إداري"""
    if not session.get('is_admin') or session.get('admin_role') != 'super_admin':
        return redirect(url_for('admin_login'))
    
    try:
        admin_manager.delete_admin(admin_id)
        flash('تم حذف المستخدم بنجاح', 'success')
        
    except Exception as e:
        logger.error(f"خطأ في حذف المستخدم: {str(e)}")
        flash('حدث خطأ في حذف المستخدم', 'error')
    
    return redirect(url_for('admin_users'))

@app.route('/admin/reports')
def admin_reports():
    """صفحة التقارير والإحصائيات"""
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
    
    try:
        # فلاتر التقارير
        period = request.args.get('period', 'month')
        card_type = request.args.get('card_type', '')
        
        # إحصائيات شاملة
        stats = card_manager.get_card_statistics()
        
        # بيانات للرسوم البيانية (يمكن تطويرها لاحقاً)
        chart_data = {
            'sales_by_month': [],
            'cards_by_type': [],
            'revenue_trend': []
        }
        
        return render_template('admin_reports.html', 
                             stats=stats,
                             chart_data=chart_data,
                             period=period,
                             card_type=card_type)
                             
    except Exception as e:
        logger.error(f"خطأ في صفحة التقارير: {str(e)}")
        # إرسال بيانات افتراضية في حالة الخطأ
        default_stats = {
            'total_cards': 0,
            'paid_cards': 0,
            'pending_cards': 0,
            'failed_cards': 0,
            'total_revenue': 0,
            'average_order_value': 0,
            'cards_by_type': {},
            'cards_by_value': {}
        }
        default_chart_data = {
            'sales_by_month': [],
            'cards_by_type': [],
            'revenue_trend': []
        }
        return render_template('admin_reports.html', 
                             stats=default_stats,
                             chart_data=default_chart_data,
                             period='month',
                             card_type='',
                             error='حدث خطأ في تحميل التقارير')

@app.route('/admin/export_report')
def admin_export_report():
    """تصدير التقارير بصيغ مختلفة"""
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
    
    try:
        format_type = request.args.get('format', 'excel')
        period = request.args.get('period', 'month')
        card_type = request.args.get('card_type', '')
        
        # الحصول على البيانات
        stats = card_manager.get_card_statistics()
        cards = card_manager.get_all_cards()
        
        if format_type == 'excel':
            # تصدير Excel (يحتاج مكتبة openpyxl)
            flash('تصدير Excel غير متاح حالياً', 'warning')
            return redirect(url_for('admin_reports'))
            
        elif format_type == 'pdf':
            # تصدير PDF (يحتاج مكتبة reportlab)
            flash('تصدير PDF غير متاح حالياً', 'warning')
            return redirect(url_for('admin_reports'))
            
        elif format_type == 'csv':
            # تصدير CSV
            import csv
            import io
            from flask import make_response
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # كتابة العناوين
            writer.writerow(['رقم البطاقة', 'النوع', 'القيمة', 'الحالة', 'تاريخ الإنشاء', 'رقم الهاتف'])
            
            # كتابة البيانات
            for card in cards:
                writer.writerow([
                    card.get('card_number', ''),
                    card.get('card_type', ''),
                    card.get('card_value', ''),
                    card.get('payment_status', ''),
                    card.get('created_at', ''),
                    card.get('phone_number', '')
                ])
            
            output.seek(0)
            
            response = make_response(output.getvalue())
            response.headers['Content-Type'] = 'text/csv; charset=utf-8'
            response.headers['Content-Disposition'] = 'attachment; filename=cards_report.csv'
            
            return response
            
        else:
            flash('صيغة التصدير غير مدعومة', 'error')
            return redirect(url_for('admin_reports'))
            
    except Exception as e:
        logger.error(f"خطأ في تصدير التقرير: {str(e)}")
        flash('حدث خطأ في تصدير التقرير', 'error')
        return redirect(url_for('admin_reports'))

@app.route('/admin/products', methods=['GET', 'POST'])
def admin_products():
    """صفحة إدارة المنتجات"""
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add':
            try:
                price = request.form.get('price', '').strip()
                background_color = request.form.get('background_color', '').strip()
                product_type = request.form.get('type', '').strip()
                
                # التحقق من النوع (إما من القائمة أو نوع جديد)
                if product_type == '__new__':
                    product_type = request.form.get('new_type', '').strip()
                
                if not all([price, background_color, product_type]):
                    flash('جميع الحقول مطلوبة', 'error')
                    return redirect(url_for('admin_products'))
                
                try:
                    price = int(price)
                    if price <= 0:
                        flash('السعر يجب أن يكون أكبر من صفر', 'error')
                        return redirect(url_for('admin_products'))
                except ValueError:
                    flash('السعر يجب أن يكون رقم صحيح', 'error')
                    return redirect(url_for('admin_products'))
                
                # التعامل مع رفع صورة الخلفية
                background_image = None
                if 'background_image' in request.files:
                    file = request.files['background_image']
                    if file and file.filename != '':
                        # التحقق من نوع الملف
                        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
                        file_extension = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
                        
                        if file_extension in allowed_extensions:
                            # إنشاء اسم ملف فريد باللغة الإنجليزية
                            import uuid
                            unique_filename = f"background_{uuid.uuid4().hex[:8]}.{file_extension}"
                            
                            # إنشاء مجلد الخلفيات إذا لم يكن موجوداً
                            backgrounds_dir = os.path.join('static', 'uploads', 'backgrounds')
                            os.makedirs(backgrounds_dir, exist_ok=True)
                            
                            # حفظ الملف
                            file_path = os.path.join(backgrounds_dir, unique_filename)
                            file.save(file_path)
                            background_image = f"uploads/backgrounds/{unique_filename}"
                        else:
                            flash('نوع الملف غير مدعوم. يرجى استخدام PNG, JPG, JPEG, GIF, أو WEBP', 'error')
                            return redirect(url_for('admin_products'))
                
                # التعامل مع رفع الشعار
                logo_image = None
                if 'logo_image' in request.files:
                    file = request.files['logo_image']
                    if file and file.filename != '':
                        # التحقق من نوع الملف
                        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'svg'}
                        file_extension = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
                        
                        if file_extension in allowed_extensions:
                            # إنشاء اسم ملف فريد باللغة الإنجليزية
                            import uuid
                            unique_filename = f"product_logo_{uuid.uuid4().hex[:8]}.{file_extension}"
                            
                            # إنشاء مجلد الشعارات إذا لم يكن موجوداً
                            logos_dir = os.path.join('static', 'uploads', 'product_logos')
                            os.makedirs(logos_dir, exist_ok=True)
                            
                            # حفظ الملف
                            file_path = os.path.join(logos_dir, unique_filename)
                            file.save(file_path)
                            logo_image = f"uploads/product_logos/{unique_filename}"
                        else:
                            flash('نوع الملف غير مدعوم. يرجى استخدام PNG, JPG, JPEG, GIF, أو SVG', 'error')
                            return redirect(url_for('admin_products'))
                
                # استخدام نوع المنتج كاسم المنتج
                product_manager.add_product(product_type, price, background_color, logo_image, background_image)
                flash('تم إضافة المنتج بنجاح', 'success')
                
            except Exception as e:
                logger.error(f"خطأ في إضافة المنتج: {str(e)}")
                flash('حدث خطأ في إضافة المنتج', 'error')
        
        elif action == 'update':
            try:
                product_id = request.form.get('product_id')
                price = request.form.get('price', '').strip()
                background_color = request.form.get('background_color', '').strip()
                product_type = request.form.get('type', '').strip()
                
                # التحقق من النوع (إما من القائمة أو نوع جديد)
                if product_type == '__new__':
                    product_type = request.form.get('new_type', '').strip()
                
                if not all([product_id, price, background_color, product_type]):
                    flash('جميع الحقول مطلوبة', 'error')
                    return redirect(url_for('admin_products'))
                
                try:
                    price = int(price)
                    if price <= 0:
                        flash('السعر يجب أن يكون أكبر من صفر', 'error')
                        return redirect(url_for('admin_products'))
                except ValueError:
                    flash('السعر يجب أن يكون رقم صحيح', 'error')
                    return redirect(url_for('admin_products'))
                
                # الحصول على الملفات القديمة لحذفها لاحقاً
                old_product = product_manager.get_product_by_id(product_id)
                old_logo_path = None
                old_background_path = None
                if old_product:
                    if old_product.get('logo_image'):
                        old_logo_path = os.path.join('static', old_product['logo_image'])
                    if old_product.get('background_image'):
                        old_background_path = os.path.join('static', old_product['background_image'])
                
                # التعامل مع رفع صورة الخلفية
                background_image = old_product.get('background_image') if old_product else None
                if 'background_image' in request.files:
                    file = request.files['background_image']
                    if file and file.filename != '':
                        # التحقق من نوع الملف
                        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
                        file_extension = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
                        
                        if file_extension in allowed_extensions:
                            # إنشاء اسم ملف فريد باللغة الإنجليزية
                            import uuid
                            unique_filename = f"background_{uuid.uuid4().hex[:8]}.{file_extension}"
                            
                            # إنشاء مجلد الخلفيات إذا لم يكن موجوداً
                            backgrounds_dir = os.path.join('static', 'uploads', 'backgrounds')
                            os.makedirs(backgrounds_dir, exist_ok=True)
                            
                            # حفظ الملف
                            file_path = os.path.join(backgrounds_dir, unique_filename)
                            file.save(file_path)
                            background_image = f"uploads/backgrounds/{unique_filename}"
                        else:
                            flash('نوع الملف غير مدعوم. يرجى استخدام PNG, JPG, JPEG, GIF, أو WEBP', 'error')
                            return redirect(url_for('admin_products'))
                
                # التعامل مع رفع الشعار
                logo_image = old_product.get('logo_image') if old_product else None
                if 'logo_image' in request.files:
                    file = request.files['logo_image']
                    if file and file.filename != '':
                        # التحقق من نوع الملف
                        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'svg'}
                        file_extension = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
                        
                        if file_extension in allowed_extensions:
                            # إنشاء اسم ملف فريد باللغة الإنجليزية
                            import uuid
                            unique_filename = f"product_logo_{uuid.uuid4().hex[:8]}.{file_extension}"
                            
                            # إنشاء مجلد الشعارات إذا لم يكن موجوداً
                            logos_dir = os.path.join('static', 'uploads', 'product_logos')
                            os.makedirs(logos_dir, exist_ok=True)
                            
                            # حفظ الملف
                            file_path = os.path.join(logos_dir, unique_filename)
                            file.save(file_path)
                            logo_image = f"uploads/product_logos/{unique_filename}"
                        else:
                            flash('نوع الملف غير مدعوم. يرجى استخدام PNG, JPG, JPEG, GIF, أو SVG', 'error')
                            return redirect(url_for('admin_products'))
                
                product_manager.update_product(product_id, product_type, price, background_color, logo_image, background_image)
                
                # حذف الملفات القديمة إذا تم رفع ملفات جديدة
                if logo_image and old_logo_path and os.path.exists(old_logo_path) and logo_image != old_product.get('logo_image'):
                    try:
                        os.remove(old_logo_path)
                        logger.info(f"تم حذف الشعار القديم: {old_logo_path}")
                    except Exception as e:
                        logger.warning(f"فشل في حذف الشعار القديم {old_logo_path}: {str(e)}")
                
                if background_image and old_background_path and os.path.exists(old_background_path) and background_image != old_product.get('background_image'):
                    try:
                        os.remove(old_background_path)
                        logger.info(f"تم حذف الخلفية القديمة: {old_background_path}")
                    except Exception as e:
                        logger.warning(f"فشل في حذف الخلفية القديمة {old_background_path}: {str(e)}")
                
                flash('تم تحديث المنتج بنجاح', 'success')
                
            except Exception as e:
                logger.error(f"خطأ في تحديث المنتج: {str(e)}")
                flash('حدث خطأ في تحديث المنتج', 'error')
        
        elif action == 'delete':
            try:
                product_id = request.form.get('product_id')
                if product_id:
                    product_manager.delete_product(product_id)
                    flash('تم حذف المنتج بنجاح', 'success')
                else:
                    flash('معرف المنتج مطلوب', 'error')
                    
            except Exception as e:
                logger.error(f"خطأ في حذف المنتج: {str(e)}")
                flash('حدث خطأ في حذف المنتج', 'error')
        
        return redirect(url_for('admin_products'))
    
    # GET request
    try:
        products = product_manager.get_all_products()
        stats = product_manager.get_product_statistics()
        unique_types = product_manager.get_unique_product_types()
        
        return render_template('admin_card_products.html', 
                             products=products, 
                             stats=stats,
                             unique_types=unique_types)
    except Exception as e:
        logger.error(f"خطأ في تحميل صفحة المنتجات: {str(e)}")
        flash('حدث خطأ في تحميل المنتجات', 'error')
        return render_template('admin_card_products.html', 
                             products=[], 
                             stats={'total_products': 0, 'products_by_type': {}, 'price_ranges': {}, 'average_price': 0},
                             unique_types=[])

@app.route('/admin/products/get/<product_id>', methods=['GET'])
def get_product(product_id):
    """جلب بيانات منتج محدد"""
    if not session.get('is_admin'):
        return jsonify({'error': 'غير مصرح'}), 403
    
    try:
        product = product_manager.get_product_by_id(product_id)
        if product:
            return jsonify(product)
        else:
            return jsonify({'error': 'المنتج غير موجود'}), 404
    except Exception as e:
        logger.error(f"خطأ في جلب المنتج {product_id}: {str(e)}")
        return jsonify({'error': 'حدث خطأ في جلب بيانات المنتج'}), 500

@app.route('/admin/products/add', methods=['POST'])
def admin_add_product():
    """إضافة منتج جديد"""
    if not session.get('is_admin'):
        return jsonify({'success': False, 'message': 'غير مصرح'}), 403
    
    try:
        name = request.form.get('name', '').strip()
        price = request.form.get('price', '').strip()
        background_color = request.form.get('background_color', '').strip()
        
        if not name or not price or not background_color:
            return jsonify({'success': False, 'message': 'جميع الحقول مطلوبة'})
        
        # التحقق من صحة السعر
        try:
            price = int(price)
            if price <= 0:
                return jsonify({'success': False, 'message': 'السعر يجب أن يكون أكبر من صفر'})
        except ValueError:
            return jsonify({'success': False, 'message': 'السعر يجب أن يكون رقماً صحيحاً'})
        
        # إضافة المنتج
        new_product = product_manager.add_product(name, price, background_color)
        
        if new_product:
            return jsonify({'success': True, 'message': 'تم إضافة المنتج بنجاح', 'product': new_product})
        else:
            return jsonify({'success': False, 'message': 'فشل في إضافة المنتج'})
            
    except Exception as e:
        logger.error(f"خطأ في إضافة المنتج: {str(e)}")
        return jsonify({'success': False, 'message': 'حدث خطأ في إضافة المنتج'})

@app.route('/admin/products/update/<product_id>', methods=['POST'])
def admin_update_product(product_id):
    """تحديث منتج موجود"""
    if not session.get('is_admin'):
        return jsonify({'success': False, 'message': 'غير مصرح'}), 403
    
    try:
        name = request.form.get('name', '').strip()
        price = request.form.get('price', '').strip()
        background_color = request.form.get('background_color', '').strip()
        
        if not name or not price or not background_color:
            return jsonify({'success': False, 'message': 'جميع الحقول مطلوبة'})
        
        # التحقق من صحة السعر
        try:
            price = int(price)
            if price <= 0:
                return jsonify({'success': False, 'message': 'السعر يجب أن يكون أكبر من صفر'})
        except ValueError:
            return jsonify({'success': False, 'message': 'السعر يجب أن يكون رقماً صحيحاً'})
        
        # تحديث المنتج
        updated_product = product_manager.update_product(product_id, name, price, background_color)
        
        if updated_product:
            return jsonify({'success': True, 'message': 'تم تحديث المنتج بنجاح', 'product': updated_product})
        else:
            return jsonify({'success': False, 'message': 'المنتج غير موجود'})
            
    except Exception as e:
        logger.error(f"خطأ في تحديث المنتج: {str(e)}")
        return jsonify({'success': False, 'message': 'حدث خطأ في تحديث المنتج'})

@app.route('/admin/products/delete/<product_id>', methods=['POST'])
def admin_delete_product(product_id):
    """حذف منتج"""
    if not session.get('is_admin'):
        return jsonify({'success': False, 'message': 'غير مصرح'}), 403
    
    try:
        success = product_manager.delete_product(product_id)
        
        if success:
            return jsonify({'success': True, 'message': 'تم حذف المنتج بنجاح'})
        else:
            return jsonify({'success': False, 'message': 'المنتج غير موجود'})
            
    except Exception as e:
        logger.error(f"خطأ في حذف المنتج: {str(e)}")
        return jsonify({'success': False, 'message': 'حدث خطأ في حذف المنتج'})

@app.route('/admin/logout')
def admin_logout():
    """تسجيل خروج المدير"""
    session.pop('admin_id', None)
    session.pop('admin_email', None)
    session.pop('admin_role', None)
    session.pop('is_admin', None)
    
    flash('تم تسجيل الخروج بنجاح', 'success')
    return redirect(url_for('admin_login'))

@app.route('/admin/codes')
def admin_codes():
    """صفحة إدارة الأكواد"""
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
    
    try:
        # جلب جميع المنتجات للقائمة المنسدلة
        products = product_manager.get_all_products()
        
        # جلب الأكواد المتاحة والمستخدمة بشكل منفصل
        available_codes = code_manager.get_codes_by_status('available')
        used_codes = code_manager.get_codes_by_status('used')
        
        # جلب الطريقة الحالية
        current_method = code_manager.get_code_method()
        
        return render_template('admin_codes.html', 
                             products=products,
                             available_codes=available_codes,
                             used_codes=used_codes,
                             current_method=current_method)
    except Exception as e:
        logger.error(f"خطأ في صفحة إدارة الأكواد: {str(e)}")
        flash('حدث خطأ في تحميل الصفحة', 'error')
        return redirect(url_for('admin_dashboard'))

@app.route('/admin/codes/method', methods=['POST'])
def admin_set_code_method():
    """تحديد طريقة اختيار الكود"""
    if not session.get('is_admin'):
        return jsonify({'error': 'غير مصرح'}), 403
    
    try:
        data = request.get_json()
        method = data.get('method')
        
        if method in ['random', 'system']:
            code_manager.set_code_method(method)
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'طريقة غير صحيحة'}), 400
    except Exception as e:
        logger.error(f"خطأ في تحديد طريقة الكود: {str(e)}")
        return jsonify({'error': 'حدث خطأ'}), 500

@app.route('/admin/codes/add-manual', methods=['POST'])
def admin_add_codes_manual():
    """إضافة أكواد يدوياً"""
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
    
    try:
        code = request.form.get('code', '').strip().upper()
        price = request.form.get('price', '').strip()
        quantity = int(request.form.get('quantity', 1))
        
        if not code or not price:
            flash('جميع الحقول مطلوبة', 'error')
            return redirect(url_for('admin_codes'))
        
        # التحقق من صحة السعر
        try:
            price = int(price)
        except ValueError:
            flash('السعر يجب أن يكون رقماً صحيحاً', 'error')
            return redirect(url_for('admin_codes'))
        
        # إضافة الأكواد
        added_codes = code_manager.add_multiple_codes(code, price, quantity)
        
        if added_codes:
            flash(f'تم إضافة {len(added_codes)} كود بنجاح', 'success')
        else:
            flash('فشل في إضافة الأكواد', 'error')
        return redirect(url_for('admin_codes'))
        
    except Exception as e:
        logger.error(f"خطأ في إضافة الأكواد يدوياً: {str(e)}")
        flash('حدث خطأ في إضافة الأكواد', 'error')
        return redirect(url_for('admin_codes'))

@app.route('/admin/codes/upload', methods=['POST'])
def admin_upload_codes():
    """رفع ملف الأكواد"""
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
    
    try:
        if 'codes_file' not in request.files:
            flash('لم يتم اختيار ملف', 'error')
            return redirect(url_for('admin_codes'))
        
        file = request.files['codes_file']
        if file.filename == '':
            flash('لم يتم اختيار ملف', 'error')
            return redirect(url_for('admin_codes'))
        
        if file and file.filename.lower().endswith(('.csv', '.txt')):
            # قراءة محتوى الملف
            content = file.read().decode('utf-8')
            
            # استيراد الأكواد
            added_codes, errors = code_manager.import_codes_from_csv(content)
            
            if added_codes:
                flash(f'تم إضافة {len(added_codes)} كود بنجاح', 'success')
            
            if errors:
                flash(f'أخطاء: {"; ".join(errors[:5])}', 'error')
            
        else:
            flash('نوع الملف غير مدعوم. يرجى استخدام CSV أو TXT', 'error')
        
        return redirect(url_for('admin_codes'))
        
    except Exception as e:
        logger.error(f"خطأ في رفع ملف الأكواد: {str(e)}")
        flash('حدث خطأ في رفع الملف', 'error')
        return redirect(url_for('admin_codes'))

@app.route('/admin/codes/delete/<code_id>', methods=['POST'])
def admin_delete_code(code_id):
    """حذف كود"""
    if not session.get('is_admin'):
        return jsonify({'error': 'غير مصرح'}), 403
    
    try:
        success = code_manager.delete_code(code_id)
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'فشل في حذف الكود'}), 400
    except Exception as e:
        logger.error(f"خطأ في حذف الكود {code_id}: {str(e)}")
        return jsonify({'error': 'حدث خطأ'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)