from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
import uuid
from datetime import datetime

from database.queries import UserQueries, PaymentQueries, ReferralQueries
from utils.config_loader import config, load_tariff2_strings
from services.payment_service import PaymentService

router = Router()

@router.callback_query(F.data.startswith("buy_tariff_"))
async def handle_tariff_purchase(callback: CallbackQuery):
    """Обработка покупки тарифа"""
    user_id = callback.from_user.id
    tariff_type = int(callback.data.split("_")[-1])  # buy_tariff_1 -> 1
    
    # Получаем данные пользователя
    user_data = await UserQueries.get_user(user_id)
    if not user_data:
        await callback.answer("❌ Ошибка: пользователь не найден")
        return
    
    # Определяем цену тарифа
    if tariff_type == 1:
        original_price = config.get_int('TARIFF_1_PRICE')
        tariff_name = "Тариф 1 (Базовый)"
    elif tariff_type == 2:
        original_price = config.get_int('TARIFF_2_PRICE')
        tariff_name = "Тариф 2 (Премиум)"
    else:
        await callback.answer("❌ Неверный тариф")
        return
    
    # Применяем реферальную скидку
    referral_balance = user_data['referral_balance']
    discount_amount = min(referral_balance, original_price)
    final_price = original_price - discount_amount
    
    # Формируем текст
    payment_text = f"💳 <b>Оплата подписки</b>\n\n"
    payment_text += f"📦 Тариф: {tariff_name}\n"
    payment_text += f"💰 Стоимость: {original_price}₽\n"
    
    if discount_amount > 0:
        payment_text += f"🎁 Ваша скидка: -{discount_amount}₽\n"
        payment_text += f"💸 К оплате: <b>{final_price}₽</b>\n\n"
    else:
        payment_text += f"💸 К оплате: <b>{final_price}₽</b>\n\n"
    
    # Описание тарифа
    if tariff_type == 1:
        payment_text += "🔓 Что включено:\n• Доступ к боту на 30 дней\n• Безлимитные вопросы к ИИ"
    else:
        payment_text += "🔓 Что включено:\n• Доступ к боту на 30 дней\n• Безлимитные вопросы к ИИ\n• Эксклюзивные материалы курса"
    
    # Проверяем режим разработки
    dev_mode = config.get('DEV_MODE', 'FALSE').upper() == 'TRUE'
    
    if dev_mode:
        # В режиме разработки - и тестовая оплата И реальный CloudPayments
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💳 CloudPayments (тест)", callback_data=f"cloudpay_{tariff_type}_{final_price}_{discount_amount}")],
            [InlineKeyboardButton(text="✅ Быстрая тестовая оплата", callback_data=f"test_pay_{tariff_type}_{final_price}_{discount_amount}")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="main_menu")]
        ])
        payment_text += "\n\n🧪 <b>РЕЖИМ РАЗРАБОТКИ</b>\n"
        payment_text += "• CloudPayments (тест) - настоящий виджет с тестовыми картами\n"
        payment_text += "• Быстрая тестовая оплата - мгновенная эмуляция"
    else:
        # Реальная оплата через CloudPayments
        payment_id = str(uuid.uuid4())
        payment_url = await PaymentService.create_payment(
            amount=final_price,
            description=f"{tariff_name} для пользователя {user_id}",
            payment_id=payment_id,
            user_id=user_id
        )
        
        # Сохраняем платеж в БД
        await PaymentQueries.create_payment(payment_id, user_id, final_price, tariff_type)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💳 Оплатить", url=payment_url)],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="main_menu")]
        ])
    
    await callback.message.edit_text(payment_text, reply_markup=keyboard)
    await callback.answer()

