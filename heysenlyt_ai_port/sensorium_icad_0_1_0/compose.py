"""sensorium-icad-0.1.0 — 향연 compose 계약. 의존성 0.

⛔ 이 파일은 **이 세대만의 계약**이다(2026-09-27 세대 축 개편). 다른 세대와 내용이 같아 보여도 공유하지 않는다 —
   세대가 갈릴 때 옛 세대 계약을 건드리지 않기 위해 처음부터 세대 폴더 안에 둔다. 세대끼리 import 금지(tests/test_shape.py).
   세대 무관 계약(LlmPort · 실패 어휘 · VersionPort)만 패키지 최상위에 있다.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import dataclasses
from typing import Any

from heysenlyt_ai_port.llm import LlmPort
from heysenlyt_ai_port.version import VersionPort  # get_version() 도 추상 메서드 — 무조건 구현(2026-09-27)


# ## Palette — 이번 요청에서 **쓸 수 있는 향료** (2026-09-20 신설 · 2026-09-27 세대 폴더 안으로)
# 
# ## 왜 필요한가 — 엔진은 기기를 모른 채 고른다
# 센소리움(레시피) 모델은 **향료 → 하드웨어 → 산식**이 한 덩어리다. 그런데 계약에는 그 첫 칸(향료)을
#   넘길 자리가 없었다. 엔진은 자기 안의 카탈로그(향장향 27종 · 식향 16종) 전체에서 고르고, **그 기기에
#   실제로 무엇이 꽂혀 있는지는 모른다.** 운영자가 관제에서 포트 매핑을 바꿔도 엔진 출력은 그대로다.
# 
# 결과는 늦게 드러난다 — 엔진이 안 꽂힌 향료를 고르면:
#   · 향장향 : 주문 접수에서 409 `fragrance_note_unmapped` 로 거절된다(손님은 결과 화면까지 본 뒤다).
#   · 식향   : 접수 검사조차 없어 **조립까지 내려가서** 터진다(`unmapped liquid`). 손님은 대기 화면에 남는다.
#   게다가 향장향은 지금 **정확히 만석**이다(3펌프 × 9칸 = 27칸 · 카탈로그 27종). 28번째 향료를 더하는
#   순간 그 향료는 영구 미매핑이 되고, 엔진이 그걸 고른 주문은 전부 위 길로 떨어진다.
# 
# ⇒ web 이 "지금 이 기기에 꽂힌 향료"를 실어 보내고, 엔진이 **그 안에서만** 고른다.
#   그러면 향료 라인업을 바꾸는 일이 **운영자의 포트 매핑 편집 하나**로 끝난다(엔진 재배포 0).
# 
# ## 어휘 — 엔진 카탈로그 키 그대로
# `notes` 의 문자열은 **엔진 카탈로그의 키**다. 두 트랙 모두 web 이 같은 키의 미러를 이미 들고 있다:
#   · 향장향 : `domain/fragrance/recipe.py` `NOTE_META` 키(예 "Bitter Lemon") ↔ web `NoteMetadata.ts` `NOTE_META`
#   · 식향   : `domain/flavor/recipe.py` 팔레트 16종 키                        ↔ web `shared/expo/palette.ts`
#   새 어휘를 만들지 않는다 — 번역 층이 하나 늘면 그 층이 곧 드리프트 지점이다.
# 
# ## 계약
#   · `palette=None`(기본)  → **제한 없음.** 오늘과 1비트도 다르지 않다(하위호환 · 구 web·구 어댑터 그대로 동작).
#   · `palette.notes` 있음  → 어댑터는 **그 목록 안에서만** 고른다. 목록 밖 향료를 결과에 내지 않는다.
#   · 목록에 **카탈로그에 없는 키**가 섞여 오면 → 어댑터는 그 키를 **무시한다**(거부하지 않는다).
#         web 과 엔진의 카탈로그가 잠깐 어긋난 배포 창에서 주문이 통째로 죽지 않게 하려는 것이다.
#   · 걸러 내고 **남은 것이 너무 적어 만들 수 없으면** → 어댑터는 `is_valid: false` + `warnings` 로 돌려준다.
#         "몇 종이면 만들 수 있나"는 **산식의 문제라 어댑터가 정한다**(향장향 8향 선정 · 식향 역할별 최소 등).
#         예외로 던지지 않는다 — 실패가 아니라 "이 구성으로는 못 만든다"는 정상 답이다.
#   · 빈 목록(`notes=()`)은 **서버가 어댑터를 부르기 전에 422 로 끊는다** — 만들 재료가 0 이면 갈 이유가 없다.
# 
# ## 어댑터가 정할 것 (계약이 단정하지 않는 것)
#   · 목록을 **어떻게** 지키나 — 프롬프트에 주입하나 · 선정 뒤 거르나 · 둘 다 하나.
#   · 목록이 작을 때 품질을 어떻게 지키나(8향을 못 채우면 줄이나 · 대체하나).
#   · 재조향(`regenerate`)에서 prior 의 향료가 지금 목록에 없으면 어떻게 다루나.
#   계약이 요구하는 건 **결과에 목록 밖 향료가 없다**는 것 하나다.

@dataclass(frozen=True)
class Palette:
    """이번 요청에서 쓸 수 있는 향료 목록 — 그 기기에 실제로 꽂혀 있는 것.

    notes : 엔진 카탈로그 키의 튜플(순서 무의미 · 중복 없음). 헤더 「어휘」 참조.
            ⛔ 양(mL)·포트 번호·펌프 주소는 **싣지 않는다** — 엔진은 "무엇을 쓸 수 있나"만 알면 된다.
               "어디에 꽂혔나"는 조립(web `wire`·pi)의 일이고, 그게 엔진에 닿으면 하드웨어 배치가
               산식에 새어 들어간다.
    """

    notes: tuple[str, ...]


@dataclass(frozen=True)
class ComposeTurn:
    """대화 한 턴 — `role` 은 "user" | "assistant" 만(서버 Body 가 400 경계를 강제한다)."""

    role: str
    content: str


@dataclass(frozen=True)
class ComposePrior:
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
class ComposeParam:
    """향연 compose 한 번 — **대화 이력 전체**가 입력이다(사양서 §3-1 · 서버 IcadComposeBody 와 1:1).

    ⛔ `RecipeParam` 과 **별개 DTO** 다(사양서 §3-3). 입력이 `prompt`(한 문장) 가 아니라
       `history`(이력 전문)라 개념이 다르고, 식향엔 이 동작이 없어야 한다 — 현행 `regenerate` 가
       fragrance 에만 있는 것과 같은 자세. `RecipeParam` 에 nullable history 를 얹으면
       "무엇이 지배하나(prompt 냐 history 냐)"가 타입에서 사라진다.

    history : 이번 회차 대화 전문(≤100턴 · 상한은 서버가 강제) — 관호 확정 입력.
    round   : 1 | 2. 서버가 access_codes 로 **재확정한 값**(클라 주장값 아님).
    prior   : 2차에만. 양 없음(ComposePrior 참조).
    lang    : 1차 파일럿 "ko" 고정(서버가 그 경계를 잡는다 — 여기선 타입만).
    params  : 어댑터 확장 슬롯(현행 RecipeParam.params 와 같은 의미 · 허용목록은 어댑터 소유).
    선언 3필드(sensorium_version·ai_models·ai_model)는 서버 층(ModelSelection)에서 소비되고
    LLM 핀으로 적용되므로 이 DTO 엔 실리지 않는다 — 현행 RecipeParam 과 같은 배선.
    """

    history: tuple[ComposeTurn, ...]
    round: int = 1
    prior: ComposePrior | None = None
    lang: str = "ko"
    params: dict[str, Any] = field(default_factory=dict)
    # (2026-09-20) 이번 요청에서 **쓸 수 있는 향료** — 그 기기에 실제로 꽂혀 있는 것. None = 제한 없음(현행).
    #   계약·어휘·실패 규약 정본 = 이 파일 `Palette` 절. ⚠️ 신규 필드라 **끝에** 둔다(위치인자 소비자 호환).
    palette: Palette | None = None


@dataclass(frozen=True)
class ComposeReply:
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


class ComposePort(VersionPort):
    """향연 compose 의 약속 — 연구소(관호)가 상속해 이 세대의 compose 어댑터를 만든다."""

    @abstractmethod
    def compose(
        self, param: ComposeParam, llm: LlmPort | None = None
    ) -> ComposeReply:
        """대화 이력 → 제품 payload 하나. 내부 엔진·라벨링·규제 호출 횟수·순서는 어댑터 소관."""
        ...
