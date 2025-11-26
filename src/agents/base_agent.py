"""Базовый класс для ИИ-агентов."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from loguru import logger
from src.config.settings import settings


class BaseAgent(ABC):
    """Базовый класс для всех агентов."""
    
    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        """
        Инициализация агента.
        
        Args:
            name: Имя агента
            config: Конфигурация агента
        """
        self.name = name
        self.config = config or {}
        self.timeout = self.config.get("timeout", settings.agent_timeout)
        logger.info(f"Инициализирован агент: {self.name}")
    
    @abstractmethod
    async def execute(self, *args, **kwargs) -> Any:
        """
        Выполнить основную логику агента.
        
        Args:
            *args: Позиционные аргументы
            **kwargs: Именованные аргументы
            
        Returns:
            Результат выполнения агента
        """
        pass
    
    async def run(self, *args, **kwargs) -> Any:
        """
        Запустить агента с обработкой ошибок.
        
        Args:
            *args: Позиционные аргументы
            **kwargs: Именованные аргументы
            
        Returns:
            Результат выполнения агента
        """
        try:
            logger.info(f"Запуск агента: {self.name}")
            result = await self.execute(*args, **kwargs)
            logger.info(f"Агент {self.name} успешно завершил работу")
            return result
        except Exception as e:
            logger.error(f"Ошибка в агенте {self.name}: {e}")
            raise
    
    def validate_config(self) -> bool:
        """
        Валидация конфигурации агента.
        
        Returns:
            True если конфигурация валидна
        """
        return True

