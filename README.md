# نظام بطاقات الهدايا - Gift Card System

نظام متكامل لإنشاء وإدارة بطاقات الهدايا مع تكامل بوابة الدفع Paymob.

## المميزات

- إنشاء بطاقات هدايا مخصصة
- تكامل آمن مع بوابة الدفع Paymob
- واجهة مستخدم عربية سهلة الاستخدام
- نظام تسجيل شامل للأخطاء والعمليات
- التحقق من صحة البيانات
- معالجة آمنة للاستثناءات

## متطلبات النظام

- Python 3.8+
- Flask 2.3.3
- حساب Paymob نشط

## التثبيت

1. استنساخ المشروع:
```bash
git clone <repository-url>
cd giftcard
```

2. إنشاء بيئة افتراضية:
```bash
python3 -m venv venv
source venv/bin/activate  # على macOS/Linux
# أو
venv\Scripts\activate  # على Windows
```

3. تثبيت المتطلبات:
```bash
pip install -r requirements.txt
```

4. إعداد متغيرات البيئة:
```bash
cp .env.example .env
```

ثم قم بتحديث ملف `.env` ببيانات Paymob الخاصة بك:

```env
# Paymob Configuration
PAYMOB_API_KEY=your_api_key_here
PAYMOB_PUBLIC_KEY=your_public_key_here
PAYMOB_IFRAME_ID=your_iframe_id_here
PAYMOB_INTEGRATION_ID=your_integration_id_here
PAYMOB_HMAC_SECRET=your_hmac_secret_here

# Flask Configuration
FLASK_SECRET_KEY=your_secret_key_here
FLASK_DEBUG=True
```

## الحصول على بيانات Paymob

### 1. API Key
- سجل الدخول إلى [Paymob Dashboard](https://accept.paymob.com/portal2/en/login)
- اذهب إلى **Settings > Account Info**
- انسخ **API Key**

### 2. Integration ID
- في لوحة التحكم، اذهب إلى **Developers > Payment Integrations**
- اختر التكامل المطلوب
- انسخ **Integration ID**

### 3. iFrame ID
- اذهب إلى **Developers > iFrames**
- اختر iFrame المطلوب
- انسخ **iFrame ID**

### 4. HMAC Secret
- في إعدادات التكامل، ستجد **HMAC Secret**
- انسخه لاستخدامه في التحقق من صحة البيانات

## تشغيل التطبيق

```bash
python app.py
```

سيعمل التطبيق على: `http://127.0.0.1:8080`

## هيكل المشروع

```
giftcard/
├── app.py                 # التطبيق الرئيسي
├── config.py             # إعدادات التطبيق
├── paymob_client.py      # عميل Paymob API
├── validators.py         # التحقق من صحة البيانات
├── exceptions.py         # الاستثناءات المخصصة
├── requirements.txt      # متطلبات Python
├── .env                  # متغيرات البيئة
├── data/                 # مجلد البيانات
├── static/              # الملفات الثابتة (CSS, JS, Images)
└── templates/           # قوالب HTML
    ├── index.html
    ├── card_form.html
    ├── payment.html
    └── payment_success.html
```

## الأمان

- جميع البيانات الحساسة محفوظة في متغيرات البيئة
- التحقق من صحة جميع المدخلات
- استخدام HMAC للتحقق من صحة callbacks
- معالجة آمنة للأخطاء
- تسجيل شامل للعمليات

## المساهمة

1. Fork المشروع
2. إنشاء فرع للميزة الجديدة (`git checkout -b feature/AmazingFeature`)
3. Commit التغييرات (`git commit -m 'Add some AmazingFeature'`)
4. Push للفرع (`git push origin feature/AmazingFeature`)
5. فتح Pull Request

## الترخيص

هذا المشروع مرخص تحت رخصة MIT - راجع ملف [LICENSE](LICENSE) للتفاصيل.

## الدعم

للحصول على الدعم، يرجى فتح issue في GitHub أو التواصل مع فريق التطوير.