from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from database.connection import db

class UserQueries:
    """Запросы для работы с пользователями"""
    
    @staticmethod
    async def create_user(user_id: int, phone_number: str, username: str = None, 
                         first_name: str = None, referrer_phone: str = None) -> bool:
        """Создание нового пользователя"""
        try:
            print(f"🔍 Создаем пользователя: user_id={user_id}, phone={phone_number}, referrer={referrer_phone}")
            
            await db.execute("""
                INSERT OR REPLACE INTO users 
                (user_id, phone_number, username, first_name, referrer_phone)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, phone_number, username, first_name, referrer_phone))
            return True
        except Exception as e:
            print(f"❌ Ошибка создания пользователя: {e}")
            return False
    
    @staticmethod
    async def get_user(user_id: int) -> Optional[Dict[str, Any]]:
        """Получение пользователя по ID"""
        try:
            row = await db.fetchone("SELECT * FROM users WHERE user_id = ?", (user_id,))
            if row:
                columns = ['user_id', 'username', 'first_name', 'phone_number', 'registration_date',
                          'referrer_phone', 'referral_balance', 'subscription_end', 'tariff_type', 
                          'tariff2_counter', 'has_paid', 'privacy_consent', 'privacy_consent_date', 'waiting_for_referrer']
                return dict(zip(columns, row))
            return None
        except Exception as e:
            print(f"❌ Ошибка получения пользователя: {e}")
            return None
    
    @staticmethod
    async def get_user_by_phone(phone_number: str) -> Optional[Dict[str, Any]]:
        """Получение пользователя по номеру телефона (для веб-хука)"""
        try:
            row = await db.fetchone("SELECT * FROM users WHERE phone_number = ?", (phone_number,))
            if row:
                columns = ['user_id', 'username', 'first_name', 'phone_number', 'registration_date',
                          'referrer_phone', 'referral_balance', 'subscription_end', 'tariff_type', 
                          'tariff2_counter', 'has_paid', 'privacy_consent', 'privacy_consent_date', 'waiting_for_referrer']
                return dict(zip(columns, row))
            return None
        except Exception as e:
            print(f"❌ Ошибка получения пользователя по телефону: {e}")
            return None
    
    @staticmethod
    async def update_subscription(phone_number: str, tariff_type: int, days: int = 30):
        """Обновление подписки пользователя по номеру телефона"""
        try:
            # Если у пользователя уже есть активная подписка, продлеваем её
            user = await UserQueries.get_user_by_phone(phone_number)
            if user and user['subscription_end']:
                current_end = datetime.fromisoformat(user['subscription_end'])
                if current_end > datetime.now():
                    new_end = current_end + timedelta(days=days)
                else:
                    new_end = datetime.now() + timedelta(days=days)
            else:
                new_end = datetime.now() + timedelta(days=days)
            
            # Увеличиваем счетчик для тарифа 2
            if tariff_type == 2:
                await db.execute("""
                    UPDATE users 
                    SET subscription_end = ?, tariff_type = ?, tariff2_counter = tariff2_counter + 1, has_paid = TRUE
                    WHERE phone_number = ?
                """, (new_end.isoformat(), tariff_type, phone_number))
            else:
                await db.execute("""
                    UPDATE users 
                    SET subscription_end = ?, tariff_type = ?, has_paid = TRUE
                    WHERE phone_number = ?
                """, (new_end.isoformat(), tariff_type, phone_number))
            
            return True
        except Exception as e:
            print(f"❌ Ошибка обновления подписки: {e}")
            return False
    
    @staticmethod
    async def check_subscription(user_id: int) -> bool:
        """Проверка активности подписки"""
        try:
            user = await UserQueries.get_user(user_id)
            if not user or not user['subscription_end']:
                return False
            
            end_date = datetime.fromisoformat(user['subscription_end'])
            return end_date > datetime.now()
        except Exception as e:
            print(f"❌ Ошибка проверки подписки: {e}")
            return False
    
    @staticmethod
    async def get_users_expiring_soon(days: int) -> list:
        """Получение пользователей с истекающей подпиской"""
        try:
            target_date = (datetime.now() + timedelta(days=days)).isoformat()
            current_date = datetime.now().isoformat()
            
            rows = await db.fetchall("""
                SELECT user_id, username, first_name, subscription_end 
                FROM users 
                WHERE subscription_end BETWEEN ? AND ?
            """, (current_date, target_date))
            
            return [{'user_id': row[0], 'username': row[1], 'first_name': row[2], 'subscription_end': row[3]} 
                    for row in rows]
        except Exception as e:
            print(f"❌ Ошибка получения истекающих подписок: {e}")
            return []

class PaymentQueries:
    """Запросы для работы с платежами"""
    
    @staticmethod
    async def create_payment(payment_id: str, user_id: int, amount: float, tariff_type: int) -> bool:
        """Создание записи о платеже"""
        try:
            await db.execute("""
                INSERT INTO payments (payment_id, user_id, amount, tariff_type)
                VALUES (?, ?, ?, ?)
            """, (payment_id, user_id, amount, tariff_type))
            return True
        except Exception as e:
            print(f"❌ Ошибка создания платежа: {e}")
            return False
    
    @staticmethod
    async def update_payment_status(payment_id: str, status: str) -> bool:
        """Обновление статуса платежа"""
        try:
            await db.execute("""
                UPDATE payments SET status = ? WHERE payment_id = ?
            """, (status, payment_id))
            return True
        except Exception as e:
            print(f"❌ Ошибка обновления статуса платежа: {e}")
            return False

class ReferralQueries:
    """Запросы для работы с реферальной системой"""
    
    @staticmethod
    async def add_referral_bonus(referrer_phone: str, referred_phone: str, bonus_amount: float) -> bool:
        """Начисление реферального бонуса"""
        try:
            # Добавляем бонус к балансу реферера
            await db.execute("""
                UPDATE users SET referral_balance = referral_balance + ? 
                WHERE phone_number = ?
            """, (bonus_amount, referrer_phone))
            
            # Записываем в таблицу рефералов
            await db.execute("""
                INSERT INTO referrals (referrer_phone, referred_phone, bonus_amount)
                VALUES (?, ?, ?)
            """, (referrer_phone, referred_phone, bonus_amount))
            
            return True
        except Exception as e:
            print(f"❌ Ошибка начисления реферального бонуса: {e}")
            return False
    
    @staticmethod
    async def use_referral_balance(phone_number: str, amount: float) -> bool:
        """Использование реферального баланса для оплаты"""
        try:
            user = await UserQueries.get_user_by_phone(phone_number)
            if not user or user['referral_balance'] < amount:
                return False
            
            await db.execute("""
                UPDATE users SET referral_balance = referral_balance - ? 
                WHERE phone_number = ?
            """, (amount, phone_number))
            
            return True
        except Exception as e:
            print(f"❌ Ошибка использования реферального баланса: {e}")
            return False