"""
Controle de rate limit para APIs externas.
Garante conformidade com os tiers gratuitos de cada serviço.
"""

import time
from collections import defaultdict
from dataclasses import dataclass, field
from threading import Lock


@dataclass
class RateLimitConfig:
    """Configuração de rate limit para um serviço."""
    requests_per_minute: int
    requests_per_day: int


@dataclass
class _BucketState:
    """Estado interno de um bucket de rate limit."""
    minute_timestamps: list[float] = field(default_factory=list)
    daily_count: int = 0
    daily_reset_time: float = 0.0
    lock: Lock = field(default_factory=Lock)


class RateLimiter:
    """
    Rate limiter baseado em janela deslizante (por minuto) e contagem diária.
    Thread-safe para uso com QThread.
    """

    def __init__(self):
        self._configs: dict[str, RateLimitConfig] = {}
        self._states: dict[str, _BucketState] = defaultdict(_BucketState)

    def register_service(self, service_name: str, config: RateLimitConfig):
        """Registra um serviço com seus limites."""
        self._configs[service_name] = config
        state = self._states[service_name]
        state.daily_reset_time = time.time()

    def can_make_request(self, service_name: str) -> bool:
        """Verifica se é possível fazer uma requisição sem violar o limite."""
        if service_name not in self._configs:
            return True

        config = self._configs[service_name]
        state = self._states[service_name]

        with state.lock:
            now = time.time()
            self._cleanup_minute_window(state, now)
            self._check_daily_reset(state, now)

            # Verifica limite por minuto
            if len(state.minute_timestamps) >= config.requests_per_minute:
                return False

            # Verifica limite diário
            if state.daily_count >= config.requests_per_day:
                return False

            return True

    def record_request(self, service_name: str) -> bool:
        """
        Registra uma requisição feita. Retorna True se foi registrada,
        False se o limite foi atingido (não deveria fazer a requisição).
        """
        if service_name not in self._configs:
            return True

        config = self._configs[service_name]
        state = self._states[service_name]

        with state.lock:
            now = time.time()
            self._cleanup_minute_window(state, now)
            self._check_daily_reset(state, now)

            if (len(state.minute_timestamps) >= config.requests_per_minute
                    or state.daily_count >= config.requests_per_day):
                return False

            state.minute_timestamps.append(now)
            state.daily_count += 1
            return True

    def get_wait_time(self, service_name: str) -> float:
        """Retorna segundos restantes até poder fazer próxima requisição."""
        if service_name not in self._configs:
            return 0.0

        config = self._configs[service_name]
        state = self._states[service_name]

        with state.lock:
            now = time.time()
            self._cleanup_minute_window(state, now)

            if len(state.minute_timestamps) < config.requests_per_minute:
                return 0.0

            oldest = state.minute_timestamps[0]
            return max(0.0, 60.0 - (now - oldest))

    def get_remaining(self, service_name: str) -> dict:
        """Retorna contadores restantes para o serviço."""
        if service_name not in self._configs:
            return {"minute": -1, "daily": -1}

        config = self._configs[service_name]
        state = self._states[service_name]

        with state.lock:
            now = time.time()
            self._cleanup_minute_window(state, now)
            self._check_daily_reset(state, now)

            return {
                "minute": config.requests_per_minute - len(state.minute_timestamps),
                "daily": config.requests_per_day - state.daily_count,
            }

    @staticmethod
    def _cleanup_minute_window(state: _BucketState, now: float):
        """Remove timestamps mais antigos que 60 segundos."""
        cutoff = now - 60.0
        state.minute_timestamps = [
            ts for ts in state.minute_timestamps if ts > cutoff
        ]

    @staticmethod
    def _check_daily_reset(state: _BucketState, now: float):
        """Reseta contador diário a cada 24 horas."""
        if now - state.daily_reset_time >= 86400:
            state.daily_count = 0
            state.daily_reset_time = now
