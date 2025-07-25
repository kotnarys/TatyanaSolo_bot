import hashlib
import json
import aiohttp
from typing import Optional
from utils.config_loader import config

class PaymentService:
    """Сервис для работы с CloudPayments"""
    
    @staticmethod
    async def create_payment(amount: float, description: str, payment_id: str, user_id: int) -> str:
        """Создание ссылки на оплату CloudPayments"""
        
        # Получаем настройки CloudPayments
        public_id = config.get('CLOUDPAYMENTS_PUBLIC_ID')
        api_secret = config.get('CLOUDPAYMENTS_API_SECRET')
        
        # Проверяем режим разработки
        dev_mode = config.get('DEV_MODE', 'FALSE').upper() == 'TRUE'
        
        if dev_mode:
            print(f"🧪 Режим разработки: создаем тестовую оплату")
            # В тестовом режиме используем тестовый Public ID
            public_id = config.get('CLOUDPAYMENTS_TEST_PUBLIC_ID', public_id)
        
        if not public_id or public_id in ['TEMP_PLACEHOLDER', 'YOUR_PUBLIC_ID_HERE']:
            # Возвращаем тестовую ссылку если ключи не настроены
            return f"https://demo.cloudpayments.ru/test?amount={amount}&id={payment_id}"
        
        # Формируем данные для платежа
        payment_data = {
            'amount': amount,
            'currency': 'RUB',
            'description': description,
            'invoiceId': payment_id,
            'accountId': str(user_id),
            'email': f"user{user_id}@telegram.bot",  # Временный email
            'requireConfirmation': False,  # Не требуем подтверждение для тестов
            'cultureName': 'ru-RU'
        }
        
        # Формируем ссылку на виджет CloudPayments
        if dev_mode:
            # Тестовый виджет
            widget_url = f"https://widget.cloudpayments.ru/widgets/test/{public_id}"
        else:
            # Боевой виджет
            widget_url = f"https://widget.cloudpayments.ru/widgets/{public_id}"
        
        # Добавляем параметры к ссылке
        params = []
        for key, value in payment_data.items():
            params.append(f"{key}={value}")
        
        widget_params = "&".join(params)
        final_url = f"{widget_url}?{widget_params}"
        
        print(f"💳 Создана ссылка на оплату: {final_url}")
        return final_url
    
    @staticmethod
    async def create_payment_link_simple(amount: float, description: str, payment_id: str, user_id: int) -> str:
        """Упрощенная версия создания платежа для тестов"""
        public_id = config.get('CLOUDPAYMENTS_PUBLIC_ID', 'test_api_00000000000000000000001')
        
        # Простая ссылка на виджет CloudPayments
        payment_url = (
            f"https://widget.cloudpayments.ru/widgets/{public_id}?"
            f"amount={amount}&"
            f"currency=RUB&"
            f"description={description}&"
            f"invoiceId={payment_id}&"
            f"accountId={user_id}&"
            f"email=user{user_id}@test.com&"
            f"requireConfirmation=false&"
            f"cultureName=ru-RU"
        )
        
        return payment_url
    
    @staticmethod
    async def test_payment_api() -> bool:
        """Тестирование API CloudPayments"""
        try:
            public_id = config.get('CLOUDPAYMENTS_PUBLIC_ID')
            api_secret = config.get('CLOUDPAYMENTS_API_SECRET')
            
            if not public_id or not api_secret:
                print("⚠️ Ключи CloudPayments не настроены")
                return False
            
            # Тестовый запрос к API
            test_url = "https://api.cloudpayments.ru/test"
            
            async with aiohttp.ClientSession() as session:
                auth = aiohttp.BasicAuth(public_id, api_secret)
                async with session.post(test_url, auth=auth) as response:
                    if response.status == 200:
                        print("✅ CloudPayments API работает")
                        return True
                    else:
                        print(f"❌ CloudPayments API ошибка: {response.status}")
                        return False
        
        except Exception as e:
            print(f"❌ Ошибка тестирования CloudPayments API: {e}")
            return False
    
    @staticmethod
    def verify_webhook_signature(data: str, signature: str) -> bool:
        """Проверка подписи веб-хука CloudPayments"""
        
        api_secret = config.get('CLOUDPAYMENTS_API_SECRET')
        if not api_secret:
            print("⚠️ API Secret для проверки подписи не найден")
            return False
        
        try:
            # Вычисляем HMAC-SHA256
            import hmac
            expected_signature = hmac.new(
                api_secret.encode('utf-8'),
                data.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            result = hmac.compare_digest(expected_signature.lower(), signature.lower())
            print(f"🔐 Проверка подписи: {'✅ OK' if result else '❌ FAIL'}")
            return result
            
        except Exception as e:
            print(f"❌ Ошибка проверки подписи: {e}")
            return False