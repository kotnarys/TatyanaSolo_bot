from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from datetime import datetime

from database.queries import UserQueries
from utils.config_loader import config

router = Router()

@router.message(Command("profile"))
@router.callback_query(F.data == "profile")
async def show_profile(update):
    """Показать профиль пользователя"""
    if isinstance(update, CallbackQuery):
        user_id = update.from_user.id
        message = update.message
        answer_method = message.edit_text
    else:
        user_id = update.from_user.id
        message = update
        answer_method = message.answer
    
    user_data = await UserQueries.get_user(user_id)
    if not user_data:
        await answer_method("❌ Пользователь не найден")
        return
    
    # Формируем текст профиля
    profile_text = f"👤 <b>Ваш профиль</b>\n\n"
    profile_text += f"🆔 ID: <code>{user_id}</code>\n"
    profile_text += f"📱 Телефон: <code>{user_data['phone_number']}</code>\n"
    profile_text += f"👤 Имя: {user_data['first_name'] or 'Не указано'}\n"
    
    if user_data['username']:
        profile_text += f"📱 Username: @{user_data['username']}\n"
    
    # Статус подписки
    if user_data['subscription_end']:
        end_date = datetime.fromisoformat(user_data['subscription_end'])
        if end_date > datetime.now():
            profile_text += f"✅ Подписка активна до: {end_date.strftime('%d.%m.%Y %H:%M')}\n"
            profile_text += f"📦 Тариф: {user_data['tariff_type']}\n"
            if user_data['tariff_type'] == 2:
                profile_text += f"📚 Получено уроков: {user_data['tariff2_counter']}\n"
        else:
            profile_text += "❌ Подписка истекла\n"
    else:
        profile_text += "❌ Подписка не активна\n"
    
    # Реферальный баланс
    if user_data['referral_balance'] > 0:
        profile_text += f"💰 Реферальный баланс: {user_data['referral_balance']}₽\n"
    
    # Кнопки
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 Реферальная программа", callback_data="referral")],
        [InlineKeyboardButton(text="🏠 В главное меню", callback_data="main_menu")]
    ])
    
    await answer_method(profile_text, reply_markup=keyboard)

@router.message(Command("referral"))
@router.callback_query(F.data == "referral")
async def show_referral(update):
    """Показать реферальную программу"""
    if isinstance(update, CallbackQuery):
        user_id = update.from_user.id
        message = update.message
        answer_method = message.edit_text
    else:
        user_id = update.from_user.id
        message = update
        answer_method = message.answer
    
    user_data = await UserQueries.get_user(user_id)
    if not user_data:
        await answer_method("❌ Пользователь не найден")
        return
    
    # Проверяем, есть ли у пользователя право на реферальную программу
    if not user_data['has_paid']:
        referral_text = "❌ <b>Реферальная программа недоступна</b>\n\n"
        referral_text += "Для участия в реферальной программе необходимо хотя бы один раз оплатить подписку."
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💳 Оплатить подписку", callback_data="show_tariffs")],
            [InlineKeyboardButton(text="🏠 В главное меню", callback_data="main_menu")]
        ])
    else:
        # Генерируем реферальную ссылку на основе номера телефона
        bot_username = config.get('BOT_USERNAME', 'your_bot_username')
        # Убираем + и делаем короткий параметр
        phone_clean = user_data['phone_number'].replace('+', '')
        referral_link = f"https://t.me/{bot_username}?start=r{phone_clean}"
        
        referral_text = f"👥 <b>Реферальная программа</b>\n\n"
        referral_text += f"💰 Ваш реферальный баланс: <b>{user_data['referral_balance']}₽</b>\n\n"
        referral_text += "🎁 <b>Как это работает:</b>\n"
        referral_text += f"• Приглашайте друзей по вашей ссылке\n"
        referral_text += f"• Когда друг оплачивает подписку, вы получаете {config.get_int('REFERRAL_BONUS')}₽\n"
        referral_text += f"• Бонусы можно использовать как скидку при оплате\n\n"
        referral_text += f"🔗 <b>Ваша реферальная ссылка:</b>\n"
        referral_text += f"<code>{referral_link}</code>\n\n"
        referral_text += f"🚨 <b>ОЧЕНЬ ВАЖНО!</b> Скажите другу:\n"
        referral_text += f"1️⃣ Перейти по ссылке\n"
        referral_text += f"2️⃣ ОБЯЗАТЕЛЬНО написать /start в чате с ботом\n"
        referral_text += f"3️⃣ НЕ нажимать кнопку START в профиле!\n\n"
        referral_text += f"📱 <b>Если ссылка не работает:</b>\n"
        referral_text += f"Друг может указать ваш номер <code>{user_data['phone_number']}</code> при регистрации"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📤 Поделиться ссылкой", url=f"https://t.me/share/url?url={referral_link}")],
            [InlineKeyboardButton(text="🏠 В главное меню", callback_data="main_menu")]
        ])
    
    await answer_method(referral_text, reply_markup=keyboard)

@router.callback_query(F.data == "show_tariffs")
async def show_tariffs(callback: CallbackQuery):
    """Показать доступные тарифы"""
    user_id = callback.from_user.id
    user_data = await UserQueries.get_user(user_id)
    
    tariff_text = "📦 <b>Доступные тарифы</b>\n\n"
    
    # Цены с учетом реферального баланса
    tariff1_price = config.get_int('TARIFF_1_PRICE')
    tariff2_price = config.get_int('TARIFF_2_PRICE')
    referral_balance = user_data['referral_balance'] if user_data else 0
    
    if referral_balance > 0:
        tariff1_final = max(0, tariff1_price - referral_balance)
        tariff2_final = max(0, tariff2_price - referral_balance)
        
        tariff_text += f"💰 Ваша скидка: {referral_balance}₽\n\n"
        tariff_text += f"💳 <b>Тариф 1</b> - ~~{tariff1_price}₽~~ <b>{tariff1_final}₽</b>\n"
        tariff_text += "• Доступ к боту на 30 дней\n\n"
        
        tariff_text += f"💎 <b>Тариф 2</b> - ~~{tariff2_price}₽~~ <b>{tariff2_final}₽</b>\n"
        tariff_text += "• Доступ к боту на 30 дней\n"
        tariff_text += "• Материалы курса после каждой оплаты\n"
    else:
        tariff_text += f"💳 <b>Тариф 1</b> - {tariff1_price}₽\n"
        tariff_text += "• Доступ к боту на 30 дней\n\n"
        
        tariff_text += f"💎 <b>Тариф 2</b> - {tariff2_price}₽\n"
        tariff_text += "• Доступ к боту на 30 дней\n"
        tariff_text += "• Материалы курса после каждой оплаты\n"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Купить Тариф 1", callback_data="buy_tariff_1")],
        [InlineKeyboardButton(text="💎 Купить Тариф 2", callback_data="buy_tariff_2")],
        [InlineKeyboardButton(text="🏠 В главное меню", callback_data="main_menu")]
    ])
    
    await callback.message.edit_text(tariff_text, reply_markup=keyboard)
    await callback.answer()