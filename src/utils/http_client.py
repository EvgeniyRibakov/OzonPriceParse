"""HTTP клиент для работы с API."""

import asyncio
from typing import Optional, Dict, Any
import httpx
from loguru import logger
from src.config.settings import settings


class HTTPClient:
    """Асинхронный HTTP клиент."""
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3,
    ):
        """
        Инициализация HTTP клиента.
        
        Args:
            base_url: Базовый URL для запросов (None = использовать полные URL в методах)
            timeout: Таймаут запросов в секундах
            max_retries: Максимальное количество повторов
        """
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        """Вход в контекстный менеджер."""
        client_kwargs = {
            "timeout": self.timeout,
            "headers": {"User-Agent": settings.user_agent},
        }
        if self.base_url:
            client_kwargs["base_url"] = self.base_url
        self.client = httpx.AsyncClient(**client_kwargs)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Выход из контекстного менеджера."""
        if self.client:
            await self.client.aclose()
    
    async def get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> httpx.Response:
        """
        Выполнить GET запрос.
        
        Args:
            url: URL для запроса
            params: Параметры запроса
            headers: Дополнительные заголовки
            
        Returns:
            Ответ от сервера
            
        Raises:
            httpx.HTTPError: При ошибке запроса
        """
        if not self.client:
            raise RuntimeError("HTTPClient не инициализирован. Используйте async with.")
        
        for attempt in range(self.max_retries):
            try:
                response = await self.client.get(
                    url,
                    params=params,
                    headers=headers,
                )
                response.raise_for_status()
                return response
            except httpx.HTTPError as e:
                if attempt == self.max_retries - 1:
                    logger.error(f"Ошибка при запросе {url}: {e}")
                    raise
                logger.warning(f"Попытка {attempt + 1}/{self.max_retries} не удалась: {e}")
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
    
    async def post(
        self,
        url: str,
        json: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> httpx.Response:
        """
        Выполнить POST запрос.
        
        Args:
            url: URL для запроса
            json: JSON данные
            data: Form data
            headers: Дополнительные заголовки
            
        Returns:
            Ответ от сервера
            
        Raises:
            httpx.HTTPError: При ошибке запроса
        """
        if not self.client:
            raise RuntimeError("HTTPClient не инициализирован. Используйте async with.")
        
        for attempt in range(self.max_retries):
            try:
                response = await self.client.post(
                    url,
                    json=json,
                    data=data,
                    headers=headers,
                )
                response.raise_for_status()
                return response
            except httpx.HTTPError as e:
                if attempt == self.max_retries - 1:
                    logger.error(f"Ошибка при запросе {url}: {e}")
                    raise
                logger.warning(f"Попытка {attempt + 1}/{self.max_retries} не удалась: {e}")
                await asyncio.sleep(2 ** attempt)  # Exponential backoff

