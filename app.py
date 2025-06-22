from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import os
import json
import random
import logging
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify

# استيراد الوحدات المحسنة
from config import AppConfig
from paymob_intention_client import paymob_intention_client, process_payment_intention
from validators import CardDataValidator, UserDataValidator, UserDataError
from exceptions import CardDataValidationError, PaymobError
from admin_manager import AdminManager
from card_manager import CardManager
from product_manager import ProductManager

# إعداد نظام السجلات
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = AppConfig.SECRET_KEY

# تأكد من وجود مجلد للبيانات
DATA_FOLDER = AppConfig.DATA_FOLDER
os.makedirs(DATA_FOLDER, exist_ok=True)

# إنشاء مدير الإدارة ومدير البطاقات ومدير المنتجات
admin_manager = AdminManager()
card_manager = CardManager()
product_manager = ProductManager()

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
        
        # توليد كود عشوائي مكون من 6 أرقام
        random_code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        
        # إنشاء بطاقة جديدة
        card_data = {
            'id': datetime.now().strftime('%Y%m%d%H%M%S'),
            'card_type': validated_data['card_type'],
            'card_value': validated_data['card_value'],
            'sender_name': validated_data['sender_name'],
            'recipient_name': validated_data['recipient_name'],
            'message': message,
            'random_code': random_code,
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'user_phone': validated_data['user_phone'],
            'payment_status': 'pending'
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
        
        if not payment_info:
            logger.warning("لا توجد معلومات دفع في الجلسة")
            return redirect(url_for('index'))
        
        logger.info("تم الوصول إلى صفحة نجاح الدفع باستخدام Intention API")
        
        # عرض صفحة النجاح
        return render_template('payment_success_intention.html', payment_info=payment_info)
        
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
    
    return render_template('card_view.html', card=card)

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
            'message': request.form.get('message', '').strip()
        }
        
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
                
                # استخدام نوع المنتج كاسم المنتج
                product_manager.add_product(product_type, price, background_color)
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
                
                product_manager.update_product(product_id, product_type, price, background_color)
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
    """تسجيل خروج الإدارة"""
    session.pop('admin_id', None)
    session.pop('admin_email', None)
    session.pop('admin_role', None)
    session.pop('is_admin', None)
    
    flash('تم تسجيل الخروج بنجاح', 'success')
    return redirect(url_for('admin_login'))

if __name__ == '__main__':
    app.run(debug=True, port=8080)