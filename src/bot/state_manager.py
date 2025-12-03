"""Менеджер состояния пользователей бота."""
from typing import Optional, Dict, Any
from datetime import datetime


class StateManager:
    """Управление состоянием пользователей."""
    
    # Хранилище состояний пользователей
    _authorized_users: Dict[int, bool] = {}
    _waiting_for_password: Dict[int, bool] = {}
    _waiting_for_2fa: Dict[int, bool] = {}
    _waiting_for_extra_otp: Dict[int, bool] = {}
    _2fa_codes: Dict[int, Optional[str]] = {}
    _extra_otp_codes: Dict[int, Optional[str]] = {}
    _parsing_active: Dict[int, bool] = {}
    _parsing_status: Dict[int, Optional[Dict[str, Any]]] = {}
    
    @classmethod
    def is_authorized(cls, user_id: int) -> bool:
        """Проверка авторизации пользователя."""
        return cls._authorized_users.get(user_id, False)
    
    @classmethod
    def set_authorized(cls, user_id: int, authorized: bool) -> None:
        """Установка статуса авторизации."""
        cls._authorized_users[user_id] = authorized
    
    @classmethod
    def is_waiting_for_password(cls, user_id: int) -> bool:
        """Проверка ожидания пароля."""
        return cls._waiting_for_password.get(user_id, False)
    
    @classmethod
    def set_waiting_for_password(cls, user_id: int, waiting: bool) -> None:
        """Установка ожидания пароля."""
        cls._waiting_for_password[user_id] = waiting
    
    @classmethod
    def is_waiting_for_2fa(cls, user_id: int) -> bool:
        """Проверка ожидания кода 2FA."""
        return cls._waiting_for_2fa.get(user_id, False)
    
    @classmethod
    def set_waiting_for_2fa(cls, user_id: int, waiting: bool) -> None:
        """Установка ожидания кода 2FA."""
        cls._waiting_for_2fa[user_id] = waiting
    
    @classmethod
    def get_2fa_code(cls, user_id: int) -> Optional[str]:
        """Получение кода 2FA."""
        return cls._2fa_codes.get(user_id)
    
    @classmethod
    def set_2fa_code(cls, user_id: int, code: Optional[str]) -> None:
        """Установка кода 2FA."""
        cls._2fa_codes[user_id] = code
    
    @classmethod
    def is_waiting_for_extra_otp(cls, user_id: int) -> bool:
        """Проверка ожидания дополнительного кода."""
        return cls._waiting_for_extra_otp.get(user_id, False)
    
    @classmethod
    def set_waiting_for_extra_otp(cls, user_id: int, waiting: bool) -> None:
        """Установка ожидания дополнительного кода."""
        cls._waiting_for_extra_otp[user_id] = waiting
    
    @classmethod
    def get_extra_otp_code(cls, user_id: int) -> Optional[str]:
        """Получение дополнительного кода."""
        return cls._extra_otp_codes.get(user_id)
    
    @classmethod
    def set_extra_otp_code(cls, user_id: int, code: Optional[str]) -> None:
        """Установка дополнительного кода."""
        cls._extra_otp_codes[user_id] = code
    
    @classmethod
    def is_parsing_active(cls, user_id: int) -> bool:
        """Проверка активности парсинга."""
        return cls._parsing_active.get(user_id, False)
    
    @classmethod
    def set_parsing_active(cls, user_id: int, active: bool) -> None:
        """Установка активности парсинга."""
        cls._parsing_active[user_id] = active
    
    @classmethod
    def get_parsing_status(cls, user_id: int) -> Optional[Dict[str, Any]]:
        """Получение статуса парсинга."""
        return cls._parsing_status.get(user_id)
    
    @classmethod
    def set_parsing_status(cls, user_id: int, status: Dict[str, Any]) -> None:
        """Установка статуса парсинга."""
        if 'time' not in status:
            status['time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cls._parsing_status[user_id] = status
    
    @classmethod
    def logout(cls, user_id: int) -> None:
        """Выход пользователя."""
        cls._authorized_users.pop(user_id, None)
        cls._waiting_for_password.pop(user_id, None)
        cls._waiting_for_2fa.pop(user_id, None)
        cls._waiting_for_extra_otp.pop(user_id, None)
        cls._2fa_codes.pop(user_id, None)
        cls._extra_otp_codes.pop(user_id, None)
        cls._parsing_active.pop(user_id, None)
        cls._parsing_status.pop(user_id, None)
