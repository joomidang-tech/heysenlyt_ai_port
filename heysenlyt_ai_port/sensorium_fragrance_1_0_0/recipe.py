"""sensorium-fragrance-1.0.0 — 레시피 계약. 의존성 0.

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
class RecipeParam:
    """한 번의 레시피 요청. 불변(frozen) — 요청 객체 재사용이 안전하다.

    prompt : 자연어 요청(백지 생성). 손님 피드백은 여기가 아니라 RegenerateParam.feedback.
             조향=한 문장(예 "제주 서귀포 해수욕장의 향"), 식향=취향 축 요약(scene/mood/taste).
    mode   : 도메인 내 방식. 조향 "rule"(v1.2.0 기본) / 식향 "generative"(expo, v1.2.0 기본).
             None이면 도메인 기본값.
    lang   : 결과 텍스트 언어 ("ko"|"en"|"ja"|"vi"). 비-ko는 ko 병기(직원 주문 읽기 P0).
    params : 방식 파라미터 오버라이드. 조향 {complexity, ratio} / 식향 {} / 공통 {temperature}.
             어댑터 허용목록 밖 키는 거부된다(비용·통제 이탈 차단).

    ⛔ prior 필드는 없다 — 재조향은 이 DTO 가 아니라 **RegenerateParam** 이다(계약상 별개 동작).
       nullable prior 로 두 동작을 한 타입에 얹으면 "무엇이 지배하나"가 타입에서 사라진다.
    """

    prompt: str
    mode: str | None = None
    lang: str = "ko"
    params: dict[str, Any] = field(default_factory=dict)
    # (2026-09-20) 이번 요청에서 **쓸 수 있는 향료** — 그 기기에 실제로 꽂혀 있는 것. None = 제한 없음(현행).
    #   계약·어휘·실패 규약 정본 = 이 파일 `Palette` 절. ⚠️ 신규 필드라 **끝에** 둔다(위치인자 소비자 호환).
    palette: Palette | None = None


@dataclass(frozen=True)
class RegenerateParam:
    """재조향 한 번 — 손님이 결과를 맡아보고 "이렇게 바꿔줘"를 넣은 상황.

    generate 와 **별개 동작**이라 별개 DTO 로 둔다. 두 동작의 차이는 prior 유무가 아니라
    **무엇이 결과를 지배하느냐**다:

      generate    : prompt 가 지배. 백지에서 만든다.
      regenerate  : feedback 이 지배. prior 는 "직전엔 이랬다"는 **참고 맥락일 뿐 픽스가 아니다**
                    — 결과가 prior 와 크게 달라지는 것이 정상이고, 그래야 맞다.

    이 구분이 기획 결정(2026-08-14 D1 "B 방식")이다. 미세조정(A′ — prior 를 base 로 깔고
    비율만 만지는 쪽)은 **기각됐다.** 어댑터가 그 둘을 헷갈리지 않도록 계약 표면에서 갈라 둔다.

    feedback : 손님이 적은 수정 방향. 예 "덜 우디하게" / "잔향을 더 진하게" (≤300자, 화면 규칙)
    prior    : 직전 generate/regenerate 가 돌려준 dict 그대로. 참고 맥락.
               ⛔ 상태는 어댑터가 아니라 호출자(서버)가 보관한다 — 재진입 안전의 전제.
    mode/lang/params : RecipeParam 과 같은 의미.
    """

    feedback: str
    prior: dict[str, Any]
    mode: str | None = None
    lang: str = "ko"
    params: dict[str, Any] = field(default_factory=dict)
    # (2026-09-20) 이번 요청에서 **쓸 수 있는 향료** — 그 기기에 실제로 꽂혀 있는 것. None = 제한 없음(현행).
    #   계약·어휘·실패 규약 정본 = 이 파일 `Palette` 절. ⚠️ 신규 필드라 **끝에** 둔다(위치인자 소비자 호환).
    palette: Palette | None = None


@dataclass(frozen=True)
class RecipeReply:
    """generate 출력. to_dict() 통째가 다음 요청의 prior.

    stamp  : 도장 세트 {model, mode, released_at, kernel_version} — kernel_version 은
             `{model}+{mode}+{released_at}` 단일 문자열(v1.2.0 stampVersion 동일 형식).
    recipe : 도메인 레시피 페이로드.
             조향 = {buckets, weights, items, moves}(rule 엔진 산출)
             식향 = ExpoRecipePayload(drinkTitle·reason·families·sweetMl·sourMl·items·baseMl…)
    """

    domain: str  # "fragrance" | "flavor"
    version: str  # "1.0.0"
    stamp: dict[str, str]  # model·mode·released_at·kernel_version
    recipe: dict[str, Any]  # 도메인 레시피 페이로드
    is_valid: bool = True
    warnings: list[str] = field(default_factory=list)
    result_type: str = ""  # "module:Class" — refine prior 복원 힌트
    state: dict[str, Any] = field(default_factory=dict)  # refine 전제 상태(호출자 보관)

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


class RecipePort(VersionPort):
    """레시피를 만드는 함수 — 연구소(관호)가 이 클래스를 상속해 어댑터를 만든다.

    계약 불변식 (구현이 반드시 지킬 것):
      1. 재진입: generate()는 self의 어떤 상태도 바꾸지 않는다. 같은 인스턴스로
         여러 번·동시에 불러도 호출끼리 간섭하지 않는다.
      2. 부작용은 인자로: 밖으로 나가는 호출(LLM)은 llm 인자를 통해서만.
         llm=None이면 구현 기본 클라이언트를 쓴다 (현행 프로덕션 동작).
      3. 같은 입력 + 같은 llm 응답 → 같은 반환 dict.

    반환 dict = RecipeReply.to_dict() (JSON-safe). 통째로 RegenerateParam.prior 로 넣으면 재조향.
    """

    @abstractmethod
    def generate(self, request: RecipeParam, llm: LlmPort | None = None) -> dict[str, Any]:
        """레시피 생성 — prompt 가 지배한다. 위 불변식 참조.

        재조향(손님 피드백 반영)은 이 메서드가 아니라 regenerate() 다.
        """
        ...

    @abstractmethod
    def regenerate(
        self, request: RegenerateParam, llm: LlmPort | None = None
    ) -> dict[str, Any]:
        """재조향 — **feedback 이 지배**하는 신규 레시피. prior 는 참고 맥락(픽스 아님).

        generate 와 갈라 둔 이유: 두 동작은 "지배하는 입력"이 다르다. 한 메서드에 nullable
        prior 로 얹으면 그 차이가 타입에서 사라지고, 어댑터마다 "prior 를 얼마나 존중하나"가
        갈린다. 기획 결정(B 방식)은 **크게 달라지는 것이 정상**이다 — 그걸 계약에 박아 둔다.

        구현은 생성 경로를 generate 와 공유해도 된다(프롬프트를 무엇으로 만드느냐만 다르다).
        계약이 요구하는 건 **두 동작이 호출자에게 구분되어 보이는 것**이지 코드 분리가 아니다.

        불변식은 generate 와 동일(재진입·부작용은 인자로·같은 입력이면 같은 반환).
        """
        ...
