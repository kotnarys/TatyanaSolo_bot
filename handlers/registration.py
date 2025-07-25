from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove

from database.queries import UserQueries
from utils.config_loader import config

router = Router()

async def request_phone_number(message: Message):
    """Запрос согласия на обработку ПД и номера телефона у пользователя"""
    welcome_text = f"👋 Добро пожаловать!\n\n"
    welcome_text += "📱 Для использования бота необходимо ваше согласие на обработку персональных данных и номер телефона.\n\n"
    welcome_text += "🔒 <b>Зачем нужен номер телефона?</b>\n"
    welcome_text += "• Привязка покупок с сайта к вашему аккаунту\n"
    welcome_text += "• Восстановление доступа при смене устройства\n"
    welcome_text += "• Безопасность вашего аккаунта\n\n"
    welcome_text += "📋 <b>Согласие на обработку персональных данных:</b>\n"
    welcome_text += "Нажимая кнопку \"Согласен\", вы даете согласие на обработку ваших персональных данных в соответствии с 152-ФЗ \"О персональных данных\".\n\n"
    welcome_text += "📄 С полной политикой конфиденциальности можно ознакомиться по ссылке: "
    
    # Получаем ссылку на политику из настроек
    policy_url = config.get('PRIVACY_POLICY_URL', 'https://example.com/privacy')
    welcome_text += f"{policy_url}"
    
    # Кнопки для согласия
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Согласен на обработку ПД", callback_data="agree_privacy")],
        [InlineKeyboardButton(text="❌ Не согласен", callback_data="disagree_privacy")],
        [InlineKeyboardButton(text="📄 Политика конфиденциальности", url=policy_url)]
    ])
    
    await message.answer(welcome_text, reply_markup=keyboard)

@router.callback_query(F.data == "agree_privacy")
async def handle_privacy_agreement(callback: CallbackQuery):
    """Обработка согласия на обработку ПД"""
    user_id = callback.from_user.id
    
    # Сохраняем факт согласия в БД
    await save_privacy_consent(user_id, True)
    
    # Теперь запрашиваем номер телефона
    phone_text = "✅ Спасибо за согласие!\n\n"
    phone_text += "📱 Теперь поделитесь номером телефона для завершения регистрации.\n\n"
    phone_text += "Нажмите кнопку ниже 👇"
    
    # Кнопка для отправки номера телефона
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Поделиться номером телефона", request_contact=True)]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    
    await callback.message.edit_text(phone_text)
    await callback.message.answer("Поделитесь номером телефона:", reply_markup=keyboard)
    await callback.answer()

@router.callback_query(F.data == "disagree_privacy")
async def handle_privacy_disagreement(callback: CallbackQuery):
    """Обработка отказа от согласия на обработку ПД"""
    user_id = callback.from_user.id
    
    # Сохраняем факт отказа
    await save_privacy_consent(user_id, False)
    
    disagree_text = "❌ <b>Согласие не предоставлено</b>\n\n"
    disagree_text += "К сожалению, без согласия на обработку персональных данных использование бота невозможно.\n\n"
    disagree_text += "Это требование российского законодательства (152-ФЗ \"О персональных данных\").\n\n"
    disagree_text += "Если передумаете, используйте команду /start"
    
    await callback.message.edit_text(disagree_text)
    await callback.answer()

