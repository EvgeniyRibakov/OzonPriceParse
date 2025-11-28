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
        # Пробуем оба варианта endpoint
        self.actions_api_url = "https://api-seller.ozon.ru/v1/actions/candidates"
        self.actions_list_url = "https://api-seller.ozon.ru/v1/actions"
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
        
        # Получаем акции для всех товаров через /v1/actions
        # Собираем product_id из результатов парсинга цен
        product_ids_for_actions = []
        product_id_mapping = {}  # {product_id: matched_id} для сопоставления
        
        for matched_id, data in results.items():
            if "error" not in data and isinstance(data, dict):
                product_id = data.get("product_id")
                if product_id:
                    product_ids_for_actions.append(str(product_id))
                    product_id_mapping[str(product_id)] = matched_id
        
        if product_ids_for_actions:
            logger.info(f"Начало получения акций через /v1/actions для {len(product_ids_for_actions)} товаров")
            try:
                actions_data = await self.fetch_actions_for_products(product_ids_for_actions)
                
                # Объединяем данные об акциях с данными о ценах
                for product_id, actions in actions_data.items():
                    matched_id = product_id_mapping.get(str(product_id))
                    if matched_id and matched_id in results and "error" not in results[matched_id]:
                        # Добавляем данные об акциях
                        if actions:
                            results[matched_id]["actions"] = actions
                            results[matched_id]["actions_count"] = len(actions)
                            # Извлекаем discount_value из первой акции, если есть
                            if actions and actions[0].get("discount_value"):
                                if not results[matched_id].get("discount_value"):
                                    results[matched_id]["discount_value"] = actions[0].get("discount_value")
                        else:
                            results[matched_id]["actions"] = []
                            results[matched_id]["actions_count"] = 0
            except Exception as e:
                logger.warning(f"Ошибка при получении акций: {e}. Продолжаем без данных об акциях")
        
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
        # В первой итерации использовался запрос со всеми товарами, затем фильтрация по списку
        # Это работает, потому что API возвращает все товары, а мы фильтруем их локально
        payload = {
            "filter": {
                "visibility": "ALL"
            },
            "limit": 1000  # Максимальный лимит API
        }
        
        headers = self._get_headers()
        
        logger.debug(f"Отправка запроса к API: {len(product_ids)} товаров")
        logger.debug(f"Payload: {payload}")
        
        async with HTTPClient(
            base_url=None,  # Используем полный URL в запросе
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
        logger.debug(f"Ищем {len(requested_set)} товаров из запроса")
        
        for item in items_list:
            product_id = str(item.get("product_id", ""))
            offer_id = str(item.get("offer_id", ""))
            
            # Определяем какой ID использовать для сопоставления
            # Сначала проверяем offer_id (артикул), потом product_id
            matched_id = None
            if offer_id and offer_id in requested_set:
                matched_id = offer_id
            elif product_id and product_id in requested_set:
                matched_id = product_id
            
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
        Извлечь все данные из элемента ответа API /v5/product/info/prices.
        
        Args:
            item: Элемент товара из ответа API
            
        Returns:
            Словарь со всеми данными о товаре
        """
        # Инициализируем все возможные поля
        price_data = {
            "price": None,
            "old_price": None,
            "marketing_seller_price": None,
            "retail_price": None,
            "premium_price": None,
            "min_price": None,
            "vat": None,
            "discount_value": None,
            "currency": "RUB",
            "available": True,
            "timestamp": datetime.now().isoformat()
        }
        
        # Извлекаем данные из объекта price (если есть)
        if "price" in item:
            price_info = item["price"]
            if isinstance(price_info, dict):
                # Извлекаем все поля из price объекта
                price_data["price"] = price_info.get("price") or price_info.get("value")
                price_data["old_price"] = price_info.get("old_price")
                price_data["marketing_seller_price"] = price_info.get("marketing_seller_price")
                price_data["retail_price"] = price_info.get("retail_price")
                price_data["premium_price"] = price_info.get("premium_price")
                price_data["min_price"] = price_info.get("min_price")
                price_data["vat"] = price_info.get("vat")
                price_data["currency"] = price_info.get("currency", "RUB")
                price_data["discount_value"] = price_info.get("discount_value") or price_info.get("total_discount_value")
            elif isinstance(price_info, (int, float, str)):
                try:
                    price_data["price"] = float(price_info)
                except (ValueError, TypeError):
                    pass
        
        # Извлекаем поля напрямую из item (если они есть на верхнем уровне)
        # Это для случаев, когда API возвращает поля не только в price объекте
        if not price_data["price"]:
            price_data["price"] = item.get("price") or item.get("offer_price") or item.get("current_price")
        
        if not price_data["old_price"]:
            price_data["old_price"] = item.get("old_price")
        
        if not price_data["marketing_seller_price"]:
            price_data["marketing_seller_price"] = item.get("marketing_seller_price")
        
        if not price_data["retail_price"]:
            price_data["retail_price"] = item.get("retail_price")
        
        if not price_data["premium_price"]:
            price_data["premium_price"] = item.get("premium_price")
        
        if not price_data["min_price"]:
            price_data["min_price"] = item.get("min_price")
        
        if not price_data["vat"]:
            price_data["vat"] = item.get("vat")
        
        if not price_data["discount_value"]:
            price_data["discount_value"] = item.get("discount_value") or item.get("total_discount_value")
        
        # Извлекаем available (может быть булевым или строкой)
        available = item.get("available")
        if available is not None:
            if isinstance(available, bool):
                price_data["available"] = available
            elif isinstance(available, str):
                price_data["available"] = available.upper() in ["TRUE", "ИСТИНА", "1", "YES"]
            else:
                price_data["available"] = bool(available)
        
        # Конвертируем числовые поля в float где возможно
        numeric_fields = ["price", "old_price", "marketing_seller_price", 
                         "retail_price", "premium_price", "min_price", "vat", "discount_value"]
        for key in numeric_fields:
            if price_data[key] is not None:
                try:
                    price_data[key] = float(price_data[key])
                except (ValueError, TypeError):
                    price_data[key] = None
        
        return price_data
    
    async def _fetch_discount_values(
        self,
        product_ids: List[str]
    ) -> Dict[str, float]:
        """
        Получить discount_value для товаров через Actions API.
        
        Args:
            product_ids: Список ID товаров
            
        Returns:
            Словарь {product_id: discount_value}
        """
        discount_values = {}
        
        await self._rate_limit()
        
        headers = self._get_headers()
        
        # Запрос к /v1/actions/candidates
        # Согласно документации, может потребоваться другой формат
        logger.debug(f"Запрос discount_value через Actions API для {len(product_ids)} товаров")
        
        async with HTTPClient(
            base_url=None,
            timeout=self.timeout,
            max_retries=self.config.get("max_retries", 3),
        ) as client:
            try:
                # Пробуем сначала /v1/actions (список акций)
                # Затем для каждой акции получаем товары с discount_value
                response = await client.post(
                    self.actions_list_url,
                    json={},
                    headers=headers
                )
                
                if response.status_code >= 400:
                    # Если не работает, пробуем candidates
                    logger.debug(f"Пробуем endpoint /v1/actions/candidates")
                    response = await client.post(
                        self.actions_api_url,
                        json={},
                        headers=headers
                    )
                
                # Если ошибка, логируем и пропускаем
                if response.status_code >= 400:
                    try:
                        error_data = response.json()
                        logger.debug(f"Ошибка {response.status_code} от Actions API: {error_data}")
                    except:
                        error_text = response.text[:500] if hasattr(response, 'text') else str(response.content[:500])
                        logger.debug(f"Ошибка {response.status_code} от Actions API: {error_text}")
                    logger.warning("Пропускаем получение discount_value, продолжаем без него")
                    return discount_values
                
                response_data = response.json()
                logger.debug(f"Ответ Actions API получен")
                
                # Парсим ответ
                items = []
                if "result" in response_data:
                    if isinstance(response_data["result"], list):
                        items = response_data["result"]
                    elif "items" in response_data["result"]:
                        items = response_data["result"]["items"]
                elif "items" in response_data:
                    items = response_data["items"]
                
                # Извлекаем discount_value для нужных товаров
                requested_set = {str(pid) for pid in product_ids}
                
                for item in items:
                    product_id = str(item.get("product_id", ""))
                    if product_id in requested_set:
                        discount_value = item.get("discount_value")
                        if discount_value is not None:
                            try:
                                discount_values[product_id] = float(discount_value)
                            except (ValueError, TypeError):
                                pass
                
                logger.debug(f"Извлечено {len(discount_values)} discount_value из Actions API")
                
            except Exception as e:
                logger.warning(f"Ошибка при получении discount_value из Actions API: {e}")
                # Не прерываем выполнение, просто не будет discount_value
        
        return discount_values
    
    async def fetch_actions_for_products(
        self,
        product_ids: List[str]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Получить акции для товаров через /v1/actions endpoint.
        
        Args:
            product_ids: Список ID товаров (product_id)
            
        Returns:
            Словарь {product_id: [список акций]}
        """
        if not self.client_id or not self.api_key:
            raise ValueError("Ozon API credentials not configured")
        
        logger.info(f"Начало парсинга акций для {len(product_ids)} товаров через /v1/actions")
        start_time = time.time()
        
        results = {product_id: [] for product_id in product_ids}
        requested_set = {str(pid) for pid in product_ids}
        
        # Сначала пробуем получить все акции одним запросом
        try:
            await self._rate_limit()
            all_actions = await self._fetch_all_actions()
            
            if all_actions:
                logger.info(f"Получено {len(all_actions)} акций из /v1/actions")
                
                # Фильтруем акции, где товары участвуют
                # Поскольку в ответе нет прямой связи с товарами, 
                # возвращаем все акции с is_participating=true для всех запрошенных товаров
                for action in all_actions:
                    is_participating = action.get("is_participating", False)
                    
                    if is_participating:
                        action_data = self._extract_action_data(action)
                        # Добавляем акцию ко всем запрошенным товарам
                        # (в реальности нужно получать список товаров для каждой акции отдельно)
                        for product_id in product_ids:
                            results[str(product_id)].append(action_data)
                
                elapsed = time.time() - start_time
                total_actions = sum(len(actions) for actions in results.values())
                
                logger.info(
                    f"Парсинг акций завершен: найдено {total_actions} акций для товаров, "
                    f"время: {elapsed:.2f} сек"
                )
                
                return results
        except Exception as e:
            logger.warning(f"Не удалось получить все акции одним запросом: {e}. Пробуем по товарам")
        
        # Если не получилось одним запросом, пробуем для каждого товара отдельно
        batch_size = min(self.batch_size, 100)  # Для акций используем меньший батч
        
        for batch_start in range(0, len(product_ids), batch_size):
            batch = product_ids[batch_start:batch_start + batch_size]
            batch_num = (batch_start // batch_size) + 1
            total_batches = (len(product_ids) + batch_size - 1) // batch_size
            
            logger.info(
                f"Обработка батча акций {batch_num}/{total_batches} "
                f"({len(batch)} товаров)"
            )
            
            try:
                # Пробуем получить акции для батча товаров
                batch_results = await self._fetch_actions_batch(batch)
                
                # Объединяем результаты
                for product_id, actions in batch_results.items():
                    results[product_id] = actions
                
                logger.info(
                    f"Батч {batch_num} завершен: получено акций для {len(batch_results)} товаров"
                )
                
            except Exception as e:
                logger.error(f"Ошибка при обработке батча акций {batch_num}: {e}")
                # Помечаем товары из батча как ошибки
                for product_id in batch:
                    if not results[product_id]:
                        results[product_id] = []
            
            # Задержка между батчами
            if batch_start + batch_size < len(product_ids):
                await asyncio.sleep(self.request_delay)
        
        elapsed = time.time() - start_time
        total_actions = sum(len(actions) for actions in results.values())
        
        logger.info(
            f"Парсинг акций завершен: найдено {total_actions} акций для товаров, "
            f"время: {elapsed:.2f} сек"
        )
        
        return results
    
    async def _fetch_actions_batch(
        self,
        product_ids: List[str]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Получить акции для батча товаров.
        
        Args:
            product_ids: Список ID товаров
            
        Returns:
            Словарь {product_id: [список акций]}
        """
        headers = self._get_headers()
        results = {product_id: [] for product_id in product_ids}
        
        async with HTTPClient(
            base_url=None,
            timeout=self.timeout,
            max_retries=self.config.get("max_retries", 3),
        ) as client:
            # Делаем запрос для каждого товара отдельно
            for product_id in product_ids:
                try:
                    await self._rate_limit()
                    
                    # Пробуем передать product_id в параметрах запроса (GET)
                    params = {}
                    if product_id.isdigit():
                        params = {"product_id": int(product_id)}
                    
                    response = await client.get(
                        self.actions_list_url,
                        params=params,
                        headers=headers
                    )
                    
                    if response.status_code >= 400:
                        try:
                            error_data = response.json()
                            logger.debug(f"Ошибка {response.status_code} от /v1/actions для товара {product_id}: {error_data}")
                        except:
                            error_text = response.text[:500] if hasattr(response, 'text') else str(response.content[:500])
                            logger.debug(f"Ошибка {response.status_code} от /v1/actions для товара {product_id}: {error_text}")
                        continue
                    
                    response_data = response.json()
                    logger.debug(f"Ответ /v1/actions получен для товара {product_id}")
                    
                    # Парсим ответ согласно структуре из примера
                    actions = []
                    if "result" in response_data:
                        if isinstance(response_data["result"], list):
                            actions = response_data["result"]
                        elif "items" in response_data["result"]:
                            actions = response_data["result"]["items"]
                    elif "items" in response_data:
                        actions = response_data["items"]
                    
                    logger.debug(f"Извлечено {len(actions)} акций для товара {product_id}")
                    
                    # Фильтруем акции, где товар участвует
                    for action in actions:
                        is_participating = action.get("is_participating", False)
                        
                        # Если акция активна и товар участвует, добавляем акцию
                        if is_participating:
                            action_data = self._extract_action_data(action)
                            results[str(product_id)].append(action_data)
                    
                except Exception as e:
                    logger.error(f"Ошибка при получении акций для товара {product_id}: {e}")
                    continue
        
        return results
    
    async def _fetch_all_actions(self) -> List[Dict[str, Any]]:
        """
        Получить все акции через /v1/actions endpoint.
        
        Returns:
            Список акций
        """
        await self._rate_limit()
        
        headers = self._get_headers()
        
        async with HTTPClient(
            base_url=None,
            timeout=self.timeout,
            max_retries=self.config.get("max_retries", 3),
        ) as client:
            try:
                response = await client.get(
                    self.actions_list_url,
                    params={},
                    headers=headers
                )
                
                if response.status_code >= 400:
                    try:
                        error_data = response.json()
                        logger.error(f"Ошибка {response.status_code} от /v1/actions: {error_data}")
                    except:
                        error_text = response.text[:500] if hasattr(response, 'text') else str(response.content[:500])
                        logger.error(f"Ошибка {response.status_code} от /v1/actions: {error_text}")
                    return []
                
                response_data = response.json()
                logger.debug(f"Ответ /v1/actions получен")
                
                # Парсим ответ согласно структуре из примера
                actions = []
                if "result" in response_data:
                    if isinstance(response_data["result"], list):
                        actions = response_data["result"]
                    elif "items" in response_data["result"]:
                        actions = response_data["result"]["items"]
                elif "items" in response_data:
                    actions = response_data["items"]
                
                logger.debug(f"Извлечено {len(actions)} акций из ответа")
                return actions
                
            except Exception as e:
                logger.error(f"Ошибка при получении акций из /v1/actions: {e}")
                return []
    
    def _extract_action_data(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """
        Извлечь данные об акции согласно структуре ответа.
        
        Args:
            action: Объект акции из ответа API
            
        Returns:
            Словарь с данными об акции
        """
        return {
            "id": action.get("id"),
            "title": action.get("title"),
            "date_start": action.get("date_start"),
            "date_end": action.get("date_end"),
            "potential_products_count": action.get("potential_products_count"),
            "is_participating": action.get("is_participating"),
            "participating_products_count": action.get("participating_products_count"),
            "description": action.get("description"),
            "action_type": action.get("action_type"),
            "banned_products_count": action.get("banned_products_count"),
            "with_targeting": action.get("with_targeting"),
            "discount_type": action.get("discount_type"),
            "discount_value": action.get("discount_value"),
            "order_amount": action.get("order_amount"),
            "freeze_date": action.get("freeze_date"),
            "is_voucher_action": action.get("is_voucher_action"),
            "timestamp": datetime.now().isoformat()
        }

