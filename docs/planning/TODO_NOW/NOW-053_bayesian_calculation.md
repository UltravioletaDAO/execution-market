# NOW-053: Implementar Bayesian Average calculation

## Metadata
- **Prioridad**: P0
- **Fase**: 4 - ERC-8004 Reputation
- **Dependencias**: NOW-008
- **Archivos a crear**: `mcp_server/reputation/bayesian.py`
- **Tiempo estimado**: 2-3 horas

## Descripción
Implementar el cálculo de Bayesian Average para el sistema de reputación, que combina ratings con pesos por valor de tarea y decay temporal.

## Contexto Técnico
- **Fórmula**: `Score = (C × m + Σ(ratings × weight)) / (C + Σ weights)`
- **Parámetros**:
  - C = 15-20 (confidence parameter)
  - m = 50 (prior mean - neutral starting point)
  - weight = log(task_value + 1) (higher value tasks count more)
  - decay = 0.9^months_old (older ratings decay)

## Fórmula Detallada

```
Bayesian Score = (C × m + Σᵢ(ratingᵢ × weightᵢ × decayᵢ)) / (C + Σᵢ(weightᵢ × decayᵢ))

Donde:
- C = 15 (confidence parameter, ajustable)
- m = 50 (prior mean, punto neutral)
- ratingᵢ = score del rating i (1-100)
- weightᵢ = ln(task_value_usd + 1)
- decayᵢ = 0.9^(months_since_rating)
```

## Código de Referencia

### bayesian.py
```python
"""
Bayesian Average Reputation System for Execution Market
"""
import math
from datetime import datetime, UTC
from decimal import Decimal
from typing import List, Optional
from dataclasses import dataclass


@dataclass
class Rating:
    """Individual rating record"""
    score: int  # 1-100
    task_value_usdc: float
    created_at: datetime
    task_type: Optional[str] = None


@dataclass
class BayesianConfig:
    """Configuration for Bayesian calculation"""
    C: float = 15.0  # Confidence parameter
    m: float = 50.0  # Prior mean
    decay_rate: float = 0.9  # Monthly decay rate
    min_score: float = 1.0
    max_score: float = 100.0


class BayesianCalculator:
    """
    Calculates Bayesian Average reputation scores.

    The Bayesian Average prevents gaming by:
    1. Pulling new users toward the mean (C parameter)
    2. Weighting high-value tasks more heavily
    3. Decaying old ratings over time
    """

    def __init__(self, config: Optional[BayesianConfig] = None):
        self.config = config or BayesianConfig()

    def calculate_weight(self, task_value_usdc: float) -> float:
        """
        Calculate weight for a rating based on task value.

        Higher value tasks count more because:
        - More at stake = more careful selection
        - Spam prevention (can't game with $0.01 tasks)

        Uses log to prevent extreme outliers from dominating.
        """
        return math.log(task_value_usdc + 1)

    def calculate_decay(self, rating_date: datetime) -> float:
        """
        Calculate time decay for a rating.

        Older ratings matter less because:
        - Worker quality can change over time
        - Recency is valuable signal
        - Prevents ancient history from dominating

        Decay formula: 0.9^months_old
        - 1 month old: 0.9 weight
        - 6 months old: 0.53 weight
        - 12 months old: 0.28 weight
        """
        now = datetime.now(UTC)
        if rating_date.tzinfo is None:
            rating_date = rating_date.replace(tzinfo=UTC)

        months_old = (now - rating_date).days / 30.0
        return self.config.decay_rate ** months_old

    def calculate_score(self, ratings: List[Rating]) -> float:
        """
        Calculate Bayesian Average score from a list of ratings.

        Formula:
        Score = (C × m + Σ(rating × weight × decay)) / (C + Σ(weight × decay))

        Returns:
            float: Score between 1 and 100, defaulting to m (50) if no ratings
        """
        if not ratings:
            return self.config.m  # Return prior mean if no ratings

        weighted_sum = 0.0
        weight_total = 0.0

        for rating in ratings:
            # Calculate individual weight and decay
            weight = self.calculate_weight(rating.task_value_usdc)
            decay = self.calculate_decay(rating.created_at)

            # Apply to weighted sum
            effective_weight = weight * decay
            weighted_sum += rating.score * effective_weight
            weight_total += effective_weight

        # Bayesian average formula
        numerator = (self.config.C * self.config.m) + weighted_sum
        denominator = self.config.C + weight_total

        score = numerator / denominator

        # Clamp to valid range
        return max(self.config.min_score, min(self.config.max_score, score))

    def calculate_with_details(self, ratings: List[Rating]) -> dict:
        """
        Calculate score with detailed breakdown for transparency.

        Returns dict with:
        - score: final Bayesian score
        - raw_average: simple average (for comparison)
        - total_ratings: count of ratings
        - effective_ratings: sum of weighted ratings
        - confidence: how confident we are (based on weight_total)
        """
        if not ratings:
            return {
                "score": self.config.m,
                "raw_average": None,
                "total_ratings": 0,
                "effective_ratings": 0,
                "confidence": 0,
                "weights": []
            }

        weighted_sum = 0.0
        weight_total = 0.0
        raw_sum = 0
        weight_details = []

        for rating in ratings:
            weight = self.calculate_weight(rating.task_value_usdc)
            decay = self.calculate_decay(rating.created_at)
            effective_weight = weight * decay

            weighted_sum += rating.score * effective_weight
            weight_total += effective_weight
            raw_sum += rating.score

            weight_details.append({
                "score": rating.score,
                "task_value": rating.task_value_usdc,
                "weight": round(weight, 3),
                "decay": round(decay, 3),
                "effective_weight": round(effective_weight, 3)
            })

        score = (self.config.C * self.config.m + weighted_sum) / (self.config.C + weight_total)

        return {
            "score": round(score, 2),
            "raw_average": round(raw_sum / len(ratings), 2),
            "total_ratings": len(ratings),
            "effective_ratings": round(weight_total, 2),
            "confidence": round(weight_total / (self.config.C + weight_total) * 100, 1),
            "weights": weight_details,
            "config": {
                "C": self.config.C,
                "m": self.config.m,
                "decay_rate": self.config.decay_rate
            }
        }


# Convenience function for simple use
def calculate_bayesian_score(
    ratings: List[dict],
    C: float = 15.0,
    m: float = 50.0,
    decay_rate: float = 0.9
) -> float:
    """
    Convenience function to calculate Bayesian score from raw rating dicts.

    Args:
        ratings: List of dicts with 'score', 'task_value_usdc', 'created_at'
        C: Confidence parameter (default 15)
        m: Prior mean (default 50)
        decay_rate: Monthly decay rate (default 0.9)

    Returns:
        Bayesian average score (1-100)
    """
    config = BayesianConfig(C=C, m=m, decay_rate=decay_rate)
    calculator = BayesianCalculator(config)

    rating_objects = [
        Rating(
            score=r["score"],
            task_value_usdc=r.get("task_value_usdc", 1.0),
            created_at=r["created_at"] if isinstance(r["created_at"], datetime)
                       else datetime.fromisoformat(r["created_at"].replace("Z", "+00:00"))
        )
        for r in ratings
    ]

    return calculator.calculate_score(rating_objects)
```

