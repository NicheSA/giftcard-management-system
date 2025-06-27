import json
import os
import uuid
from datetime import datetime
from config import AppConfig

class ProductManager:
    """مدير منتجات البطاقات"""
    
    def __init__(self):
        self.products_file = os.path.join(AppConfig.DATA_FOLDER, 'card_products.json')
        self._ensure_products_file()
    
    def _ensure_products_file(self):
        """التأكد من وجود ملف المنتجات وإنشاؤه إذا لم يكن موجوداً"""
        if not os.path.exists(self.products_file):
            default_products = [
                {
                    'id': str(uuid.uuid4()),
                    'name': 'زواج',
                    'price': 50,
                    'background_color': '#667eea',
                    'created_at': datetime.now().isoformat(),
                    'is_active': True
                },
                {
                    'id': str(uuid.uuid4()),
                    'name': 'زواج',
                    'price': 100,
                    'background_color': '#764ba2',
                    'created_at': datetime.now().isoformat(),
                    'is_active': True
                },
                {
                    'id': str(uuid.uuid4()),
                    'name': 'مولود',
                    'price': 30,
                    'background_color': '#56ab2f',
                    'created_at': datetime.now().isoformat(),
                    'is_active': True
                },
                {
                    'id': str(uuid.uuid4()),
                    'name': 'مولود',
                    'price': 50,
                    'background_color': '#4ecdc4',
                    'created_at': datetime.now().isoformat(),
                    'is_active': True
                },
                {
                    'id': str(uuid.uuid4()),
                    'name': 'تخرج',
                    'price': 75,
                    'background_color': '#f39c12',
                    'created_at': datetime.now().isoformat(),
                    'is_active': True
                },
                {
                    'id': str(uuid.uuid4()),
                    'name': 'عيد ميلاد',
                    'price': 40,
                    'background_color': '#ff6b6b',
                    'created_at': datetime.now().isoformat(),
                    'is_active': True
                }
            ]
            
            with open(self.products_file, 'w', encoding='utf-8') as f:
                json.dump(default_products, f, ensure_ascii=False, indent=2)
    
    def get_all_products(self):
        """الحصول على جميع المنتجات"""
        try:
            with open(self.products_file, 'r', encoding='utf-8') as f:
                products = json.load(f)
                return [p for p in products if p.get('is_active', True)]
        except Exception as e:
            print(f"خطأ في تحميل المنتجات: {str(e)}")
            return []
    
    def get_product_by_id(self, product_id):
        """الحصول على منتج بواسطة المعرف"""
        products = self.get_all_products()
        for product in products:
            if product['id'] == product_id:
                return product
        return None
    
    def add_product(self, name, price, background_color, logo_image=None, background_image=None):
        """إضافة منتج جديد"""
        try:
            with open(self.products_file, 'r', encoding='utf-8') as f:
                products = json.load(f)
            
            new_product = {
                'id': str(uuid.uuid4()),
                'name': name,
                'price': int(price),
                'background_color': background_color,
                'logo_image': logo_image,
                'background_image': background_image,
                'created_at': datetime.now().isoformat(),
                'is_active': True
            }
            
            products.append(new_product)
            
            with open(self.products_file, 'w', encoding='utf-8') as f:
                json.dump(products, f, ensure_ascii=False, indent=2)
            
            return new_product
        except Exception as e:
            print(f"خطأ في إضافة المنتج: {str(e)}")
            return None
    
    def update_product(self, product_id, name, price, background_color, logo_image=None, background_image=None):
        """تحديث منتج موجود"""
        try:
            with open(self.products_file, 'r', encoding='utf-8') as f:
                products = json.load(f)
            
            for i, product in enumerate(products):
                if product['id'] == product_id:
                    update_data = {
                        'name': name,
                        'price': int(price),
                        'background_color': background_color,
                        'updated_at': datetime.now().isoformat()
                    }
                    
                    # تحديث الشعار فقط إذا تم توفيره
                    if logo_image is not None:
                        update_data['logo_image'] = logo_image
                    
                    # تحديث صورة الخلفية فقط إذا تم توفيرها
                    if background_image is not None:
                        update_data['background_image'] = background_image
                    
                    products[i].update(update_data)
                    
                    with open(self.products_file, 'w', encoding='utf-8') as f:
                        json.dump(products, f, ensure_ascii=False, indent=2)
                    
                    return products[i]
            
            return None
        except Exception as e:
            print(f"خطأ في تحديث المنتج: {str(e)}")
            return None
    
    def delete_product(self, product_id):
        """حذف منتج (حذف منطقي)"""
        try:
            with open(self.products_file, 'r', encoding='utf-8') as f:
                products = json.load(f)
            
            for i, product in enumerate(products):
                if product['id'] == product_id:
                    products[i]['is_active'] = False
                    products[i]['deleted_at'] = datetime.now().isoformat()
                    
                    with open(self.products_file, 'w', encoding='utf-8') as f:
                        json.dump(products, f, ensure_ascii=False, indent=2)
                    
                    return True
            
            return False
        except Exception as e:
            print(f"خطأ في حذف المنتج: {str(e)}")
            return False
    
    def get_product_by_id(self, product_id):
        """الحصول على منتج واحد بواسطة المعرف"""
        try:
            with open(self.products_file, 'r', encoding='utf-8') as f:
                products = json.load(f)
            
            for product in products:
                if product['id'] == product_id and product.get('is_active', True):
                    return product
            
            return None
        except Exception as e:
            print(f"خطأ في الحصول على المنتج: {str(e)}")
            return None
    
    def get_products_by_type(self, product_type):
        """الحصول على المنتجات حسب النوع"""
        products = self.get_all_products()
        return [p for p in products if p['name'] == product_type]
    
    def get_product_statistics(self):
        """الحصول على إحصائيات المنتجات"""
        products = self.get_all_products()
        
        stats = {
            'total_products': len(products),
            'products_by_type': {},
            'price_ranges': {
                'under_50': 0,
                '50_to_100': 0,
                'over_100': 0
            },
            'average_price': 0
        }
        
        if products:
            # إحصائيات حسب النوع
            for product in products:
                product_type = product['name']
                if product_type not in stats['products_by_type']:
                    stats['products_by_type'][product_type] = 0
                stats['products_by_type'][product_type] += 1
                
                # إحصائيات الأسعار
                price = product['price']
                if price < 50:
                    stats['price_ranges']['under_50'] += 1
                elif price <= 100:
                    stats['price_ranges']['50_to_100'] += 1
                else:
                    stats['price_ranges']['over_100'] += 1
            
            # متوسط السعر
            total_price = sum(p['price'] for p in products)
            stats['average_price'] = round(total_price / len(products), 2)
        
        return stats
    
    def get_unique_product_types(self):
        """الحصول على أنواع المنتجات الفريدة الموجودة في قاعدة البيانات"""
        try:
            products = self.get_all_products()
            unique_types = list(set(product['name'] for product in products))
            return sorted(unique_types)
        except Exception as e:
            print(f"خطأ في الحصول على أنواع المنتجات: {str(e)}")
            return []