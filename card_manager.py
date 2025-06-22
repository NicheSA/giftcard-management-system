import os
import json
from datetime import datetime
from config import AppConfig

class CardManager:
    """مدير البطاقات للنظام الإداري"""
    
    def __init__(self):
        self.data_folder = AppConfig.DATA_FOLDER
    
    def get_all_cards(self, limit=None):
        """الحصول على جميع البطاقات من جميع المستخدمين"""
        all_cards = []
        
        try:
            for filename in os.listdir(self.data_folder):
                if filename.endswith('_cards.json'):
                    file_path = os.path.join(self.data_folder, filename)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        cards = json.load(f)
                        all_cards.extend(cards)
        except Exception as e:
            print(f"خطأ في تحميل البطاقات: {str(e)}")
        
        # ترتيب البطاقات حسب تاريخ الإنشاء (الأحدث أولاً)
        all_cards.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        # تطبيق الحد الأقصى إذا تم تحديده
        if limit:
            return all_cards[:limit]
        
        return all_cards
    
    def get_cards_by_status(self, status):
        """الحصول على البطاقات حسب الحالة"""
        all_cards = self.get_all_cards()
        return [card for card in all_cards if card.get('payment_status') == status]
    
    def get_cards_by_type(self, card_type):
        """الحصول على البطاقات حسب النوع"""
        all_cards = self.get_all_cards()
        return [card for card in all_cards if card.get('card_type') == card_type]
    
    def get_card_statistics(self):
        """الحصول على إحصائيات البطاقات"""
        all_cards = self.get_all_cards()
        
        stats = {
            'total_cards': len(all_cards),
            'completed_payments': len([c for c in all_cards if c.get('payment_status') == 'completed']),
            'pending_payments': len([c for c in all_cards if c.get('payment_status') == 'pending']),
            'failed_payments': len([c for c in all_cards if c.get('payment_status') == 'failed']),
            'total_revenue': 0,
            'cards_by_type': {},
            'cards_by_value': {}
        }
        
        # حساب الإيرادات والإحصائيات التفصيلية
        for card in all_cards:
            if card.get('payment_status') == 'completed':
                stats['total_revenue'] += float(card.get('card_value', 0))
            
            # إحصائيات حسب النوع
            card_type = card.get('card_type', 'غير محدد')
            stats['cards_by_type'][card_type] = stats['cards_by_type'].get(card_type, 0) + 1
            
            # إحصائيات حسب القيمة
            card_value = str(card.get('card_value', 0))
            stats['cards_by_value'][card_value] = stats['cards_by_value'].get(card_value, 0) + 1
        
        return stats
    
    def create_card(self, card_data):
        """إنشاء بطاقة جديدة من الداشبورد الإداري"""
        try:
            # إنشاء معرف فريد للبطاقة
            card_id = datetime.now().strftime('%Y%m%d%H%M%S')
            
            # إنشاء كود عشوائي
            import random
            random_code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
            
            new_card = {
                'id': card_id,
                'card_type': card_data['card_type'],
                'card_value': float(card_data['card_value']),
                'sender_name': card_data['sender_name'],
                'recipient_name': card_data['recipient_name'],
                'message': card_data.get('message', ''),
                'random_code': random_code,
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'user_phone': card_data.get('user_phone', 'admin'),
                'payment_status': 'completed',  # البطاقات المنشأة من الداشبورد تعتبر مدفوعة
                'created_by_admin': True
            }
            
            # حفظ البطاقة
            phone = card_data.get('user_phone', 'admin')
            cards_file = os.path.join(self.data_folder, f'{phone}_cards.json')
            
            cards = []
            if os.path.exists(cards_file):
                with open(cards_file, 'r', encoding='utf-8') as f:
                    cards = json.load(f)
            
            cards.append(new_card)
            
            with open(cards_file, 'w', encoding='utf-8') as f:
                json.dump(cards, f, ensure_ascii=False, indent=4)
            
            return {'success': True, 'card_id': card_id, 'card': new_card}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def update_card_status(self, card_id, new_status):
        """تحديث حالة البطاقة"""
        try:
            for filename in os.listdir(self.data_folder):
                if filename.endswith('_cards.json'):
                    file_path = os.path.join(self.data_folder, filename)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        cards = json.load(f)
                    
                    for card in cards:
                        if card['id'] == card_id:
                            card['payment_status'] = new_status
                            card['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            
                            with open(file_path, 'w', encoding='utf-8') as f:
                                json.dump(cards, f, ensure_ascii=False, indent=4)
                            
                            return {'success': True}
            
            return {'success': False, 'error': 'البطاقة غير موجودة'}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def delete_card(self, card_id):
        """حذف بطاقة"""
        try:
            for filename in os.listdir(self.data_folder):
                if filename.endswith('_cards.json'):
                    file_path = os.path.join(self.data_folder, filename)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        cards = json.load(f)
                    
                    original_count = len(cards)
                    cards = [card for card in cards if card['id'] != card_id]
                    
                    if len(cards) < original_count:
                        with open(file_path, 'w', encoding='utf-8') as f:
                            json.dump(cards, f, ensure_ascii=False, indent=4)
                        return {'success': True}
            
            return {'success': False, 'error': 'البطاقة غير موجودة'}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}

# إنشاء مثيل عام
card_manager = CardManager()