### Tests
```python
# tests/test_bayesian.py
import pytest
from datetime import datetime, timedelta, UTC
from reputation.bayesian import BayesianCalculator, Rating, BayesianConfig


def test_no_ratings_returns_prior():
    calc = BayesianCalculator()
    assert calc.calculate_score([]) == 50.0


def test_single_high_rating():
    calc = BayesianCalculator()
    rating = Rating(score=100, task_value_usdc=10.0, created_at=datetime.now(UTC))
    # With C=15 and m=50, single rating shouldn't swing score too much
    score = calc.calculate_score([rating])
    assert 50 < score < 80  # Pulled toward mean


def test_many_high_ratings():
    calc = BayesianCalculator()
    ratings = [
        Rating(score=90, task_value_usdc=50.0, created_at=datetime.now(UTC))
        for _ in range(20)
    ]
    score = calc.calculate_score(ratings)
    assert score > 80  # Many ratings overcome prior


def test_old_ratings_decay():
    calc = BayesianCalculator()
    old_rating = Rating(
        score=100,
        task_value_usdc=10.0,
        created_at=datetime.now(UTC) - timedelta(days=365)
    )
    new_rating = Rating(
        score=50,
        task_value_usdc=10.0,
        created_at=datetime.now(UTC)
    )
    # New rating should matter more
    score = calc.calculate_score([old_rating, new_rating])
    assert score < 75  # Closer to new rating


def test_high_value_tasks_weight_more():
    calc = BayesianCalculator()
    low_value = Rating(score=100, task_value_usdc=1.0, created_at=datetime.now(UTC))
    high_value = Rating(score=50, task_value_usdc=100.0, created_at=datetime.now(UTC))
    # High value task should dominate
    score = calc.calculate_score([low_value, high_value])
    assert score < 75  # Pulled toward high-value rating


def test_weight_calculation():
    calc = BayesianCalculator()
    assert calc.calculate_weight(0) == 0  # ln(1) = 0
    assert calc.calculate_weight(1.0) > 0
    assert calc.calculate_weight(100.0) > calc.calculate_weight(10.0)
```

## Criterios de Éxito
- [ ] Fórmula implementada correctamente
- [ ] Tests pasan
- [ ] Score en rango 1-100
- [ ] Decay funciona (ratings viejos valen menos)
- [ ] Weights funcionan (tareas caras valen más)
- [ ] Prior mean (50) para nuevos workers
- [ ] calculate_with_details muestra breakdown

## Uso en MCP Server
```python
# En get_my_tasks o profile endpoint
from reputation.bayesian import calculate_bayesian_score

# Fetch ratings from DB
ratings = supabase.table("ratings").select("*").eq("ratee_id", executor_id).execute()

# Calculate score
score = calculate_bayesian_score(ratings.data)

# Return in response
return {"reputation_score": score}
```

## Integración con PostgreSQL RPC
Ya existe la función RPC `calculate_bayesian_score` en NOW-009. Este módulo Python es para:
1. Uso directo en el MCP server
2. Testing y validación
3. Cálculos más complejos (breakdown, what-if)
