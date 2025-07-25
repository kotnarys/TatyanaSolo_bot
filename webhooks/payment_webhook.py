from aiohttp import web, web_request
import json
from database.queries import UserQueries, PaymentQueries
from services.payment_service import PaymentService
from handlers.payments import process_successful_payment

class PaymentWebhook:
    """Веб-хук для обработки уведомлений о платежах"""
    
    @staticmethod
    async def handle_cloudpayments_webhook(request: web_request.Request) -> web.Response:
        """Обработка веб-хука от CloudPayments"""
        try:
            # Получаем данные
            body = await request.text()
            signature = request.headers.get('X-HMAC-SHA256', '')
            
            # Проверяем подпись (в реальном режиме)
            dev_mode = True  # В реальности проверить через config
            if not dev_mode and not PaymentService.verify_webhook_signature(body, signature):
                return web.Response(status=401, text="Invalid signature")
            
            # Парсим JSON
            data = json.loads(body)
            
            # Извлекаем данные о платеже
            payment_id = data.get('InvoiceId')
            amount = float(data.get('Amount', 0))
            status = data.get('Status')  # Completed для успешного платежа
            account_id = data.get('AccountId')  # user_id
            
            if status == 'Completed' and payment_id and account_id:
                user_id = int(account_id)
                
                # Обновляем статус платежа в БД
                await PaymentQueries.update_payment_status(payment_id, 'completed')
                
                # Определяем тариф (нужно получить из БД)
                # TODO: Добавить в PaymentQueries метод для получения данных платежа
                
                # Временно берем тариф 1 (нужно доработать)
                tariff_type = 1
                
                # Обрабатываем успешный платеж
                await process_successful_payment(user_id, tariff_type, amount, 0.0, bot=None, is_test=False)
                
                return web.Response(status=200, text="OK")
            
            return web.Response(status=400, text="Invalid payment data")
            
        except Exception as e:
            print(f"❌ Ошибка обработки веб-хука: {e}")
            return web.Response(status=500, text="Internal error")
    
    @staticmethod
    async def handle_website_webhook(request: web_request.Request) -> web.Response:
        """Обработка веб-хука с сайта (когда пользователь оплатил на сайте)"""
        try:
            data = await request.json()
            
            # Ожидаемые поля: phone_number, tariff_type, amount
            phone_number = data.get('phone_number')
            tariff_type = int(data.get('tariff_type', 1))
            amount = float(data.get('amount', 0))
            
            if not phone_number:
                return web.Response(status=400, text="Phone number required")
            
            # Ищем пользователя по номеру телефона
            user_data = await UserQueries.get_user_by_phone(phone_number)
            
            if user_data:
                # Пользователь найден - обновляем подписку
                user_id = user_data['user_id']
                await process_successful_payment(user_id, tariff_type, amount, 0.0, bot=None, is_test=False)
            else:
                # Создаем нового пользователя (он запустит бота позже)
                # Для этого нужно добавить временную запись
                await UserQueries.create_user(
                    user_id=0,  # Временный ID, будет обновлен при старте бота
                    phone_number=phone_number
                )
                # TODO: Доработать логику для пользователей, оплативших на сайте
            
            return web.Response(status=200, text="OK")
            
        except Exception as e:
            print(f"❌ Ошибка обработки веб-хука сайта: {e}")
            return web.Response(status=500, text="Internal error")

# Создание веб-приложения для веб-хуков
async def create_webhook_app():
    """Создание веб-приложения для обработки веб-хуков"""
    app = web.Application()
    
    # Маршруты для веб-хуков
    app.router.add_post('/webhook/cloudpayments', PaymentWebhook.handle_cloudpayments_webhook)
    app.router.add_post('/webhook/website', PaymentWebhook.handle_website_webhook)
    
    return app

# Для запуска веб-хуков отдельно (если нужно)
if __name__ == "__main__":
    import asyncio
    from aiohttp import web
    
    async def main():
        app = await create_webhook_app()
        runner = web.AppRunner(app)
        await runner.setup()
        
        site = web.TCPSite(runner, 'localhost', 8000)
        await site.start()
        
        print("🌐 Веб-хуки запущены на http://localhost:8000")
        
        # Держим сервер запущенным
        await asyncio.Event().wait()
    
    asyncio.run(main())