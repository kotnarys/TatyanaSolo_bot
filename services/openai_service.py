from typing import List, Dict
from utils.config_loader import config
from database.connection import db

class OpenAIService:
    """Сервис для работы с OpenAI API"""
    
    @staticmethod
    async def get_response(user_id: int, user_message: str) -> str:
        """Получение ответа от OpenAI с учетом контекста"""
        
        # Проверяем наличие API ключа
        api_key = config.get('OPENAI_API_KEY')
        if not api_key or api_key == 'TEMP_PLACEHOLDER':
            # Режим разработки - возвращаем заглушку
            await OpenAIService._save_message_to_history(user_id, user_message, "dev_response")
            return f"🤖 <b>Режим разработки</b>\n\nВаше сообщение: <i>{user_message}</i>\n\n" \
                   f"OpenAI API пока не настроен. Это заглушка ответа.\n" \
                   f"После настройки API здесь будет настоящий ИИ-ассистент!"
        
        try:
            # Получаем историю сообщений (последние 10)
            message_history = await OpenAIService._get_message_history(user_id)
            
            # TODO: Здесь будет реальная интеграция с OpenAI
            # import openai
            # openai.api_key = api_key
            
            # Временная заглушка
            ai_response = f"Ответ ИИ на ваше сообщение: {user_message}"
            
            # Сохраняем сообщение и ответ в историю
            await OpenAIService._save_message_to_history(user_id, user_message, ai_response)
            
            return ai_response
            
        except Exception as e:
            print(f"❌ Ошибка OpenAI API: {e}")
            return "😔 Произошла ошибка при обработке вашего запроса. Попробуйте позже."
    
    @staticmethod
    async def _get_message_history(user_id: int, limit: int = 10) -> List[Dict[str, str]]:
        """Получение истории сообщений пользователя"""
        try:
            rows = await db.fetchall("""
                SELECT message, response FROM chat_history 
                WHERE user_id = ? 
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (user_id, limit))
            
            # Возвращаем в обратном порядке (старые сообщения первыми)
            history = []
            for row in reversed(rows):
                history.append({
                    "role": "user",
                    "content": row[0]
                })
                if row[1]:  # Если есть ответ
                    history.append({
                        "role": "assistant", 
                        "content": row[1]
                    })
            
            return history
            
        except Exception as e:
            print(f"❌ Ошибка получения истории: {e}")
            return []
    
    @staticmethod
    async def _save_message_to_history(user_id: int, message: str, response: str) -> None:
        """Сохранение сообщения в историю"""
        try:
            await db.execute("""
                INSERT INTO chat_history (user_id, message, response)
                VALUES (?, ?, ?)
            """, (user_id, message, response))
            
            # Удаляем старые сообщения (оставляем только последние 20 записей)
            await db.execute("""
                DELETE FROM chat_history 
                WHERE user_id = ? AND id NOT IN (
                    SELECT id FROM chat_history 
                    WHERE user_id = ? 
                    ORDER BY timestamp DESC 
                    LIMIT 20
                )
            """, (user_id, user_id))
            
        except Exception as e:
            print(f"❌ Ошибка сохранения в историю: {e}")
    
    @staticmethod
    async def setup_real_openai_integration():
        """Настройка реальной интеграции с OpenAI (для будущего использования)"""
        # TODO: Раскомментировать когда будет готов API ключ
        
        # import openai
        # from openai import OpenAI
        
        # api_key = config.get('OPENAI_API_KEY')
        # client = OpenAI(api_key=api_key)
        
        # system_message = config.get('OPENAI_SYSTEM_MESSAGE', 'Ты полезный ассистент.')
        
        # # Пример запроса к OpenAI
        # response = await client.chat.completions.create(
        #     model="gpt-3.5-turbo",  # ИЛИ ЗАМЕНИ НА НУЖНУЮ МОДЕЛЬ
        #     messages=[
        #         {"role": "system", "content": system_message},
        #         *message_history,
        #         {"role": "user", "content": user_message}
        #     ],
        #     max_tokens=1000,
        #     temperature=0.7
        # )
        
        # return response.choices[0].message.content
        
        pass