"""Клиент для работы со Statistics API Ozon (Цены товаров).

Работает с эндпоинтом Statistics API:
POST https://statistics-api.ozon.ru/v1/price

Документация (схематично):
- Тело запроса: {"skus": ["123", "456", ...]}
- Ответ: {"result": [{"sku": "123", "price": {...}}, ...]}
"""

from typing import Any, Dict, List, Optional

import httpx
from loguru import logger

from src.config.settings import Settings


class OzonApiClient:
    """Простой клиент Statistics API для получения цен по SKU."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or Settings()

        if not self.settings.ozon_client_id or not self.settings.ozon_api_key:
            logger.warning(
                "Ozon API credentials are not configured. "
                "Заполните OZON_CLIENT_ID и OZON_API_KEY в .env, "
                "чтобы можно было вызывать /v1/price."
            )

        self._client = httpx.AsyncClient(
            base_url=self.settings.ozon_api_base_url.rstrip("/"),
            headers={
                "Client-Id": self.settings.ozon_client_id or "",
                "Api-Key": self.settings.ozon_api_key or "",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )

    async def close(self) -> None:
        """Закрыть HTTP‑клиент."""
        await self._client.aclose()

    async def get_prices_by_skus(
        self,
        skus: List[int | str],
        with_seller_currency: bool = True,
    ) -> List[Dict[str, Any]]:
        """Получить цены по списку SKU через /v1/price (Цены товаров).

        :param skus: список SKU (int или str), максимум 100 штук.
        :return: список объектов из поля `result` ответа.
        """
        if not skus:
            logger.warning("Передан пустой список SKU в get_prices_by_skus")
            return []

        if len(skus) > 100:
            raise ValueError("В одном запросе к /v1/price можно передать не более 100 SKU")

        body = {
            "options": {
                # как в примере из доки:
                # "with_seller_currency": true
                "with_seller_currency": with_seller_currency,
            },
            "skus": [str(sku) for sku in skus],
        }
        logger.info(f"Запрос цен /statistics/v1/price для {len(skus)} SKU")

        # Согласно Statistics API, путь имеет префикс /statistics
        response = await self._client.post("/statistics/v1/price", json=body)

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.error(
                f"Ozon API /v1/price вернул ошибку: "
                f"status={exc.response.status_code}, body={exc.response.text}"
            )
            raise

        data: Dict[str, Any] = response.json()

        # Ожидаем структуру:
        # {
        #   "result": [
        #     {
        #       "price": {
        #         "base_price": 100,
        #         "currency": "RUB",
        #         "discount_price": 70,
        #         "ozon_card_price": 50,
        #         "premium_price": 60
        #       },
        #       "sku": 427186572
        #     }
        #   ]
        # }

        result = data.get("result") or []
        if not isinstance(result, list):
            logger.error(f"Неожиданная структура ответа /v1/price: {data}")
            raise ValueError("Ozon API /v1/price вернул неожиданный формат данных")

        logger.debug(f"Получено ценовых записей: {len(result)}")
        return result


async def example_fetch_price() -> None:
    """Пример использования клиента для одного SKU.

    Ориентировочный ожидаемый ответ:
    {
        "result": [
            {
                "price": {
                    "base_price": 100,
                    "currency": "RUB",
                    "discount_price": 70,
                    "ozon_card_price": 50,
                    "premium_price": 60
                },
                "sku": 427186572
            }
        ]
    }
    """

    settings = Settings()
    client = OzonApiClient(settings)

    try:
        prices = await client.get_prices_by_skus([427186572])
        logger.info(f"Ответ от /v1/price: {prices}")
    finally:
        await client.close()