@router.message(F.contact)
async def handle_contact(message: Message):
    """Обработка полученного контакта"""
    contact = message.contact
    user_id = message.from_user.id
    
    # Проверяем, что пользователь отправил свой номер
    if contact.user_id != user_id:
        await message.answer(
            "❌ Пожалуйста, отправьте свой собственный номер телефона, а не чужой.",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text="📱 Поделиться номером телефона", request_contact=True)]],
                resize_keyboard=True,
                one_time_keyboard=True
            )
        )
        return
    
    # Проверяем наличие согласия на обработку ПД
    temp_user = await UserQueries.get_user(user_id)
    if not temp_user:
        await message.answer(
            "❌ Пользователь не найден в системе.\n\n"
            "Пожалуйста, используйте команду /start для регистрации.",
            reply_markup=ReplyKeyboardRemove()
        )
        return
    
    # Проверяем согласие (оно должно быть True)
    privacy_consent = temp_user.get('privacy_consent')
    if privacy_consent != 1 and privacy_consent != True:  # SQLite может возвращать 0/1 вместо False/True
        await message.answer(
            "❌ Не найдено согласие на обработку персональных данных.\n\n"
            "Пожалуйста, сначала дайте согласие, используя команду /start",
            reply_markup=ReplyKeyboardRemove()
        )
        return
    
    phone_number = contact.phone_number
    
    # Приводим номер к единому формату (добавляем + если нет)
    if not phone_number.startswith('+'):
        phone_number = '+' + phone_number
    
    # Проверяем, нет ли уже пользователя с таким номером
    existing_phone_user = await UserQueries.get_user_by_phone(phone_number)
    
    if existing_phone_user and existing_phone_user['user_id'] != user_id:
        # Номер уже используется другим пользователем
        await message.answer(
            "❌ Этот номер телефона уже используется другим пользователем.\n\n"
            "Если это ваш номер, обратитесь в поддержку.",
            reply_markup=ReplyKeyboardRemove()
        )
        return
    
    # Обновляем пользователя с реальным номером телефона
    # ВАЖНО: Сохраняем реферера из временной записи!
    referrer_phone = temp_user.get('referrer_phone')
    print(f"🔍 Данные пользователя из БД: {temp_user}")
    print(f"🔍 Извлеченный реферер: {referrer_phone}")
    
    await UserQueries.create_user(
        user_id=user_id,
        phone_number=phone_number,
        username=temp_user['username'],
        first_name=temp_user['first_name'],
        referrer_phone=referrer_phone  # Передаем реферера из временной записи
    )
    
    # Сохраняем факт согласия с новым номером
    await save_privacy_consent_with_phone(user_id, phone_number, True)
    
    # Получаем обновленные данные пользователя
    user_data = await UserQueries.get_user(user_id)
    
    success_text = "✅ Номер телефона успешно привязан!\n\n"
    success_text += "📋 Ваше согласие на обработку персональных данных зафиксировано в соответствии с 152-ФЗ.\n\n"
    
    # Проверяем реферальную программу
    if user_data['referrer_phone'] and user_data['referrer_phone'] != phone_number:
        success_text += "🎉 Вы зарегистрировались по реферальной ссылке!\n"
        success_text += "После оплаты подписки пригласивший вас пользователь получит бонус.\n\n"
    
    await message.answer(success_text, reply_markup=ReplyKeyboardRemove())
    
    # Показываем главное меню
    from handlers.start import show_main_menu
    await show_main_menu(message, user_data, is_new_message=True)

async def save_temp_user_data(user_id: int, username: str, first_name: str, referrer_phone: str):
    """Сохранение временных данных пользователя"""
    # Используем специальный временный номер телефона
    temp_phone = f"temp_{user_id}"
    
    print(f"🔍 Сохраняем временные данные: user_id={user_id}, referrer_phone={referrer_phone}")
    
    await UserQueries.create_user(
        user_id=user_id,
        phone_number=temp_phone,
        username=username,
        first_name=first_name,
        referrer_phone=referrer_phone
    )

async def save_privacy_consent(user_id: int, consent: bool):
    """Сохранение согласия на обработку ПД"""
    try:
        from database.connection import db
        
        # НЕ используем INSERT OR REPLACE! Только UPDATE
        await db.execute("""
            UPDATE users 
            SET privacy_consent = ?, privacy_consent_date = CURRENT_TIMESTAMP
            WHERE user_id = ?
        """, (consent, user_id))
        
        print(f"💾 Согласие пользователя {user_id}: {consent}")
    except Exception as e:
        print(f"❌ Ошибка сохранения согласия: {e}")

async def save_privacy_consent_with_phone(user_id: int, phone_number: str, consent: bool):
    """Сохранение согласия на обработку ПД с номером телефона"""
    try:
        from database.connection import db
        
        await db.execute("""
            UPDATE users 
            SET privacy_consent = ?, privacy_consent_date = CURRENT_TIMESTAMP
            WHERE user_id = ? OR phone_number = ?
        """, (consent, user_id, phone_number))
        
        print(f"💾 Согласие пользователя {user_id} ({phone_number}): {consent}")
    except Exception as e:
        print(f"❌ Ошибка сохранения согласия: {e}")