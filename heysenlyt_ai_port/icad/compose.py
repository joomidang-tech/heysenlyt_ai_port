"""향연(ICAD) compose 계약 — 포트 + 입력 DTO 3종 + 응답 DTO. 의존성 0.

**향연 order web 의 계약 전부가 이 한 파일**이다(2026-09-20 구조 개편 메모). 종전엔
  `ports/icad_port.py` + `dto/params.py` 의 향연 절 + `dto/replies.py` 셋에 흩어져 있었고,
  params.py 는 헤이센릿 DTO 와 한 파일을 나눠 써서 **두 order web 의 계약이 섞여** 있었다.

정본: developer/hey_senlyt/v1.4.0/90_workorders/2026-09-15_to-ai-dev_ICAD-포트-사양서.md §3.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import dataclasses
from typing import Any

from heysenlyt_ai_port.shared.llm import LlmPort
from heysenlyt_ai_port.shared.palette import Palette


@dataclass(frozen=True)
class IcadTurn:
    """대화 한 턴 — `role` 은 "user" | "assistant" 만(서버 Body 가 400 경계를 강제한다)."""

    role: str
    content: str


@dataclass(frozen=True)
class IcadPrior:
    """2차(활동 4)에만 실리는 **1차 결과 요약** — 사용 여부는 어댑터 판단.

    ⛔ 배합 양(amountMl·percent·totalVolumeMl)은 **절대 싣지 않는다**(사양서 §2-3 · I-D23).
       converse 응답은 손님 SSE 로 그대로 내려가는데 그 경로엔 배합 allowlist 가 없어, 양이
       프롬프트에 들어가면 AI 한 마디로 샌다. 향료명(note_names)까지만이 계약이다.
       서버는 양 키가 들어오면 400 이 아니라 **버리고 경고**한다.
    """

    name: str
    emotion_group: str
    note_names: tuple[str, ...] = ()


@dataclass(frozen=True)
class IcadComposeParam:
    """향연 compose 한 번 — **대화 이력 전체**가 입력이다(사양서 §3-1 · 서버 IcadComposeBody 와 1:1).

    ⛔ `RecipeParam` 과 **별개 DTO** 다(사양서 §3-3). 입력이 `prompt`(한 문장) 가 아니라
       `history`(이력 전문)라 개념이 다르고, 식향엔 이 동작이 없어야 한다 — 현행 `regenerate` 가
       fragrance 에만 있는 것과 같은 자세. `RecipeParam` 에 nullable history 를 얹으면
       "무엇이 지배하나(prompt 냐 history 냐)"가 타입에서 사라진다.

    history : 이번 회차 대화 전문(≤100턴 · 상한은 서버가 강제) — 관호 확정 입력.
    round   : 1 | 2. 서버가 access_codes 로 **재확정한 값**(클라 주장값 아님).
    prior   : 2차에만. 양 없음(IcadPrior 참조).
    lang    : 1차 파일럿 "ko" 고정(서버가 그 경계를 잡는다 — 여기선 타입만).
    params  : 어댑터 확장 슬롯(현행 RecipeParam.params 와 같은 의미 · 허용목록은 어댑터 소유).
    선언 3필드(sensorium_version·ai_models·ai_model)는 서버 층(ModelSelection)에서 소비되고
    LLM 핀으로 적용되므로 이 DTO 엔 실리지 않는다 — 현행 RecipeParam 과 같은 배선.
    """

    history: tuple[IcadTurn, ...]
    round: int = 1
    prior: IcadPrior | None = None
    lang: str = "ko"
    params: dict[str, Any] = field(default_factory=dict)
    # (2026-09-20) 이번 요청에서 **쓸 수 있는 향료** — 그 기기에 실제로 꽂혀 있는 것. None = 제한 없음(현행).
    #   계약·어휘·실패 규약 정본 = `palette.py`. ⚠️ 신규 필드라 **끝에** 둔다(위치인자 소비자 호환).
    palette: Palette | None = None


@dataclass(frozen=True)
class IcadComposeReply:
    """향연 compose 출력 — **봉투 + 관호 dict 그대로**(사양서 §3-2).

    payload         : `to_product_payload()` 그대로. web 이 읽는 키(name·description·recipe·
                      emotion·grounding·regulatory·fragrance_load_pct·is_valid·errors·warnings ·
                      확장 result_keywords·composer_note·direction)만 읽고 나머지는 보존한다.
                      핵심 내용물(recipe·emotion·grounding·regulatory)의 내부 형상은 **불투명** —
                      포트는 단정하지 않는다(관호 회신이 포트 형상을 바꾸지 않게).
                      단 **`recipe` 만은 현행 향장향 `RecipeReply.recipe` 와 같은 FragranceResult 형상**
                      이어야 한다 — `notes[]{name, nameKo, amountMl(**mL**), percent, type: top|middle|base}`
                      + `totalVolumeMl`(mL). web 변환기·pi 조립이 이 형식만 읽는다(향연 조향 = 현행 향장향
                      엔진 · 2026-09-18 확정 · 포트 사양서 §4-1 a~c 종결). 단위를 바꾸면 1000배 오토출이다.
    stamp           : 현행 RecipeReply.stamp 와 같은 형상 {model, mode, released_at, kernel_version}.
    llm_models_used : tier→model. **모르면 None = to_dict() 에서 키 생략**(현행 규약 — 거짓값 금지).
                      서버가 실측(요청 렌즈)으로 채우거나 어댑터가 직접 기록한다(사양서 §4-5).

    ⚠️ 와이어 키는 snake_case(`llm_models_used`) — web 미러 IcadContracts.ts 와 1:1.
       (현행 recipe/converse 의 서버 추가 필드 `llmModelsUsed` 와 표기가 다르다 — 그쪽은 서버가
        응답 dict 에 덧붙이는 camelCase 필드이고, 이쪽은 **계약 DTO 의 필드**다.)
    """

    payload: dict[str, Any]
    stamp: dict[str, str]
    llm_models_used: dict[str, str] | None = None

    def to_dict(self) -> dict[str, Any]:
        d = dataclasses.asdict(self)
        if d.get("llm_models_used") is None:
            d.pop("llm_models_used", None)  # 모르면 싣지 않는다(옵셔널 키)
        return d


class IcadComposePort(ABC):
    """향연 compose 의 약속 — 연구소(관호)가 상속해 `IcadComposeAdapter` 를 만든다."""

    @abstractmethod
    def compose(
        self, param: IcadComposeParam, llm: LlmPort | None = None
    ) -> IcadComposeReply:
        """대화 이력 → 제품 payload 하나. 내부 엔진·라벨링·규제 호출 횟수·순서는 어댑터 소관."""
        ...