@router.callback_query(F.data.startswith("cloudpay_"))
async def handle_cloudpayments_test(callback: CallbackQuery):
    """Обработка CloudPayments тестовой оплаты"""
    user_id = callback.from_user.id
    
    try:
        # Парсим данные: cloudpay_1_1000_0
        _, tariff_type, final_price, discount_amount = callback.data.split("_")
        tariff_type = int(tariff_type)
        final_price = float(final_price)
        discount_amount = float(discount_amount)
    except (ValueError, IndexError):
        await callback.answer("❌ Ошибка данных платежа")
        return
    
    # Создаем реальную ссылку на CloudPayments
    payment_id = str(uuid.uuid4())
    tariff_name = f"Тариф {tariff_type}"
    
    try:
        payment_url = await PaymentService.create_payment(
            amount=final_price,
            description=f"{tariff_name} для пользователя {user_id}",
            payment_id=payment_id,
            user_id=user_id
        )
        
        # Сохраняем платеж в БД
        await PaymentQueries.create_payment(payment_id, user_id, final_price, tariff_type)
        
        cloudpay_text = "💳 <b>CloudPayments (Тестовый режим)</b>\n\n"
        cloudpay_text += f"💰 Сумма: {final_price}₽\n"
        cloudpay_text += f"📦 Тариф: {tariff_name}\n\n"
        cloudpay_text += "🧪 <b>Тестовые карты для проверки:</b>\n"
        cloudpay_text += "• <code>4242424242424242</code> (Visa)\n"
        cloudpay_text += "• <code>5555555555554444</code> (MasterCard)\n"
        cloudpay_text += "• CVV: любой 3-значный\n"
        cloudpay_text += "• Срок: любая будущая дата\n\n"
        cloudpay_text += "Нажмите кнопку ниже для перехода к оплате:"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💳 Перейти к оплате", url=payment_url)],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="main_menu")]
        ])
        
        await callback.message.edit_text(cloudpay_text, reply_markup=keyboard)
        
    except Exception as e:
        print(f"❌ Ошибка создания CloudPayments платежа: {e}")
        await callback.message.edit_text(
            "❌ Ошибка создания платежа\n\n"
            "Проверьте настройки CloudPayments в config/settings.txt",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🏠 В главное меню", callback_data="main_menu")]
            ])
        )
    
    await callback.answer()

@router.callback_query(F.data.startswith("test_pay_"))
async def handle_test_payment(callback: CallbackQuery):
    """Обработка тестовой оплаты (только в режиме разработки)"""
    user_id = callback.from_user.id
    
    # Проверяем режим разработки
    dev_mode = config.get('DEV_MODE', 'FALSE').upper() == 'TRUE'
    if not dev_mode:
        await callback.answer("❌ Тестовая оплата доступна только в режиме разработки")
        return
    
    try:
        # Парсим данные: test_pay_1_1000_0
        _, _, tariff_type, final_price, discount_amount = callback.data.split("_")
        tariff_type = int(tariff_type)
        final_price = float(final_price)
        discount_amount = float(discount_amount)
    except (ValueError, IndexError):
        await callback.answer("❌ Ошибка данных платежа")
        return
    
    # Имитируем успешную оплату
    user_data = await UserQueries.get_user(user_id)
    if user_data and user_data['phone_number']:
        await process_successful_payment(user_data['phone_number'], tariff_type, final_price, discount_amount, callback.bot, is_test=True)
    else:
        await callback.answer("❌ Ошибка: номер телефона не найден")
        return
    
    success_text = "✅ <b>Тестовая оплата успешна!</b>\n\n"
    success_text += f"📦 Активирован: Тариф {tariff_type}\n"
    success_text += f"💰 Сумма: {final_price}₽\n"
    success_text += "⏱ Срок действия: 30 дней\n\n"
    success_text += "Теперь вы можете пользоваться ботом! 🎉"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 В главное меню", callback_data="main_menu")]
    ])
    
    await callback.message.edit_text(success_text, reply_markup=keyboard)
    await callback.answer("💸 Тестовая оплата прошла успешно!")

