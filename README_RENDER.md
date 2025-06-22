# نشر نظام إدارة البطاقات الهدايا على Render

## خطوات النشر

### 1. إعداد المشروع

تأكد من أن مشروعك يحتوي على الملفات التالية:
- ✅ `render.yaml` - ملف إعدادات Render
- ✅ `requirements.txt` - مع gunicorn مضاف
- ✅ `.env.example` - مثال على المتغيرات البيئية

### 2. رفع المشروع إلى GitHub

```bash
git add .
git commit -m "Prepare for Render deployment"
git push origin main
```

### 3. إنشاء حساب على Render

1. اذهب إلى [render.com](https://render.com)
2. سجل دخول باستخدام GitHub
3. اربط حسابك مع مستودع GitHub

### 4. إنشاء خدمة ويب جديدة

1. انقر على "New +" → "Web Service"
2. اختر مستودع `giftcard-management-system`
3. املأ التفاصيل:
   - **Name**: `giftcard-management-system`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
   - **Plan**: `Free`

### 5. إعداد المتغيرات البيئية

في لوحة تحكم Render، اذهب إلى "Environment" وأضف:

#### متغيرات Paymob (مطلوبة)
```
PAYMOB_API_KEY=your_actual_api_key
PAYMOB_PUBLIC_KEY=your_actual_public_key
PAYMOB_IFRAME_ID=your_actual_iframe_id
PAYMOB_INTEGRATION_ID=your_actual_integration_id
PAYMOB_HMAC_SECRET=your_actual_hmac_secret
```

#### عناوين Callback
```
PAYMOB_PROCESSED_CALLBACK_URL=https://your-app-name.onrender.com/payment/callback
PAYMOB_RESPONSE_CALLBACK_URL=https://your-app-name.onrender.com/payment/response
```

#### إعدادات Flask
```
SECRET_KEY=generate_a_strong_secret_key
FLASK_ENV=production
```

### 6. النشر

1. انقر على "Create Web Service"
2. انتظر حتى يكتمل البناء والنشر (5-10 دقائق)
3. ستحصل على رابط مثل: `https://your-app-name.onrender.com`

## ملاحظات مهمة

### الخطة المجانية
- ✅ 750 ساعة شهرياً
- ⚠️ التطبيق ينام بعد 15 دقيقة من عدم النشاط
- ⚠️ يستغرق 30-60 ثانية للاستيقاظ
- ✅ SSL مجاني
- ✅ دومين فرعي مجاني

### الأمان
- 🔒 لا تشارك مفاتيح Paymob الحقيقية
- 🔒 استخدم مفاتيح اختبار أولاً
- 🔒 تأكد من صحة عناوين Callback

### استكشاف الأخطاء

#### إذا فشل البناء:
1. تحقق من `requirements.txt`
2. تأكد من وجود `gunicorn`
3. راجع سجلات البناء في Render

#### إذا فشل التشغيل:
1. تحقق من المتغيرات البيئية
2. راجع سجلات التطبيق
3. تأكد من صحة `app:app` في Start Command

#### إذا لم تعمل المدفوعات:
1. تحقق من مفاتيح Paymob
2. تأكد من صحة عناوين Callback
3. راجع سجلات Paymob

## الدعم

إذا واجهت مشاكل:
1. راجع [وثائق Render](https://render.com/docs)
2. تحقق من سجلات التطبيق
3. تأكد من إعدادات Paymob

## التحديثات

لتحديث التطبيق:
1. ادفع التغييرات إلى GitHub
2. Render سيعيد النشر تلقائياً
3. راقب سجلات النشر