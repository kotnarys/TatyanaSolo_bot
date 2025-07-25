from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from database.queries import UserQueries
from utils.config_loader import config

router = Router()

async def ask_for_referral(message: Message, user_id: int, username: str, first_name: str):
    """Спрашиваем пользователя про реферальную ссылку"""
    referral_text = "👋 Добро пожаловать!\n\n"
    referral_text += "🤝 Пришли ли вы по приглашению от друга?\n\n"
    referral_text += "Если да - нажмите \"Да, по приглашению\"\n"
    referral_text += "Если нет - нажмите \"Нет, сам нашел\""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤝 Да, по приглашению", callback_data="has_referrer")],
        [InlineKeyboardButton(text="🔍 Нет, сам нашел", callback_data="no_referrer")]
    ])
    
    await message.answer(referral_text, reply_markup=keyboard)

@router.callback_query(F.data == "has_referrer")
async def handle_has_referrer(callback: CallbackQuery):
    """Пользователь пришел по приглашению"""
    user_id = callback.from_user.id
    
    referrer_text = "🤝 Отлично!\n\n"
    referrer_text += "📱 Пожалуйста, попросите друга, который вас пригласил, отправить вам свой номер телефона.\n\n"
    referrer_text += "Затем отправьте мне номер телефона вашего друга в формате:\n"
    referrer_text += "<code>+79123456789</code>\n\n"
    referrer_text += "Или нажмите \"Пропустить\", если не хотите указывать."
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏭️ Пропустить", callback_data="no_referrer")]
    ])
    
    await callback.message.edit_text(referrer_text, reply_markup=keyboard)
    
    # Устанавливаем состояние "ожидание номера реферера"
    from database.connection import db
    await db.execute("""
        INSERT OR REPLACE INTO users 
        (user_id, phone_number, username, first_name, waiting_for_referrer)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, f"temp_{user_id}", callback.from_user.username, callback.from_user.first_name, True))
    
    await callback.answer()

@router.callback_query(F.data == "no_referrer")
async def handle_no_referrer(callback: CallbackQuery):
    """Пользователь пришел сам"""
    user_id = callback.from_user.id
    username = callback.from_user.username
    first_name = callback.from_user.first_name
    
    from handlers.registration import save_temp_user_data, request_phone_number
    
    await save_temp_user_data(user_id, username, first_name, None)
    
    await callback.message.edit_text("👍 Понятно, вы нашли нас сами!")
    await request_phone_number(callback.message)
    await callback.answer()

@router.message(F.text.regexp(r'^\+\d{10,15}$'))
async def handle_referrer_phone(message: Message):
    """Обработка номера телефона реферера"""
    user_id = message.from_user.id
    
    # Проверяем, что пользователь в состоянии ожидания реферера
    from database.connection import db
    user_data = await db.fetchone("""
        SELECT waiting_for_referrer FROM users WHERE user_id = ?
    """, (user_id,))
    
    if not user_data or not user_data[0]:
        return  # Пользователь не в режиме ожидания реферера
    
    referrer_phone = message.text.strip()
    username = message.from_user.username
    first_name = message.from_user.first_name
    
    # Проверяем, что реферер существует в базе
    referrer_data = await UserQueries.get_user_by_phone(referrer_phone)
    
    if referrer_data:
        from handlers.registration import save_temp_user_data, request_phone_number
        
        await save_temp_user_data(user_id, username, first_name, referrer_phone)
        
        await message.answer(
            f"✅ Отлично! Ваш друг {referrer_phone} найден в системе.\n"
            f"После оплаты подписки он получит бонус!"
        )
        
        # Убираем флаг ожидания
        await db.execute("""
            UPDATE users SET waiting_for_referrer = FALSE WHERE user_id = ?
        """, (user_id,))
        
        await request_phone_number(message)
    else:
        await message.answer(
            f"❌ Пользователь с номером {referrer_phone} не найден в системе.\n\n"
            f"Возможно:\n"
            f"• Ваш друг еще не регистрировался в боте\n"
            f"• Номер указан неверно\n\n"
            f"Попробуйте еще раз или нажмите \"Пропустить\"",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⏭️ Пропустить", callback_data="no_referrer")]
            ])
        )