async def process_successful_payment(phone_number: str, tariff_type: int, amount: float, discount_used: float, bot=None, is_test: bool = False):
    """Обработка успешной оплаты"""
    
    # Получаем данные пользователя ДО обновления подписки
    user_data_before = await UserQueries.get_user_by_phone(phone_number)
    is_first_payment = not user_data_before.get('has_paid', False) if user_data_before else True
    
    print(f"🔍 Обработка оплаты для {phone_number}, первая оплата: {is_first_payment}")
    
    # Обновляем подписку пользователя по номеру телефона
    await UserQueries.update_subscription(phone_number, tariff_type, days=30)
    
    # Если использована реферальная скидка - списываем с баланса
    if discount_used > 0:
        await ReferralQueries.use_referral_balance(phone_number, discount_used)
    
    # Обрабатываем реферальный бонус если это первая оплата
    if is_first_payment and user_data_before and user_data_before['referrer_phone']:
        referrer_phone = user_data_before['referrer_phone']
        print(f"🔍 Проверяем реферера: {referrer_phone}")
        
        # Проверяем, что реферер существует и оплачивал
        referrer_data = await UserQueries.get_user_by_phone(referrer_phone)
        if referrer_data and referrer_data['has_paid']:
            bonus_amount = config.get_int('REFERRAL_BONUS')
            success = await ReferralQueries.add_referral_bonus(
                referrer_phone, 
                phone_number, 
                bonus_amount
            )
            
            if success:
                print(f"💰 ✅ Реферальный бонус {bonus_amount}₽ начислен рефереру {referrer_phone}")
                
                # Отправляем уведомление рефереру
                if bot and referrer_data['user_id']:
                    try:
                        await bot.send_message(
                            referrer_data['user_id'],
                            f"🎉 <b>Реферальный бонус начислен!</b>\n\n"
                            f"💰 +{bonus_amount}₽ за приглашение друга\n"
                            f"📱 Номер: {phone_number}\n\n"
                            f"Бонус можно использовать как скидку при оплате подписки!"
                        )
                        print(f"📨 Уведомление отправлено рефереру {referrer_data['user_id']}")
                    except Exception as e:
                        print(f"❌ Ошибка отправки уведомления рефереру: {e}")
            else:
                print(f"❌ Ошибка начисления реферального бонуса")
        else:
            if not referrer_data:
                print(f"⚠️ Реферер {referrer_phone} не найден в базе")
            else:
                print(f"⚠️ Реферер {referrer_phone} еще не оплачивал подписку - бонус не начислен")
    elif not is_first_payment:
        print(f"⚠️ Пользователь {phone_number} уже оплачивал ранее - реферальный бонус не начисляется")
    elif not user_data_before or not user_data_before['referrer_phone']:
        print(f"⚠️ У пользователя {phone_number} нет реферера")
    
    # Для тарифа 2 - отправляем материал курса
    if tariff_type == 2:
        # Получаем обновленные данные после обновления подписки
        user_data_after = await UserQueries.get_user_by_phone(phone_number)
        if user_data_after:
            await send_course_material(user_data_after['user_id'], user_data_after['tariff2_counter'], bot)

async def send_course_material(user_id: int, lesson_number: int, bot=None):
    """Отправка материала курса для тарифа 2"""
    strings = load_tariff2_strings()
    
    if lesson_number <= len(strings):
        lesson_content = strings[lesson_number - 1]  # -1 так как индексация с 0
        
        # Формируем красивое сообщение с материалом
        course_message = f"🎓 <b>Новый урок доступен!</b>\n\n"
        course_message += f"📚 <b>Урок {lesson_number}</b>\n\n"
        course_message += f"{lesson_content}\n\n"
        course_message += f"💡 <i>Этот материал доступен только пользователям Тарифа 2</i>"
        
        # Отправляем сообщение пользователю
        if bot:
            try:
                await bot.send_message(user_id, course_message)
                print(f"✅ Урок {lesson_number} отправлен пользователю {user_id}")
            except Exception as e:
                print(f"❌ Ошибка отправки урока пользователю {user_id}: {e}")
        else:
            print(f"⚠️ Бот не передан, урок {lesson_number} не отправлен пользователю {user_id}")
    else:
        print(f"⚠️ Нет урока {lesson_number} для пользователя {user_id} - все материалы исчерпаны")
        
        # Уведомляем пользователя что материалы закончились
        if bot:
            try:
                await bot.send_message(
                    user_id,
                    "📚 <b>Все материалы курса получены!</b>\n\n"
                    "🎉 Поздравляем! Вы получили все доступные уроки курса.\n"
                    "💡 Следите за обновлениями - возможно, скоро появятся новые материалы!"
                )
            except Exception as e:
                print(f"❌ Ошибка отправки уведомления пользователю {user_id}: {e}")