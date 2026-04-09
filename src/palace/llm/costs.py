"""
Sistema de Tracking de Costos para LLM - Palace Framework

Este módulo proporciona un sistema completo para tracking de costos
asociados al uso de modelos LLM, incluyendo:

- Tracking de tokens por modelo y proveedor
- Cálculo de costos basado en precios configurables
- Historial de uso con timestamps
- Estadísticas agregadas por período
- Alertas de presupuesto
- Exportación de datos

Diseñado para ser extensible y production-ready.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4

import structlog

logger = structlog.get_logger()


# =============================================================================
# Enums y Tipos
# =============================================================================


class CostGranularity(str, Enum):
    """Granularidad para reportes de costos."""

    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class PricingModel(str, Enum):
    """Modelo de pricing del proveedor."""

    PER_TOKEN = "per_token"
    """Precio por token (input/output separados)."""

    PER_REQUEST = "per_request"
    """Precio por request (independiente de tokens)."""

    FLAT_RATE = "flat_rate"
    """Tarifa plana (subscription)."""

    TIERED = "tiered"
    """Precio por tiers de volumen."""


class BudgetAlertLevel(str, Enum):
    """Nivel de alerta de presupuesto."""

    INFO = "info"
    """Informativo - 50% del presupuesto."""

    WARNING = "warning"
    """Advertencia - 75% del presupuesto."""

    CRITICAL = "critical"
    """Crítico - 90% del presupuesto."""

    EXCEEDED = "exceeded"
    """Excedido - 100% del presupuesto."""


# =============================================================================
# Modelos de Datos
# =============================================================================


@dataclass
class TokenUsage:
    """
    Registro de uso de tokens.

    Attributes:
        prompt_tokens: Tokens del prompt (input)
        completion_tokens: Tokens de la respuesta (output)
        total_tokens: Total de tokens
        cached_tokens: Tokens servidos desde caché (si aplica)
    """

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cached_tokens: int = 0

    def __post_init__(self):
        """Calcula el total si no está definido."""
        if self.total_tokens == 0:
            self.total_tokens = self.prompt_tokens + self.completion_tokens

    def to_dict(self) -> Dict[str, int]:
        """Convierte a diccionario."""
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "cached_tokens": self.cached_tokens,
        }

    def __add__(self, other: "TokenUsage") -> "TokenUsage":
        """Suma dos usos de tokens."""
        return TokenUsage(
            prompt_tokens=self.prompt_tokens + other.prompt_tokens,
            completion_tokens=self.completion_tokens + other.completion_tokens,
            total_tokens=self.total_tokens + other.total_tokens,
            cached_tokens=self.cached_tokens + other.cached_tokens,
        )


@dataclass
class ModelPricing:
    """
    Información de precios de un modelo.

    Attributes:
        model_id: ID del modelo
        provider: Proveedor del modelo
        input_price_per_1k: Precio por 1k tokens de input (USD)
        output_price_per_1k: Precio por 1k tokens de output (USD)
        pricing_model: Modelo de pricing
        effective_date: Fecha de vigencia del precio
        currency: Moneda (default: USD)
    """

    model_id: str
    provider: str
    input_price_per_1k: float = 0.0
    output_price_per_1k: float = 0.0
    pricing_model: PricingModel = PricingModel.PER_TOKEN
    effective_date: datetime = field(default_factory=datetime.utcnow)
    currency: str = "USD"

    def calculate_cost(self, usage: TokenUsage) -> float:
        """
        Calcula el costo basado en el uso de tokens.

        Args:
            usage: Uso de tokens

        Returns:
            Costo en la moneda configurada
        """
        if self.pricing_model == PricingModel.PER_TOKEN:
            input_cost = (usage.prompt_tokens / 1000) * self.input_price_per_1k
            output_cost = (usage.completion_tokens / 1000) * self.output_price_per_1k
            return input_cost + output_cost
        elif self.pricing_model == PricingModel.PER_REQUEST:
            # Para pricing por request, el costo es fijo
            return self.input_price_per_1k
        elif self.pricing_model == PricingModel.FLAT_RATE:
            # Para tarifa plana, no hay costo adicional
            return 0.0
        else:
            # Para tiered, se necesitaría implementación adicional
            return 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario."""
        return {
            "model_id": self.model_id,
            "provider": self.provider,
            "input_price_per_1k": self.input_price_per_1k,
            "output_price_per_1k": self.output_price_per_1k,
            "pricing_model": self.pricing_model.value,
            "effective_date": self.effective_date.isoformat(),
            "currency": self.currency,
        }


