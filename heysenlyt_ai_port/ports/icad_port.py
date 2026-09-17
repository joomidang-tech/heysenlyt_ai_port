"""IcadComposePort — 향연(ICAD) "대화 이력 → 제품 payload 하나"의 약속. 의존성 0.

정본: developer/hey_senlyt/v1.4.0/90_workorders/2026-09-15_to-ai-dev_ICAD-포트-사양서.md §3-3.

`RecipePort` 를 **상속하지 않는다** — 입력이 `prompt` 가 아니라 `history` 라 개념이 다르고,
식향엔 이 메서드가 없어야 한다(현행 `regenerate` 가 fragrance 에만 있는 것과 같은 자세).
`ConversationPort` 시그니처 변경도 0 이다(대화 정책 분기는 `params.hyangyeon` 로 간다).

불변식은 RecipePort 와 동일:
  1. 재진입 — compose() 는 self 상태를 바꾸지 않는다(같은 인스턴스 동시 호출 안전).
  2. 부작용은 인자로 — 밖으로 나가는 호출(LLM)은 `llm` 인자를 통해서만.
     ⚠️ 사양서 §3-3 의 시그니처엔 `llm` 이 없지만, 현행 두 포트(RecipePort·ConversationPort)와
        서버 정책층(요청 단위 모델 핀·failover 는 **포트를 마지막 위치 인자로 갈아 끼운다**)이
        이 자리를 전제하므로 같은 자리에 둔다. 어댑터는 `llm=None` 이면 거부해도 된다.
  3. 같은 입력 + 같은 llm 응답 → 같은 반환.

반환은 `IcadComposeReply`(DTO) — 어댑터가 `IcadComposeReply(payload=to_product_payload(),
stamp=…, llm_models_used=…)` 를 **직접** 만들어 돌려준다(사양서 §2-1 🟧①). 서버가 `.to_dict()`
로 봉투를 편다. `payload.is_valid:false` 는 예외가 아니라 정상 반환(서버가 200 으로 내보낸다).
실패 신호(LlmError 계열)는 현행 RecipePort 와 동일하게 raise 한다.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from heysenlyt_ai_port.dto.params import IcadComposeParam
from heysenlyt_ai_port.dto.replies import IcadComposeReply
from heysenlyt_ai_port.ports.recipe_port import LlmPort


class IcadComposePort(ABC):
    """향연 compose 의 약속 — 연구소(관호)가 상속해 `IcadComposeAdapter` 를 만든다."""

    @abstractmethod
    def compose(
        self, param: IcadComposeParam, llm: LlmPort | None = None
    ) -> IcadComposeReply:
        """대화 이력 → 제품 payload 하나. 내부 엔진·라벨링·규제 호출 횟수·순서는 어댑터 소관."""
        ...
