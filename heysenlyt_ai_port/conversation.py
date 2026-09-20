"""대화 계약 — 포트 + 입력 DTO + 응답 DTO. 의존성 0.

**두 order web 이 함께 쓰는 유일한 계약**이다(2026-09-20 구조 개편 메모):
  · 헤이센릿 order web — `/api/chat` 그대로
  · 향연(icad) order web — 같은 `/api/chat` 에 `params.hyangyeon`(회차·턴·1차 요약)을 얹는다
  그래서 도메인별(recipe)·셸별(icad) 슬라이스와 달리 **공용 자리**에 둔다. 향연 때문에 이
  시그니처를 바꾸지 않는다는 것이 계약(대화 정책 분기는 `params` 로 간다).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import dataclasses
from typing import Any

from heysenlyt_ai_port.llm import LlmPort


@dataclass(frozen=True)
class Demographics:
    """손님 인구통계 — v1.2.0 대화가 톤·추천에 반영하던 값 (선택)."""

    gender: str = ""  # "male" | "female" | "" (미지정)
    age: int = 0  # 0 = 미지정


@dataclass(frozen=True)
class ConversationParam:
    """대화 한 턴 — v1.2.0 `POST /api/chat` ChatRequestBody 대응.

    message=None + kickoff=True 이면 대화 시작(AI 선 발화·첫 질문).
    상태(대화 기록)는 호출자(서버)가 history로 보관·회송한다 — RecipePort.prior와 같은 왕복 규약.
    """

    domain: str  # "fragrance"(향장향) | "flavor"(식향)
    message: str | None = None  # 손님 발화(userMessage). None+kickoff=첫 발화 요청
    history: tuple[tuple[str, str], ...] = ()  # ((role, content), ...) role: "user"|"assistant"
    lang: str = "ko"  # "ko"|"en"|"ja"|"vi"
    demographics: Demographics | None = None
    kickoff: bool = False  # 첫 턴 AI 선 발화
    # 식향 전용(v1.2.0 §E) — 클라가 지난 턴 자기 제출 축을 회송(통합코드는 판정 않고 에코).
    last_known_axes: dict[str, str] | None = None
    params: dict[str, Any] = field(default_factory=dict)
    # 이 호출은 **발화(텍스트)를 반드시 받아야 한다**고 호출자가 요구하는 축.
    #   왜 필요한가 — 모델이 도구만 부르고 텍스트를 빠뜨리는 턴이 있다(실측 2026-08-15:
    #   content 빈 채 tool_calls=['suggestKeywords']). 그때 호출자는 재호출로 메우려 하는데,
    #   **같은 조건으로 다시 부르면 같은 답이 온다**(실측 재호출 성공률 0/2). 조건을 바꿀
    #   손잡이가 계약에 없어서 재호출이 구조적으로 무의미했다.
    #   ⚠️ 무엇을 요구하는지만 정한다 — **어떻게 보장할지는 어댑터 소유**(도구 회수·넛지·프롬프트
    #   강화 중 무엇을 쓸지는 구현 자유). 호출자는 "텍스트가 필요하다"까지만 말한다.
    #   ⚠️ 이 호출의 산출물은 **발화뿐**이라고 봐야 한다 — 도구를 회수하는 구현이면 keywords·
    #   done·result 가 비어 돌아온다. 호출자는 직전 턴의 그 값들을 유지하고 발화만 취한다.
    require_text: bool = False
    # (2026-09-11) `require_keywords`(칩 전용 호출 축, 2026-08-16 신설)는 **삭제**됐다 — 객관식 칩이
    #   제품에서 폐기돼 받을 산출물 자체가 없다. 마지막 필드였으므로 위치인자 호환은 깨지지 않는다.


@dataclass(frozen=True)
class ConverseReply:
    """converse 출력 — v1.2.0 SSE(token·tool·done)를 한 턴 결과로 접은 형태.

    reply    : AI 발화 전체(v1.2.0 token 델타 누적분).
    keywords : ⚠️ 폐기(2026-09-11) — 객관식 칩 제거. **항상 빈 리스트.** 위치인자 4번째라 자리만 유지한다
               (지우면 위치인자 소비자가 깨진다). 호출자는 이 값을 읽지 않는다.
    done     : readiness 툴이 호출됨(취향 축 제출 완료). v1.2.0 finishReason="tool" 계열.
               ⛔ done=True 여도 대화는 계속될 수 있다(더 깊어지면 갱신 재제출) — 종료가 아니라
               "지금 만들 수 있음" 신호. 실제 확정(제조/조향)은 별도 레시피 호출.
    result   : done일 때 취향 축 페이로드.
               식향 = {scene,mood,taste,drinkTitle,reason,(recipeId),(ko*)}
               향장향 = {emotion,memory,place,fragranceName,story,(ko*)}
    history  : 이번 턴 반영한 갱신 기록 — 통째가 다음 요청의 history.
    """

    reply: str
    done: bool = False
    result: dict[str, Any] | None = None
    keywords: list[str] = field(default_factory=list)  # 폐기 — 항상 [] (위치인자 호환용 자리)
    history: list[tuple[str, str]] = field(default_factory=list)
    # 대화도 4개 독립 능력 중 하나 — 자기 버전 도장을 싣는다(어댑터가 3값 합쳐 kernel_version 제공).
    stamp: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


class ConversationPort(ABC):
    """대화 함수의 약속 — 반환 = ConverseReply.to_dict():
    {"reply": AI 발화, "keywords": 폐기(항상 []), "done": readiness 제출됨,
     "result": done일 때 취향 축 페이로드|None, "history": 갱신된 기록}.
    history 통째가 다음 요청의 history. 재진입·llm 인자 주입 불변식은 RecipePort와 동일.
    """

    @abstractmethod
    def converse(self, request: ConversationParam, llm: LlmPort | None = None) -> dict[str, Any]:
        ...
