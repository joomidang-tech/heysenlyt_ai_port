"""sensorium-shop-0.1.0 — AI 계약. 이 세대가 제공해야 하는 것 전부가 **추상 메서드**다. 의존성 0.

어댑터는 이 클래스를 상속해 구현을 만든다. 하나라도 빠지면 인스턴스를 만드는 순간 `TypeError`.
통합코드가 이 세대에 부르는 호출(`PORTS`)은 이 추상 메서드에서 파생된다.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from heysenlyt_ai_port.sensorium_shop_0_1_0.conversation import ConversationPort
from heysenlyt_ai_port.sensorium_shop_0_1_0.recipe import RecipePort


class AiContract(ABC):
    """sensorium-shop-0.1.0 세대(센릿샵) — 통합코드가 부르는 것 전부."""

    @abstractmethod
    def recipe(self) -> RecipePort:
        """레시피 한 번 — generate(RecipeParam) 를 구현한 어댑터 인스턴스(무상태 · 통합코드가 캐시)."""
        ...

    @abstractmethod
    def conversation(self) -> ConversationPort:
        """대화 한 턴 — converse(ConversationParam) 를 구현한 어댑터 인스턴스(무상태 · 통합코드가 캐시)."""
        ...