@dataclass
class UsageRecord:
    """
    Registro de uso de un modelo LLM.

    Attributes:
        record_id: ID único del registro
        timestamp: Timestamp del uso
        model_id: ID del modelo usado
        provider: Proveedor del modelo
        usage: Uso de tokens
        cost: Costo calculado
        latency_ms: Latencia en milisegundos
        request_id: ID de la request (para tracing)
        agent: Agente que hizo la request (opcional)
        project_id: ID del proyecto (opcional)
        session_id: ID de la sesión (opcional)
        metadata: Metadatos adicionales
    """

    record_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    model_id: str = ""
    provider: str = ""
    usage: TokenUsage = field(default_factory=TokenUsage)
    cost: float = 0.0
    latency_ms: int = 0
    request_id: Optional[str] = None
    agent: Optional[str] = None
    project_id: Optional[str] = None
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario."""
        return {
            "record_id": self.record_id,
            "timestamp": self.timestamp.isoformat(),
            "model_id": self.model_id,
            "provider": self.provider,
            "usage": self.usage.to_dict(),
            "cost": self.cost,
            "latency_ms": self.latency_ms,
            "request_id": self.request_id,
            "agent": self.agent,
            "project_id": self.project_id,
            "session_id": self.session_id,
            "metadata": self.metadata,
        }


@dataclass
class Budget:
    """
    Presupuesto para tracking de costos.

    Attributes:
        budget_id: ID único del presupuesto
        name: Nombre descriptivo
        total_budget: Presupuesto total
        used_budget: Presupuesto usado
        period: Período del presupuesto
        start_date: Fecha de inicio
        end_date: Fecha de fin (opcional)
        alerts: Configuración de alertas
        is_active: Si el presupuesto está activo
    """

    budget_id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    total_budget: float = 0.0
    used_budget: float = 0.0
    period: CostGranularity = CostGranularity.MONTHLY
    start_date: datetime = field(default_factory=datetime.utcnow)
    end_date: Optional[datetime] = None
    alerts: Dict[str, float] = field(
        default_factory=lambda: {
            "info": 0.5,  # 50%
            "warning": 0.75,  # 75%
            "critical": 0.9,  # 90%
        }
    )
    is_active: bool = True

    @property
    def remaining_budget(self) -> float:
        """Presupuesto restante."""
        return max(0.0, self.total_budget - self.used_budget)

    @property
    def usage_percentage(self) -> float:
        """Porcentaje de uso del presupuesto."""
        if self.total_budget == 0:
            return 0.0
        return (self.used_budget / self.total_budget) * 100

    def check_alert(self) -> Optional[BudgetAlertLevel]:
        """
        Verifica si se debe generar una alerta.

        Returns:
            Nivel de alerta si aplica, None en caso contrario
        """
        if not self.is_active:
            return None

        percentage = self.used_budget / self.total_budget if self.total_budget > 0 else 0

        if percentage >= 1.0:
            return BudgetAlertLevel.EXCEEDED
        elif percentage >= self.alerts.get("critical", 0.9):
            return BudgetAlertLevel.CRITICAL
        elif percentage >= self.alerts.get("warning", 0.75):
            return BudgetAlertLevel.WARNING
        elif percentage >= self.alerts.get("info", 0.5):
            return BudgetAlertLevel.INFO

        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario."""
        return {
            "budget_id": self.budget_id,
            "name": self.name,
            "total_budget": self.total_budget,
            "used_budget": self.used_budget,
            "remaining_budget": self.remaining_budget,
            "usage_percentage": self.usage_percentage,
            "period": self.period.value,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "alerts": self.alerts,
            "is_active": self.is_active,
        }


