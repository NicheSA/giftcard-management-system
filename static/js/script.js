/**
 * ملف JavaScript الرئيسي لتطبيق بطاقات الإهداء
 */

// التأكد من تحميل المستند بالكامل قبل تنفيذ الكود
document.addEventListener('DOMContentLoaded', function() {
    // تهيئة عناصر التنقل
    initNavigation();
    
    // تهيئة معاينة البطاقة في صفحة النموذج إذا كانت موجودة
    initCardPreview();
    
    // تهيئة أزرار المشاركة والطباعة إذا كانت موجودة
    initCardActions();
});

/**
 * تهيئة عناصر التنقل وإضافة الأحداث لها
 */
function initNavigation() {
    // الحصول على جميع عناصر التنقل
    const navItems = document.querySelectorAll('.nav-item');
    
    // إضافة حدث النقر لكل عنصر تنقل
    navItems.forEach(item => {
        if (!item.classList.contains('active')) {
            item.addEventListener('click', function() {
                // يمكن إضافة منطق التنقل هنا إذا لزم الأمر
                // حالياً يتم التعامل مع التنقل من خلال الروابط المباشرة
            });
        }
    });
}

/**
 * تهيئة معاينة البطاقة في صفحة النموذج
 */
function initCardPreview() {
    // التحقق من وجود عناصر النموذج
    const cardTypeInput = document.getElementById('card_type');
    const cardValueInput = document.getElementById('card_value');
    const fromNameInput = document.getElementById('from_name');
    const toNameInput = document.getElementById('to_name');
    const messageInput = document.getElementById('message');
    
    // إذا كانت عناصر النموذج موجودة، إضافة أحداث لها
    if (cardTypeInput && cardValueInput && fromNameInput && toNameInput && messageInput) {
        // إضافة حدث الإدخال لتحديث المعاينة
        cardTypeInput.addEventListener('change', updatePreview);
        cardValueInput.addEventListener('change', updatePreview);
        fromNameInput.addEventListener('input', updatePreview);
        toNameInput.addEventListener('input', updatePreview);
        messageInput.addEventListener('input', updatePreview);
        
        // تحديث المعاينة عند تحميل الصفحة
        updatePreview();
    }
}

/**
 * تحديث معاينة البطاقة بناءً على القيم المدخلة
 */
function updatePreview() {
    const cardType = document.getElementById('card_type').value || '-';
    const cardValue = document.getElementById('card_value').value || '-';
    const fromName = document.getElementById('from_name').value || '-';
    const toName = document.getElementById('to_name').value || '-';
    const message = document.getElementById('message').value || '-';
    
    // تحديث معلومات البطاقة في المعاينة
    if (document.getElementById('preview-type')) {
        const previewTypeElement = document.getElementById('preview-type');
        previewTypeElement.textContent = cardType;
        previewTypeElement.setAttribute('data-type', cardType);
    }
    if (document.getElementById('preview-value')) {
        document.getElementById('preview-value').textContent = cardValue ? cardValue + ' ريال' : '-';
    }
    document.getElementById('preview-from').textContent = fromName;
    document.getElementById('preview-to').textContent = toName;
    document.getElementById('preview-message').textContent = message;
}

/**
 * تهيئة أزرار المشاركة في صفحة عرض البطاقة
 */
function initCardActions() {
    // زر المشاركة
    const shareButton = document.querySelector('.card-actions .btn-primary');
    if (shareButton) {
        shareButton.addEventListener('click', function() {
            // التحقق من دعم واجهة برمجة المشاركة
            if (navigator.share) {
                navigator.share({
                    title: 'بطاقة إهداء',
                    text: 'أرسلت لك بطاقة إهداء!',
                    url: window.location.href
                })
                .then(() => console.log('تمت المشاركة بنجاح'))
                .catch((error) => console.log('خطأ في المشاركة:', error));
            } else {
                // نسخ الرابط إلى الحافظة إذا كانت واجهة المشاركة غير مدعومة
                const tempInput = document.createElement('input');
                tempInput.value = window.location.href;
                document.body.appendChild(tempInput);
                tempInput.select();
                document.execCommand('copy');
                document.body.removeChild(tempInput);
                
                alert('تم نسخ رابط البطاقة!');
            }
        });
    }
}

/**
 * التحقق من صحة نموذج تسجيل الدخول
 * @param {Event} event - حدث إرسال النموذج
 * @returns {boolean} - ما إذا كان النموذج صالحًا
 */
function validateLoginForm(event) {
    const nameInput = document.getElementById('name');
    const phoneInput = document.getElementById('phone');
    
    if (!nameInput.value.trim()) {
        alert('يرجى إدخال الاسم');
        nameInput.focus();
        event.preventDefault();
        return false;
    }
    
    if (!phoneInput.value.trim()) {
        alert('يرجى إدخال رقم الجوال');
        phoneInput.focus();
        event.preventDefault();
        return false;
    }
    
    // يمكن إضافة المزيد من التحقق من صحة رقم الجوال هنا
    
    return true;
}

/**
 * التحقق من صحة نموذج البطاقة
 * @param {Event} event - حدث إرسال النموذج
 * @returns {boolean} - ما إذا كان النموذج صالحًا
 */
function validateCardForm(event) {
    const cardTypeInput = document.getElementById('card_type');
    const cardValueInput = document.getElementById('card_value');
    const fromNameInput = document.getElementById('from_name');
    const toNameInput = document.getElementById('to_name');
    const messageInput = document.getElementById('message');
    
    if (!cardTypeInput.value) {
        alert('يرجى اختيار نوع البطاقة');
        cardTypeInput.focus();
        event.preventDefault();
        return false;
    }
    
    if (!cardValueInput.value) {
        alert('يرجى اختيار قيمة البطاقة');
        cardValueInput.focus();
        event.preventDefault();
        return false;
    }
    
    if (!fromNameInput.value.trim()) {
        alert('يرجى إدخال اسم المهدي');
        fromNameInput.focus();
        event.preventDefault();
        return false;
    }
    
    if (!toNameInput.value.trim()) {
        alert('يرجى إدخال اسم المهدى إليه');
        toNameInput.focus();
        event.preventDefault();
        return false;
    }
    
    if (!messageInput.value.trim()) {
        alert('يرجى إدخال رسالة الإهداء');
        messageInput.focus();
        event.preventDefault();
        return false;
    }
    
    return true;
}

// إضافة مستمعي أحداث للنماذج
document.addEventListener('DOMContentLoaded', function() {
    // نموذج تسجيل الدخول
    const loginForm = document.querySelector('form[action*="login"]');
    if (loginForm) {
        loginForm.addEventListener('submit', validateLoginForm);
    }
    
    // نموذج البطاقة
    const cardForm = document.querySelector('form[action*="save_card"]');
    if (cardForm) {
        cardForm.addEventListener('submit', validateCardForm);
    }
});