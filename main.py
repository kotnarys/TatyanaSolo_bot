import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from utils.config_loader import config
from database.connection import db
from handlers import start, payments, chat
# Подключаем дополнительные модули если они есть
try:
    from handlers import registration
    registration_available = True
except ImportError:
    registration_available = False
    print("⚠️ Модуль registration недоступен")

try:
    from handlers import referrals
    referrals_available = True
except ImportError:
    referrals_available = False
    print("⚠️ Модуль referrals недоступен")

try:
    from handlers import profile
    profile_available = True
except ImportError:
    profile_available = False
    print("⚠️ Модуль profile недоступен")

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """Основная функция запуска бота"""
    
    # Проверяем наличие токена
    bot_token = config.get('TELEGRAM_BOT_TOKEN')
    if not bot_token or bot_token == 'YOUR_BOT_TOKEN_HERE':
        logger.error("❌ Токен бота не найден! Проверьте файл config/settings.txt")
        return
    
    # Создаем бота и диспетчер
    bot = Bot(
        token=bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    dp = Dispatcher()
    
    try:
        # Подключаемся к базе данных
        await db.connect()
        
        # Регистрируем хендлеры
        dp.include_router(start.router)
        if registration_available:
            dp.include_router(registration.router)
            print("✅ Модуль registration подключен")
        if referrals_available:
            dp.include_router(referrals.router)
            print("✅ Модуль referrals подключен")
        if profile_available:
            dp.include_router(profile.router)
            print("✅ Модуль profile подключен")
        dp.include_router(payments.router)  
        dp.include_router(chat.router)
        
        # Устанавливаем команды бота (БЕЗ /start чтобы не терять реферальные параметры)
        from aiogram.types import BotCommand
        await bot.set_my_commands([
            BotCommand(command="profile", description="👤 Мой профиль"),
            BotCommand(command="referral", description="👥 Реферальная программа"),
        ])
        
        logger.info("✅ Бот запущен успешно!")
        
        # Запускаем polling
        await dp.start_polling(bot)
        
    except Exception as e:
        logger.error(f"❌ Ошибка при запуске бота: {e}")
    finally:
        # Закрываем соединения
        await db.disconnect()
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Бот остановлен пользователем")