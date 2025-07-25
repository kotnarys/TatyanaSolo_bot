from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart
from aiogram.filters.command import CommandObject
from datetime import datetime

from database.queries import UserQueries
from utils.config_loader import config

router = Router()

@router.message(CommandStart(deep_link=True, magic=F.args.regexp(r"r\d+")))
async def cmd_start_with_referral(message: Message, command: CommandObject):
    """Обработчик команды /start с реферальным параметром"""
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    
    # Получаем реферальный параметр
    referral_param = command.args
    print(f"🔍 Получен реферальный параметр: '{referral_param}'")
    
    # Извлекаем номер телефона реферера
    referrer_phone = None
    if referral_param and referral_param.startswith('r'):
        phone_digits = referral_param[1:]  # Убираем 'r'
        referrer_phone = '+' + phone_digits  # Добавляем +
        print(f"🔍 Извлечен номер реферера: '{referrer_phone}'")
    
    # Ищем пользователя в БД
    existing_user = await UserQueries.get_user(user_id)
    
    if existing_user and existing_user['phone_number'] and not existing_user['phone_number'].startswith('temp_'):
        # Пользователь уже зарегистрирован
        await show_main_menu(message, existing_user)
    else:
        # Импортируем функции из других модулей
        try:
            from handlers.registration import save_temp_user_data, request_phone_number
            # Новый пользователь - сохраняем реферальную информацию
            await save_temp_user_data(user_id, username, first_name, referrer_phone)
            await request_phone_number(message)
        except ImportError:
            # Если модуль registration недоступен - временная заглушка
            await message.answer(
                f"🎉 Добро пожаловать!\n\n"
                f"Вы пришли по приглашению от {referrer_phone}!\n"
                f"Система в разработке, скоро будет доступна полная регистрация."
            )

@router.message(CommandStart())
async def cmd_start(message: Message):
    """Обработчик команды /start без параметров"""
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    
    print(f"🔍 Обычный /start без параметров для пользователя {user_id}")
    
    # Ищем пользователя в БД по user_id
    existing_user = await UserQueries.get_user(user_id)
    
    if existing_user and existing_user['phone_number'] and not existing_user['phone_number'].startswith('temp_'):
        # Пользователь уже зарегистрирован с реальным номером телефона
        await show_main_menu(message, existing_user)
    else:
        # Импортируем функцию из других модулей
        try:
            from handlers.referrals import ask_for_referral
            # Новый пользователь - спрашиваем про реферера
            await ask_for_referral(message, user_id, username, first_name)
        except ImportError:
            # Если модуль недоступен - простая заглушка
            await message.answer(
                "👋 Добро пожаловать!\n\n"
                "🤝 Пришли ли вы по приглашению от друга?\n"
                "Система в разработке, скоро будет доступна полная версия."
            )

async def show_main_menu(message_or_callback, user_data, is_new_message=False):
    """Показать главное меню"""
    # Определяем как обращаться к пользователю
    display_name = user_data['username'] if user_data['username'] else (user_data['first_name'] if user_data['first_name'] else "дорогой пользователь")
    
    # Проверяем статус подписки
    has_subscription = await UserQueries.check_subscription(user_data['user_id'])
    
    if has_subscription:
        end_date = datetime.fromisoformat(user_data['subscription_end'])
        welcome_text = f"👋 Добро пожаловать, {display_name}!\n\n"
        welcome_text += f"✅ У вас активная подписка до {end_date.strftime('%d.%m.%Y')}\n\n"
        welcome_text += "Теперь вы можете задавать мне любые вопросы! 💬"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="👤 Мой профиль", callback_data="profile")],
            [InlineKeyboardButton(text="👥 Реферальная программа", callback_data="referral")],
            [InlineKeyboardButton(text="📚 Купить курс", callback_data="buy_course")]
        ])
    else:
        welcome_text = f"👋 Добро пожаловать, {display_name}!\n\n"
        welcome_text += "Для использования бота необходимо оформить подписку.\n\n"
        welcome_text += "📦 Доступные тарифы:\n"
        welcome_text += f"• Тариф 1 - {config.get_int('TARIFF_1_PRICE')}₽ (базовый доступ)\n"
        welcome_text += f"• Тариф 2 - {config.get_int('TARIFF_2_PRICE')}₽ (доступ + материалы курса)"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💳 Тариф 1", callback_data="buy_tariff_1")],
            [InlineKeyboardButton(text="💎 Тариф 2", callback_data="buy_tariff_2")],
            [InlineKeyboardButton(text="📚 Купить курс", callback_data="buy_course")],
            [InlineKeyboardButton(text="👤 Профиль", callback_data="profile")],
            [InlineKeyboardButton(text="👥 Реферальная программа", callback_data="referral")]
        ])
    
    # Проверяем тип объекта для правильной отправки
    if hasattr(message_or_callback, 'edit_text') and not is_new_message:
        # Это callback и можно редактировать
        try:
            await message_or_callback.edit_text(welcome_text, reply_markup=keyboard)
        except:
            # Если не получается отредактировать - отправляем новое
            await message_or_callback.answer(welcome_text, reply_markup=keyboard)
    else:
        # Это обычное сообщение или принудительная отправка нового
        await message_or_callback.answer(welcome_text, reply_markup=keyboard)

@router.callback_query(F.data == "main_menu")
async def main_menu(callback: CallbackQuery):
    """Возврат в главное меню"""
    user_data = await UserQueries.get_user(callback.from_user.id)
    if user_data:
        await show_main_menu(callback.message, user_data)
    await callback.answer()

@router.callback_query(F.data == "buy_course")
async def show_course_info(callback: CallbackQuery):
    """Показать информацию о курсе"""
    user_id = callback.from_user.id
    user_data = await UserQueries.get_user(user_id)
    
    # Получаем данные курса из настроек
    course_name = config.get('COURSE_NAME', 'Полный курс по нейросетям')
    course_url = config.get('COURSE_URL', 'https://example.com/course')
    
    course_text = f"📚 <b>{course_name}</b>\n\n"
    course_text += "🎯 <b>Что вы получите:</b>\n"
    course_text += "• 20+ часов обучающего контента\n"
    course_text += "• Практические задания и кейсы\n"
    course_text += "• Доступ к закрытому сообществу\n"
    course_text += "• Сертификат о прохождении\n"
    course_text += "• Пожизненный доступ к материалам\n\n"
    
    course_text += "💡 <b>Для кого курс:</b>\n"
    course_text += "• Новичков в области ИИ\n"
    course_text += "• Предпринимателей и маркетологов\n"
    course_text += "• Всех, кто хочет освоить нейросети\n\n"
    
    course_text += "🚀 <b>После курса вы сможете:</b>\n"
    course_text += "• Эффективно работать с ChatGPT и другими ИИ\n"
    course_text += "• Автоматизировать рутинные задачи\n"
    course_text += "• Создавать контент с помощью ИИ\n"
    course_text += "• Интегрировать ИИ в свой бизнес\n\n"
    
    course_text += "💰 <b>Покупка и доступ:</b>\n"
    course_text += "• Оформление курса происходит на сайте\n"
    course_text += "• После покупки вам будет предоставлен доступ к боту\n"
    course_text += "• Указывайте тот же номер телефона, что и в Telegram"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌐 Купить курс на сайте", url=course_url)],
        [InlineKeyboardButton(text="🏠 В главное меню", callback_data="main_menu")]
    ])
    
    await callback.message.edit_text(course_text, reply_markup=keyboard)
    await callback.answer()