"""sensorium-icad-0.1.0 — AI 계약. 이 세대가 제공해야 하는 것 전부가 **추상 메서드**다. 의존성 0.

어댑터는 이 클래스를 상속해 `AiContract` 구현을 만든다. 하나라도 빠지면 인스턴스를 만드는 순간(어댑터 패키지 import 시점)
`TypeError` 로 멈춘다 — 이름 규칙(`build_…`)이 아니라 타입이 "무조건 구현"을 강제한다(2026-09-27).
통합코드가 이 세대에 부르는 호출(`PORTS`)도 여기 추상 메서드에서 **파생**된다 — 손으로 적는 목록이 따로 없다.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from heysenlyt_ai_port.sensorium_icad_0_1_0.conversation import ConversationPort
from heysenlyt_ai_port.sensorium_icad_0_1_0.compose import ComposePort


class AiContract(ABC):
    """sensorium-icad-0.1.0 세대 — 통합코드가 부르는 것 전부."""

    @abstractmethod
    def conversation(self) -> ConversationPort:
        """대화 한 턴 — converse(ConversationParam) 를 구현한 어댑터 인스턴스를 돌려준다(무상태 · 통합코드가 캐시한다)."""
        ...

    @abstractmethod
    def compose(self) -> ComposePort:
        """향연 compose — compose(ComposeParam) 를 구현한 어댑터 인스턴스를 돌려준다(무상태 · 통합코드가 캐시한다)."""
        ...

    @abstractmethod
    def chat_stamp(self) -> dict[str, str]:
        """이 세대 대화 도장 {model, mode, released_at, kernel_version} — 통합코드의 향연 마지막 턴(LLM 0 · 고정 문장)이 쓴다.

        대화 어댑터를 부르지 않는 턴이라 도장을 어댑터 호출 결과에서 얻을 수 없다. 그래서 세대가 **반드시** 내준다.
        """
        ...
