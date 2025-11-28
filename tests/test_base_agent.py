"""Тесты для базового агента."""

import pytest
from src.agents.base_agent import BaseAgent


class TestAgent(BaseAgent):
    """Тестовый агент для проверки базового класса."""
    
    async def execute(self, *args, **kwargs):
        """Тестовая реализация."""
        return {"result": "success"}


@pytest.mark.asyncio
async def test_base_agent_initialization():
    """Тест инициализации базового агента."""
    agent = TestAgent(name="TestAgent")
    assert agent.name == "TestAgent"
    assert agent.config == {}


@pytest.mark.asyncio
async def test_base_agent_execute():
    """Тест выполнения агента."""
    agent = TestAgent(name="TestAgent")
    result = await agent.run()
    assert result == {"result": "success"}


@pytest.mark.asyncio
async def test_base_agent_error_handling():
    """Тест обработки ошибок."""
    
    class ErrorAgent(BaseAgent):
        async def execute(self, *args, **kwargs):
            raise ValueError("Test error")
    
    agent = ErrorAgent(name="ErrorAgent")
    
    with pytest.raises(ValueError):
        await agent.run()

