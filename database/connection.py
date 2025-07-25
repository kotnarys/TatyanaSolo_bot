import aiosqlite
import asyncio
from typing import Optional
from utils.config_loader import config

class Database:
    """Класс для работы с базой данных SQLite"""
    
    def __init__(self):
        self.db_path = "bot_database.db"  # SQLite база для разработки
        self.connection: Optional[aiosqlite.Connection] = None
    
    async def connect(self):
        """Подключение к базе данных"""
        try:
            self.connection = await aiosqlite.connect(self.db_path)
            await self.connection.execute("PRAGMA foreign_keys = ON")  # Включаем внешние ключи
            print("✅ Подключение к базе данных установлено")
            await self.create_tables()
        except Exception as e:
            print(f"❌ Ошибка подключения к БД: {e}")
            raise
    
    async def disconnect(self):
        """Отключение от базы данных"""
        if self.connection:
            await self.connection.close()
            print("✅ Соединение с базой данных закрыто")
    
    async def create_tables(self):
        """Создание всех необходимых таблиц"""
        
        # Таблица пользователей
        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                phone_number TEXT UNIQUE NOT NULL,
                registration_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                referrer_phone TEXT,
                referral_balance REAL DEFAULT 0,
                subscription_end DATETIME,
                tariff_type INTEGER,
                tariff2_counter INTEGER DEFAULT 0,
                has_paid BOOLEAN DEFAULT FALSE,
                privacy_consent BOOLEAN DEFAULT FALSE,
                privacy_consent_date DATETIME,
                waiting_for_referrer BOOLEAN DEFAULT FALSE,
                FOREIGN KEY (referrer_phone) REFERENCES users (phone_number)
            )
        """)
        
        # Таблица платежей
        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                payment_id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                tariff_type INTEGER NOT NULL,
                payment_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'pending',
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)
        
        # Таблица истории чата для OpenAI
        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                response TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)
        
        # Таблица рефералов (для статистики)
        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS referrals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_phone TEXT NOT NULL,
                referred_phone TEXT NOT NULL,
                bonus_amount REAL NOT NULL,
                earned_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (referrer_phone) REFERENCES users (phone_number),
                FOREIGN KEY (referred_phone) REFERENCES users (phone_number)
            )
        """)
        
        await self.connection.commit()
        print("✅ Таблицы базы данных созданы/обновлены")
    
    async def execute(self, query: str, params: tuple = ()):
        """Выполнение SQL запроса"""
        try:
            cursor = await self.connection.execute(query, params)
            await self.connection.commit()
            return cursor
        except Exception as e:
            print(f"❌ Ошибка выполнения запроса: {e}")
            raise
    
    async def fetchone(self, query: str, params: tuple = ()):
        """Получение одной записи"""
        try:
            cursor = await self.connection.execute(query, params)
            return await cursor.fetchone()
        except Exception as e:
            print(f"❌ Ошибка получения записи: {e}")
            raise
    
    async def fetchall(self, query: str, params: tuple = ()):
        """Получение всех записей"""
        try:
            cursor = await self.connection.execute(query, params)
            return await cursor.fetchall()
        except Exception as e:
            print(f"❌ Ошибка получения записей: {e}")
            raise

# Глобальный экземпляр базы данных
db = Database()