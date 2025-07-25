from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import StateFilter

from database.queries import UserQueries
from services.openai_service import OpenAIService

router = Router()

@router.message(F.text & ~F.text.startswith("/"))
async def handle_user_message(message: Message):
    """Обработка обычных сообщений пользователя"""
    user_id = message.from_user.id
    user_text = message.text
    
    # Проверяем подписку пользователя
    has_subscription = await UserQueries.check_subscription(user_id)
    
    if not has_subscription:
        await message.answer(
            "❌ У вас нет активной подписки!\n\n"
            "Для использования бота оформите подписку командой /start"
        )
        return
    
    # Показываем, что бот печатает
    await message.bot.send_chat_action(chat_id=user_id, action="typing")
    
    try:
        # Получаем ответ от OpenAI (или заглушки)
        ai_response = await OpenAIService.get_response(user_id, user_text)
        
        # Отправляем ответ пользователю
        await message.answer(ai_response)
        
    except Exception as e:
        print(f"❌ Ошибка при обработке сообщения: {e}")
        await message.answer(
            "😔 Произошла ошибка при обработке вашего сообщения.\n"
            "Попробуйте еще раз через несколько секунд."
        )