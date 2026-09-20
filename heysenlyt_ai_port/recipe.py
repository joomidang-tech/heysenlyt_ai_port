"""조향/식향 레시피 계약 — 포트 + 입력 DTO 2종 + 응답 DTO. 의존성 0.

**헤이센릿 order web 의 계약**이다(2026-09-20 구조 개편 메모). 향연은 이 포트를 쓰지 않는다
  (입력이 `prompt` 한 문장이 아니라 대화 이력 전문이라 `icad.py` 로 갈라져 있다).
한 파일에 포트·파라미터·응답을 모은 이유: 종전엔 `ports/recipe_port.py` + `dto/params.py` +
  `dto/replies.py` 셋에 흩어져, "generate 가 무엇을 받아 무엇을 주나"를 보려면 세 파일을 열어야 했다.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import dataclasses
from typing import Any

from heysenlyt_ai_port.llm import LlmPort


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


class RecipePort(ABC):
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