# =============================================================================
# Estadísticas
# =============================================================================


@dataclass
class UsageStatistics:
    """
    Estadísticas de uso agregadas.

    Attributes:
        period_start: Inicio del período
        period_end: Fin del período
        total_requests: Total de requests
        total_tokens: Total de tokens
        total_cost: Costo total
        by_model: Estadísticas por modelo
        by_agent: Estadísticas por agente
        by_project: Estadísticas por proyecto
        average_latency_ms: Latencia promedio
    """

    period_start: datetime
    period_end: datetime
    total_requests: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    by_model: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    by_agent: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    by_project: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    average_latency_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario."""
        return {
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "total_requests": self.total_requests,
            "total_tokens": self.total_tokens,
            "total_cost": self.total_cost,
            "by_model": self.by_model,
            "by_agent": self.by_agent,
            "by_project": self.by_project,
            "average_latency_ms": self.average_latency_ms,
        }


# =============================================================================
# Backend de Almacenamiento (Abstracto)
# =============================================================================


class CostStorageBackend(ABC):
    """
    Backend abstracto para almacenamiento de registros de costo.

    Permite diferentes implementaciones:
    - InMemoryStorage: Para desarrollo y testing
    - SQLiteStorage: Para uso local
    - PostgresStorage: Para producción
    - RedisStorage: Para caching rápido
    """

    @abstractmethod
    async def save_record(self, record: UsageRecord) -> None:
        """
        Guarda un registro de uso.

        Args:
            record: Registro a guardar
        """
        pass

    @abstractmethod
    async def get_records(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        model_id: Optional[str] = None,
        provider: Optional[str] = None,
        agent: Optional[str] = None,
        project_id: Optional[str] = None,
        limit: int = 1000,
    ) -> List[UsageRecord]:
        """
        Obtiene registros filtrados.

        Args:
            start_date: Fecha de inicio
            end_date: Fecha de fin
            model_id: Filtrar por modelo
            provider: Filtrar por proveedor
            agent: Filtrar por agente
            project_id: Filtrar por proyecto
            limit: Límite de resultados

        Returns:
            Lista de registros
        """
        pass

    @abstractmethod
    async def get_statistics(
        self,
        start_date: datetime,
        end_date: datetime,
        group_by: str = "model",
    ) -> UsageStatistics:
        """
        Obtiene estadísticas agregadas.

        Args:
            start_date: Fecha de inicio
            end_date: Fecha de fin
            group_by: Agrupar por (model, agent, project)

        Returns:
            Estadísticas del período
        """
        pass

    @abstractmethod
    async def get_total_cost(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        model_id: Optional[str] = None,
        agent: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> float:
        """
        Obtiene el costo total.

        Args:
            start_date: Fecha de inicio
            end_date: Fecha de fin
            model_id: Filtrar por modelo
            agent: Filtrar por agente
            project_id: Filtrar por proyecto

        Returns:
            Costo total en el período
        """
        pass

    @abstractmethod
    async def clear_records(
        self,
        before_date: Optional[datetime] = None,
    ) -> int:
        """
        Elimina registros.

        Args:
            before_date: Eliminar registros anteriores a esta fecha

        Returns:
            Número de registros eliminados
        """
        pass


class InMemoryStorage(CostStorageBackend):
    """
    Backend de almacenamiento en memoria.

    Útil para desarrollo y testing. No persistente.
    """

    def __init__(self, max_records: int = 10000):
        """
        Inicializa el almacenamiento en memoria.

        Args:
            max_records: Máximo número de registros a mantener
        """
        self._records: List[UsageRecord] = []
        self._max_records = max_records
        logger.info("in_memory_storage_initialized", max_records=max_records)

    async def save_record(self, record: UsageRecord) -> None:
        """Guarda un registro en memoria."""
        self._records.append(record)

        # Mantener límite de registros
        if len(self._records) > self._max_records:
            self._records = self._records[-self._max_records :]

        logger.debug(
            "record_saved",
            record_id=record.record_id,
            model_id=record.model_id,
            cost=record.cost,
        )

    async def get_records(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        model_id: Optional[str] = None,
        provider: Optional[str] = None,
        agent: Optional[str] = None,
        project_id: Optional[str] = None,
        limit: int = 1000,
    ) -> List[UsageRecord]:
        """Obtiene registros filtrados de memoria."""
        filtered = []

        for record in self._records:
            # Filtrar por fecha
            if start_date and record.timestamp < start_date:
                continue
            if end_date and record.timestamp > end_date:
                continue

            # Filtrar por modelo
            if model_id and record.model_id != model_id:
                continue

            # Filtrar por proveedor
            if provider and record.provider != provider:
                continue

            # Filtrar por agente
            if agent and record.agent != agent:
                continue

            # Filtrar por proyecto
            if project_id and record.project_id != project_id:
                continue

            filtered.append(record)

        return filtered[:limit]

    async def get_statistics(
        self,
        start_date: datetime,
        end_date: datetime,
        group_by: str = "model",
    ) -> UsageStatistics:
        """Calcula estadísticas de los registros en memoria."""
        records = await self.get_records(start_date=start_date, end_date=end_date)

        stats = UsageStatistics(
            period_start=start_date,
            period_end=end_date,
            total_requests=len(records),
        )

        total_latency = 0
        by_model: Dict[str, Dict[str, Any]] = {}
        by_agent: Dict[str, Dict[str, Any]] = {}
        by_project: Dict[str, Dict[str, Any]] = {}

        for record in records:
            # Totales
            stats.total_tokens += record.usage.total_tokens
            stats.total_cost += record.cost
            total_latency += record.latency_ms

            # Por modelo
            if record.model_id not in by_model:
                by_model[record.model_id] = {
                    "requests": 0,
                    "tokens": 0,
                    "cost": 0.0,
                }
            by_model[record.model_id]["requests"] += 1
            by_model[record.model_id]["tokens"] += record.usage.total_tokens
            by_model[record.model_id]["cost"] += record.cost

            # Por agente
            if record.agent:
                if record.agent not in by_agent:
                    by_agent[record.agent] = {
                        "requests": 0,
                        "tokens": 0,
                        "cost": 0.0,
                    }
                by_agent[record.agent]["requests"] += 1
                by_agent[record.agent]["tokens"] += record.usage.total_tokens
                by_agent[record.agent]["cost"] += record.cost

            # Por proyecto
            if record.project_id:
                if record.project_id not in by_project:
                    by_project[record.project_id] = {
                        "requests": 0,
                        "tokens": 0,
                        "cost": 0.0,
                    }
                by_project[record.project_id]["requests"] += 1
                by_project[record.project_id]["tokens"] += record.usage.total_tokens
                by_project[record.project_id]["cost"] += record.cost

        stats.by_model = by_model
        stats.by_agent = by_agent
        stats.by_project = by_project
        stats.average_latency_ms = total_latency / len(records) if records else 0.0

        return stats

    async def get_total_cost(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        model_id: Optional[str] = None,
        agent: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> float:
        """Calcula el costo total de los registros filtrados."""
        records = await self.get_records(
            start_date=start_date,
            end_date=end_date,
            model_id=model_id,
            agent=agent,
            project_id=project_id,
        )
        return sum(record.cost for record in records)

    async def clear_records(self, before_date: Optional[datetime] = None) -> int:
        """Elimina registros de memoria."""
        if before_date is None:
            count = len(self._records)
            self._records.clear()
            return count

        original_count = len(self._records)
        self._records = [r for r in self._records if r.timestamp >= before_date]
        return original_count - len(self._records)


# =============================================================================
# Tracker de Costos Principal
# =============================================================================


class CostTracker:
    """
    Sistema principal de tracking de costos.

    Coordina el registro de uso, cálculo de costos,
    gestión de presupuestos y generación de alertas.

    Ejemplo:
        tracker = CostTracker()

        # Registrar uso
        await tracker.track_usage(
            model_id="qwen3-coder-next",
            provider="ollama",
            usage=TokenUsage(prompt_tokens=100, completion_tokens=50),
            agent="backend",
        )

        # Obtener estadísticas
        stats = await tracker.get_statistics(
            start_date=datetime.utcnow() - timedelta(days=7),
            end_date=datetime.utcnow(),
        )
    """

    def __init__(
        self,
        storage: Optional[CostStorageBackend] = None,
        pricing_registry: Optional[Dict[str, ModelPricing]] = None,
        budgets: Optional[List[Budget]] = None,
    ):
        """
        Inicializa el tracker de costos.

        Args:
            storage: Backend de almacenamiento (default: InMemoryStorage)
            pricing_registry: Registro de precios por modelo
            budgets: Lista de presupuestos activos
        """
        self._storage = storage or InMemoryStorage()
        self._pricing_registry = pricing_registry or self._get_default_pricing()
        self._budgets = budgets or []
        self._alert_handlers: List[callable] = []

        logger.info(
            "cost_tracker_initialized",
            storage_type=type(self._storage).__name__,
            models_registered=len(self._pricing_registry),
            budgets=len(self._budgets),
        )

    def _get_default_pricing(self) -> Dict[str, ModelPricing]:
        """
        Obtiene los precios por defecto para los modelos del framework.

        Returns:
            Diccionario con precios por modelo
        """
        # Precios de ejemplo - ajustar según proveedor real
        return {
            # Modelos Ollama (precios estimados)
            "qwen3.5": ModelPricing(
                model_id="qwen3.5",
                provider="ollama",
                input_price_per_1k=0.0001,
                output_price_per_1k=0.0001,
            ),
            "qwen3-coder-next": ModelPricing(
                model_id="qwen3-coder-next",
                provider="ollama",
                input_price_per_1k=0.0002,
                output_price_per_1k=0.0002,
            ),
            "deepseek-v3.2": ModelPricing(
                model_id="deepseek-v3.2",
                provider="ollama",
                input_price_per_1k=0.00015,
                output_price_per_1k=0.00015,
            ),
            "gemma4:31b": ModelPricing(
                model_id="gemma4:31b",
                provider="ollama",
                input_price_per_1k=0.00012,
                output_price_per_1k=0.00012,
            ),
            "mistral-large": ModelPricing(
                model_id="mistral-large",
                provider="ollama",
                input_price_per_1k=0.00025,
                output_price_per_1k=0.00025,
            ),
            "nomic-embed-text": ModelPricing(
                model_id="nomic-embed-text",
                provider="ollama",
                input_price_per_1k=0.00001,
                output_price_per_1k=0.0,
            ),
        }

    # -------------------------------------------------------------------------
    # Gestión de Precios
    # -------------------------------------------------------------------------

    def register_pricing(self, pricing: ModelPricing) -> None:
        """
        Registra o actualiza el precio de un modelo.

        Args:
            pricing: Información de precio del modelo
        """
        self._pricing_registry[pricing.model_id] = pricing
        logger.info(
            "pricing_registered",
            model_id=pricing.model_id,
            provider=pricing.provider,
            input_price=pricing.input_price_per_1k,
            output_price=pricing.output_price_per_1k,
        )

    def get_pricing(self, model_id: str) -> Optional[ModelPricing]:
        """
        Obtiene el precio de un modelo.

        Args:
            model_id: ID del modelo

        Returns:
            Información de precio o None si no está registrado
        """
        return self._pricing_registry.get(model_id)

    def list_pricing(self) -> List[ModelPricing]:
        """
        Lista todos los precios registrados.

        Returns:
            Lista de información de precios
        """
        return list(self._pricing_registry.values())

    # -------------------------------------------------------------------------
    # Tracking de Uso
    # -------------------------------------------------------------------------

    async def track_usage(
        self,
        model_id: str,
        provider: str,
        usage: TokenUsage,
        latency_ms: int = 0,
        request_id: Optional[str] = None,
        agent: Optional[str] = None,
        project_id: Optional[str] = None,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> UsageRecord:
        """
        Registra el uso de un modelo.

        Args:
            model_id: ID del modelo usado
            provider: Proveedor del modelo
            usage: Uso de tokens
            latency_ms: Latencia en milisegundos
            request_id: ID de la request
            agent: Agente que hizo la request
            project_id: ID del proyecto
            session_id: ID de la sesión
            metadata: Metadatos adicionales

        Returns:
            Registro de uso creado
        """
        # Calcular costo
        pricing = self.get_pricing(model_id)
        cost = pricing.calculate_cost(usage) if pricing else 0.0

        # Crear registro
        record = UsageRecord(
            model_id=model_id,
            provider=provider,
            usage=usage,
            cost=cost,
            latency_ms=latency_ms,
            request_id=request_id,
            agent=agent,
            project_id=project_id,
            session_id=session_id,
            metadata=metadata or {},
        )

        # Guardar registro
        await self._storage.save_record(record)

        # Actualizar presupuestos
        await self._update_budgets(cost, agent, project_id)

        # Log
        logger.info(
            "usage_tracked",
            record_id=record.record_id,
            model_id=model_id,
            provider=provider,
            tokens=usage.total_tokens,
            cost=cost,
            agent=agent,
        )

        return record

    async def _update_budgets(
        self,
        cost: float,
        agent: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> None:
        """
        Actualiza los presupuestos después de un uso.

        Args:
            cost: Costo del uso
            agent: Agente asociado
            project_id: Proyecto asociado
        """
        for budget in self._budgets:
            if not budget.is_active:
                continue

            # Actualizar presupuesto
            budget.used_budget += cost

            # Verificar alertas
            alert_level = budget.check_alert()
            if alert_level:
                await self._handle_alert(budget, alert_level, cost, agent, project_id)

    async def _handle_alert(
        self,
        budget: Budget,
        level: BudgetAlertLevel,
        cost: float,
        agent: Optional[str],
        project_id: Optional[str],
    ) -> None:
        """
        Maneja una alerta de presupuesto.

        Args:
            budget: Presupuesto que generó la alerta
            level: Nivel de alerta
            cost: Costo que disparó la alerta
            agent: Agente asociado
            project_id: Proyecto asociado
        """
        alert_data = {
            "budget_id": budget.budget_id,
            "budget_name": budget.name,
            "level": level.value,
            "used_budget": budget.used_budget,
            "total_budget": budget.total_budget,
            "usage_percentage": budget.usage_percentage,
            "cost": cost,
            "agent": agent,
            "project_id": project_id,
            "timestamp": datetime.utcnow().isoformat(),
        }

        logger.warning(
            "budget_alert",
            **alert_data,
        )

        # Llamar handlers registrados
        for handler in self._alert_handlers:
            try:
                await handler(alert_data)
            except Exception as e:
                logger.error(
                    "alert_handler_error",
                    handler=handler.__name__,
                    error=str(e),
                )

    # -------------------------------------------------------------------------
    # Gestión de Presupuestos
    # -------------------------------------------------------------------------

    def add_budget(self, budget: Budget) -> None:
        """
        Añade un nuevo presupuesto.

        Args:
            budget: Presupuesto a añadir
        """
        self._budgets.append(budget)
        logger.info(
            "budget_added",
            budget_id=budget.budget_id,
            name=budget.name,
            total=budget.total_budget,
        )

    def remove_budget(self, budget_id: str) -> bool:
        """
        Elimina un presupuesto.

        Args:
            budget_id: ID del presupuesto a eliminar

        Returns:
            True si se eliminó, False si no existía
        """
        for i, budget in enumerate(self._budgets):
            if budget.budget_id == budget_id:
                self._budgets.pop(i)
                logger.info("budget_removed", budget_id=budget_id)
                return True
        return False

    def get_budget(self, budget_id: str) -> Optional[Budget]:
        """
        Obtiene un presupuesto por ID.

        Args:
            budget_id: ID del presupuesto

        Returns:
            Presupuesto o None si no existe
        """
        for budget in self._budgets:
            if budget.budget_id == budget_id:
                return budget
        return None

    def list_budgets(self, active_only: bool = True) -> List[Budget]:
        """
        Lista presupuestos.

        Args:
            active_only: Si solo debe listar presupuestos activos

        Returns:
            Lista de presupuestos
        """
        if active_only:
            return [b for b in self._budgets if b.is_active]
        return list(self._budgets)

    def reset_budget(self, budget_id: str) -> bool:
        """
        Resetea el uso de un presupuesto.

        Args:
            budget_id: ID del presupuesto

        Returns:
            True si se reseteó, False si no existía
        """
        budget = self.get_budget(budget_id)
        if budget:
            budget.used_budget = 0.0
            logger.info("budget_reset", budget_id=budget_id)
            return True
        return False

    # -------------------------------------------------------------------------
    # Consultas y Estadísticas
    # -------------------------------------------------------------------------

    async def get_records(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        model_id: Optional[str] = None,
        provider: Optional[str] = None,
        agent: Optional[str] = None,
        project_id: Optional[str] = None,
        limit: int = 1000,
    ) -> List[UsageRecord]:
        """
        Obtiene registros de uso.

        Args:
            start_date: Fecha de inicio
            end_date: Fecha de fin
            model_id: Filtrar por modelo
            provider: Filtrar por proveedor
            agent: Filtrar por agente
            project_id: Filtrar por proyecto
            limit: Límite de resultados

        Returns:
            Lista de registros
        """
        return await self._storage.get_records(
            start_date=start_date,
            end_date=end_date,
            model_id=model_id,
            provider=provider,
            agent=agent,
            project_id=project_id,
            limit=limit,
        )

    async def get_statistics(
        self,
        start_date: datetime,
        end_date: datetime,
        group_by: str = "model",
    ) -> UsageStatistics:
        """
        Obtiene estadísticas de uso.

        Args:
            start_date: Fecha de inicio
            end_date: Fecha de fin
            group_by: Agrupar por (model, agent, project)

        Returns:
            Estadísticas del período
        """
        return await self._storage.get_statistics(
            start_date=start_date,
            end_date=end_date,
            group_by=group_by,
        )

    async def get_total_cost(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        model_id: Optional[str] = None,
        agent: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> float:
        """
        Obtiene el costo total.

        Args:
            start_date: Fecha de inicio
            end_date: Fecha de fin
            model_id: Filtrar por modelo
            agent: Filtrar por agente
            project_id: Filtrar por proyecto

        Returns:
            Costo total en el período
        """
        return await self._storage.get_total_cost(
            start_date=start_date,
            end_date=end_date,
            model_id=model_id,
            agent=agent,
            project_id=project_id,
        )

    async def get_usage_by_model(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, TokenUsage]:
        """
        Obtiene uso agregado por modelo.

        Args:
            start_date: Fecha de inicio
            end_date: Fecha de fin

        Returns:
            Diccionario con uso por modelo
        """
        records = await self.get_records(start_date=start_date, end_date=end_date)

        usage_by_model: Dict[str, TokenUsage] = {}
        for record in records:
            if record.model_id not in usage_by_model:
                usage_by_model[record.model_id] = TokenUsage()
            usage_by_model[record.model_id] += record.usage

        return usage_by_model

    async def get_usage_by_agent(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, TokenUsage]:
        """
        Obtiene uso agregado por agente.

        Args:
            start_date: Fecha de inicio
            end_date: Fecha de fin

        Returns:
            Diccionario con uso por agente
        """
        records = await self.get_records(start_date=start_date, end_date=end_date)

        usage_by_agent: Dict[str, TokenUsage] = {}
        for record in records:
            if record.agent:
                if record.agent not in usage_by_agent:
                    usage_by_agent[record.agent] = TokenUsage()
                usage_by_agent[record.agent] += record.usage

        return usage_by_agent

    # -------------------------------------------------------------------------
    # Alertas
    # -------------------------------------------------------------------------

    def register_alert_handler(self, handler: callable) -> None:
        """
        Registra un handler para alertas de presupuesto.

        Args:
            handler: Función async que recibe los datos de la alerta
        """
        self._alert_handlers.append(handler)
        logger.info("alert_handler_registered", handler=handler.__name__)

    def unregister_alert_handler(self, handler: callable) -> bool:
        """
        Elimina un handler de alertas.

        Args:
            handler: Handler a eliminar

        Returns:
            True si se eliminó, False si no existía
        """
        try:
            self._alert_handlers.remove(handler)
            logger.info("alert_handler_unregistered", handler=handler.__name__)
            return True
        except ValueError:
            return False

    # -------------------------------------------------------------------------
    # Limpieza
    # -------------------------------------------------------------------------

    async def clear_records(self, before_date: Optional[datetime] = None) -> int:
        """
        Elimina registros antiguos.

        Args:
            before_date: Eliminar registros anteriores a esta fecha

        Returns:
            Número de registros eliminados
        """
        count = await self._storage.clear_records(before_date)
        logger.info("records_cleared", count=count, before_date=before_date)
        return count

    async def export_records(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        format: str = "json",
    ) -> str:
        """
        Exporta registros a un formato.

        Args:
            start_date: Fecha de inicio
            end_date: Fecha de fin
            format: Formato de exportación (json, csv)

        Returns:
            Datos exportados como string
        """
        import json

        records = await self.get_records(start_date=start_date, end_date=end_date)

        if format == "json":
            return json.dumps([r.to_dict() for r in records], indent=2)
        elif format == "csv":
            import csv
            from io import StringIO

            output = StringIO()
            if records:
                fieldnames = list(records[0].to_dict().keys())
                writer = csv.DictWriter(output, fieldnames=fieldnames)
                writer.writeheader()
                for record in records:
                    writer.writerow(record.to_dict())
            return output.getvalue()
        else:
            raise ValueError(f"Unsupported format: {format}")


# =============================================================================
# Factory
# =============================================================================


def create_cost_tracker(
    storage_type: str = "memory",
    pricing_config: Optional[Dict[str, Dict[str, float]]] = None,
    budget_config: Optional[List[Dict[str, Any]]] = None,
) -> CostTracker:
    """
    Factory function para crear un CostTracker.

    Args:
        storage_type: Tipo de almacenamiento (memory, sqlite, postgres)
        pricing_config: Configuración de precios
        budget_config: Configuración de presupuestos

    Returns:
        CostTracker configurado
    """
    # Crear storage backend
    if storage_type == "memory":
        storage = InMemoryStorage()
    else:
        # Por ahora solo soportamos memory
        raise ValueError(f"Unsupported storage type: {storage_type}")

    # Crear pricing registry
    pricing_registry = {}
    tracker = CostTracker(storage=storage)

    # Añadir precios personalizados
    if pricing_config:
        for model_id, config in pricing_config.items():
            pricing = ModelPricing(
                model_id=model_id,
                provider=config.get("provider", "unknown"),
                input_price_per_1k=config.get("input_price_per_1k", 0.0),
                output_price_per_1k=config.get("output_price_per_1k", 0.0),
            )
            tracker.register_pricing(pricing)

    # Añadir presupuestos
    if budget_config:
        for config in budget_config:
            budget = Budget(
                name=config.get("name", "Default Budget"),
                total_budget=config.get("total_budget", 0.0),
                period=CostGranularity(config.get("period", "monthly")),
                alerts=config.get(
                    "alerts",
                    {"info": 0.5, "warning": 0.75, "critical": 0.9},
                ),
            )
            tracker.add_budget(budget)

    return tracker


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Enums
    "CostGranularity",
    "PricingModel",
    "BudgetAlertLevel",
    # Data classes
    "TokenUsage",
    "ModelPricing",
    "UsageRecord",
    "Budget",
    "UsageStatistics",
    # Storage
    "CostStorageBackend",
    "InMemoryStorage",
    # Main class
    "CostTracker",
    # Factory
    "create_cost_tracker",
]
