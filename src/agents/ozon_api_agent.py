"""Агент для парсинга цен через Ozon Seller API."""

import asyncio
import time
from typing import Dict, Any, List, Optional
from datetime import datetime
from loguru import logger
from src.agents.base_agent import BaseAgent
from src.utils.http_client import HTTPClient
from src.config.settings import settings


class OzonAPIAgent(BaseAgent):
    """Агент для парсинга цен товаров через Ozon Seller API."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Инициализация агента парсинга цен через API.
        
        Args:
            config: Конфигурация агента
        """
        super().__init__(name="OzonAPIAgent", config=config)
        self.api_url = "https://api-seller.ozon.ru/v5/product/info/prices"
        self.client_id = self.config.get("client_id") or settings.ozon_client_id
        self.api_key = self.config.get("api_key") or settings.ozon_api_key
        self.batch_size = self.config.get("batch_size", settings.batch_size)
        self.request_delay = self.config.get("request_delay", settings.request_delay)
        self.max_requests_per_minute = self.config.get(
            "max_requests_per_minute", 
            settings.max_requests_per_minute
        )
        
        # Rate limiting
        self.last_request_time = 0
        self.request_times = []
        
        if not self.client_id or not self.api_key:
            logger.warning("Ozon API credentials not configured")
    
    def _get_headers(self) -> Dict[str, str]:
        """Получить заголовки для API запросов."""
        return {
            "Client-Id": self.client_id,
            "Api-Key": self.api_key,
            "Content-Type": "application/json"
        }
    
    async def _rate_limit(self) -> None:
        """Ограничение частоты запросов для избежания блокировок."""
        current_time = time.time()
        
        # Удаляем старые запросы (старше минуты)
        self.request_times = [t for t in self.request_times if current_time - t < 60]
        
        # Проверяем лимит запросов в минуту
        if len(self.request_times) >= self.max_requests_per_minute:
            # Ждем пока не освободится место
            sleep_time = 60 - (current_time - self.request_times[0]) + 0.1
            if sleep_time > 0:
                logger.info(f"Rate limit: ожидание {sleep_time:.2f} сек")
                await asyncio.sleep(sleep_time)
                # Обновляем список после ожидания
                current_time = time.time()
                self.request_times = [t for t in self.request_times if current_time - t < 60]
        
        # Минимальная задержка между запросами
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.request_delay:
            await asyncio.sleep(self.request_delay - time_since_last)
        
        # Обновляем время последнего запроса
        self.last_request_time = time.time()
        self.request_times.append(self.last_request_time)
    
    async def execute(self, product_ids: List[str]) -> Dict[str, Any]:
        """
        Парсинг цен для списка товаров через Ozon Seller API.
        
        Args:
            product_ids: Список ID товаров (product_id или offer_id)
            
        Returns:
            Словарь с ценами товаров {product_id: price_data}
        """
        if not self.client_id or not self.api_key:
            raise ValueError("Ozon API credentials not configured")
        
        logger.info(f"Начало парсинга {len(product_ids)} товаров через Ozon Seller API")
        start_time = time.time()
        
        results = {}
        
        # Разбиваем на батчи по 1000 товаров (лимит API)
        for batch_start in range(0, len(product_ids), self.batch_size):
            batch = product_ids[batch_start:batch_start + self.batch_size]
            batch_num = (batch_start // self.batch_size) + 1
            total_batches = (len(product_ids) + self.batch_size - 1) // self.batch_size
            
            logger.info(
                f"Обработка батча {batch_num}/{total_batches} "
                f"({len(batch)} товаров)"
            )
            
            try:
                batch_results = await self._fetch_prices_batch(batch)
                results.update(batch_results)
                
                logger.info(
                    f"Батч {batch_num} завершен: получено {len(batch_results)} цен"
                )
                
            except Exception as e:
                logger.error(f"Ошибка при обработке батча {batch_num}: {e}")
                # Помечаем товары из батча как ошибки
                for product_id in batch:
                    if product_id not in results:
                        results[product_id] = {
                            "error": str(e),
                            "error_type": type(e).__name__
                        }
            
            # Задержка между батчами
            if batch_start + self.batch_size < len(product_ids):
                await asyncio.sleep(self.request_delay)
        
        elapsed = time.time() - start_time
        success_count = sum(1 for v in results.values() if "error" not in v)
        error_count = len(results) - success_count
        
        logger.info(
            f"Парсинг завершен: {success_count} успешно, {error_count} ошибок, "
            f"время: {elapsed:.2f} сек ({elapsed/60:.2f} мин)"
        )
        
        return results
    
    async def _fetch_prices_batch(
        self, 
        product_ids: List[str]
    ) -> Dict[str, Any]:
        """
        Получить цены для батча товаров.
        
        Args:
            product_ids: Список ID товаров
            
        Returns:
            Словарь с ценами {product_id: price_data}
        """
        await self._rate_limit()
        
        # Подготавливаем payload для API
        # Ozon API требует фильтрацию по product_id или offer_id
        # Используем метод получения всех товаров с фильтром
        payload = {
            "filter": {
                "visibility": "ALL"
            },
            "limit": min(len(product_ids), 1000),
            "cursor": ""
        }
        
        headers = self._get_headers()
        
        logger.debug(f"Отправка запроса к API: {len(product_ids)} товаров")
        logger.debug(f"Payload: {payload}")
        
        async with HTTPClient(
            timeout=self.timeout,
            max_retries=self.config.get("max_retries", 3),
        ) as client:
            try:
                response = await client.post(
                    self.api_url,
                    json=payload,
                    headers=headers
                )
                
                response_data = response.json()
                logger.debug(f"Ответ API получен: {len(response_data)} байт")
                
                # Парсим ответ
                return self._parse_api_response(response_data, product_ids)
                
            except Exception as e:
                logger.error(f"Ошибка при запросе к API: {e}")
                raise
    
    def _parse_api_response(
        self, 
        response_data: Dict[str, Any], 
        requested_ids: List[str]
    ) -> Dict[str, Any]:
        """
        Парсить ответ API и извлечь цены.
        
        Args:
            response_data: Ответ от API
            requested_ids: Список запрошенных ID товаров
            
        Returns:
            Словарь с ценами {product_id: price_data}
        """
        results = {}
        requested_set = {str(pid) for pid in requested_ids}
        
        # Извлекаем список товаров из ответа
        items_list = []
        if "items" in response_data:
            items_list = response_data["items"]
        elif "result" in response_data and "items" in response_data["result"]:
            items_list = response_data["result"]["items"]
        
        logger.debug(f"Получено {len(items_list)} товаров из API")
        
        for item in items_list:
            product_id = str(item.get("product_id", ""))
            offer_id = str(item.get("offer_id", ""))
            
            # Определяем какой ID использовать для сопоставления
            matched_id = None
            if product_id in requested_set:
                matched_id = product_id
            elif offer_id in requested_set:
                matched_id = offer_id
            
            if not matched_id:
                continue
            
            # Извлекаем данные о ценах
            price_data = self._extract_price_data(item)
            price_data["product_id"] = product_id
            price_data["offer_id"] = offer_id
            price_data["matched_id"] = matched_id
            
            results[matched_id] = price_data
            
            logger.debug(
                f"Товар {matched_id}: price={price_data.get('price')}, "
                f"marketing_seller_price={price_data.get('marketing_seller_price')}"
            )
        
        # Помечаем товары, которые не были найдены
        found_ids = set(results.keys())
        for req_id in requested_ids:
            if str(req_id) not in found_ids:
                results[str(req_id)] = {
                    "error": "Товар не найден в ответе API",
                    "error_type": "NotFound"
                }
                logger.warning(f"Товар {req_id} не найден в ответе API")
        
        return results
    
    def _extract_price_data(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Извлечь данные о ценах из элемента ответа API.
        
        Args:
            item: Элемент товара из ответа API
            
        Returns:
            Словарь с данными о ценах
        """
        price_data = {
            "price": None,
            "old_price": None,
            "marketing_seller_price": None,
            "retail_price": None,
            "premium_price": None,
            "min_price": None,
            "vat": None,
            "currency": "RUB",
            "available": True,
            "timestamp": datetime.now().isoformat()
        }
        
        # Извлекаем цену из разных возможных мест
        if "price" in item:
            price_info = item["price"]
            if isinstance(price_info, dict):
                price_data["price"] = price_info.get("price") or price_info.get("value")
                price_data["old_price"] = price_info.get("old_price")
                price_data["marketing_seller_price"] = price_info.get("marketing_seller_price")
                price_data["retail_price"] = price_info.get("retail_price")
                price_data["premium_price"] = price_info.get("premium_price")
                price_data["min_price"] = price_info.get("min_price")
                price_data["vat"] = price_info.get("vat")
            elif isinstance(price_info, (int, float, str)):
                try:
                    price_data["price"] = float(price_info)
                except (ValueError, TypeError):
                    pass
        
        # Альтернативные поля
        if not price_data["price"]:
            price_data["price"] = item.get("offer_price") or item.get("current_price")
        
        if not price_data["old_price"]:
            price_data["old_price"] = item.get("old_price")
        
        # Конвертируем в float где возможно
        for key in ["price", "old_price", "marketing_seller_price", 
                     "retail_price", "premium_price", "min_price"]:
            if price_data[key] is not None:
                try:
                    price_data[key] = float(price_data[key])
                except (ValueError, TypeError):
                    price_data[key] = None
        
        return price_data

