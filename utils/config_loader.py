import os
from typing import Dict, Any

class Config:
    """Класс для загрузки настроек из файла config/settings.txt"""
    
    def __init__(self):
        self.settings = {}
        self.load_settings()
    
    def load_settings(self) -> None:
        """Загружает настройки из файла config/settings.txt"""
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'settings.txt')
        
        try:
            with open(config_path, 'r', encoding='utf-8') as file:
                for line in file:
                    line = line.strip()
                    # Пропускаем комментарии и пустые строки
                    if line and not line.startswith('#'):
                        if '=' in line:
                            key, value = line.split('=', 1)
                            self.settings[key.strip()] = value.strip()
        except FileNotFoundError:
            print(f"Файл настроек не найден: {config_path}")
            raise
        except Exception as e:
            print(f"Ошибка при чтении настроек: {e}")
            raise
    
    def get(self, key: str, default: Any = None) -> str:
        """Получает значение настройки по ключу"""
        return self.settings.get(key, default)
    
    def get_int(self, key: str, default: int = 0) -> int:
        """Получает числовое значение настройки"""
        try:
            return int(self.get(key, default))
        except (ValueError, TypeError):
            return default
    
    def get_float(self, key: str, default: float = 0.0) -> float:
        """Получает значение с плавающей точкой"""
        try:
            return float(self.get(key, default))
        except (ValueError, TypeError):
            return default

# Глобальный экземпляр конфигурации
config = Config()

def load_tariff2_strings() -> list[str]:
    """Загружает строки для тарифа 2 из файла"""
    strings_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'tariff2_strings.txt')
    
    try:
        with open(strings_path, 'r', encoding='utf-8') as file:
            lines = []
            for line in file:
                line = line.strip()
                # Пропускаем комментарии и пустые строки
                if line and not line.startswith('#'):
                    lines.append(line)
            return lines
    except FileNotFoundError:
        print(f"Файл строк тарифа 2 не найден: {strings_path}")
        return []
    except Exception as e:
        print(f"Ошибка при чтении строк тарифа 2: {e}")
        return []