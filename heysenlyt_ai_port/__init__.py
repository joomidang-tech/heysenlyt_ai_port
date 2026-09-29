"""heysenlyt_ai_port — heysenlyt(프로덕트팀) ↔ SENSORIUM(연구소) 계약 라이브러리.

## 구성 — **센소리움 세대가 축이다** (2026-09-27 개편)
포트 · 어댑터(`heysenlyt_ai_adapter`) · 통합코드(`heysenlyt-ai/application`)가 **같은 세대 폴더**를 갖는다.
  세대 폴더 하나 = "그 세대에 통합코드가 부르는 호출(포트)" 전부. 어댑터는 같은 이름의 폴더에서 그 포트를
  구현하고, 통합코드는 그 폴더를 **그대로 복사**해 꽂은 뒤 요청의 `sensorium_version` 으로 세대를 고른다.

| 폴더 | 세대 id | domain | 포트 |
|------|---------|--------|------|
| `sensorium_fragrance_1_0_0/` | sensorium-fragrance-1.0.0 | fragrance | `recipe.py`(generate·regenerate) · `conversation.py` |
| `sensorium_expo_0_1_2/`      | sensorium-expo-0.1.2      | flavor    | `recipe.py`(generate) · `conversation.py` |
| `sensorium_icad_0_1_0/`      | sensorium-icad-0.1.0 (가id) | fragrance | `conversation.py` · `compose.py` |
| 최상위                       | —                         | —         | `llm.py`(LlmPort · 역방향) · `errors.py` · `version.py`(VersionPort · Stamp · id↔폴더 규칙) |

⛔ **세대 폴더는 자기완결** — 세대끼리 import 금지. 세대 폴더가 의존할 수 있는 건 최상위 3파일뿐(tests/test_shape.py).
⛔ 의존성 0 — 표준 라이브러리 외 import 금지(test_dependency_free.py).
⛔ **공개 표면 = 세대 폴더 + 최상위 3파일.** 세대마다 같은 이름의 클래스(RecipePort 등)가 있으므로 톱레벨 재수출은
   세대 무관 심볼만 한다. 소비자는 `from heysenlyt_ai_port.sensorium_fragrance_1_0_0 import RecipePort` 로 쓴다.
   (2026-09-21 까지의 `from heysenlyt_ai_port import RecipePort` 는 **사라졌다** — 소비자는 어댑터·통합코드 둘뿐이고 같은 사이클에 옮겼다.)
"""

from heysenlyt_ai_port import sensorium_expo_0_1_2, sensorium_fragrance_1_0_0, sensorium_icad_0_1_0
from heysenlyt_ai_port.errors import LlmError, LlmResponseError, LlmTimeoutError, LlmUnavailableError, PortContractError
from heysenlyt_ai_port.llm import LlmPort
from heysenlyt_ai_port.version import Stamp, VersionInfo, VersionPort, base_version, generation_folder

# 세대 레지스트리 — 어댑터(`heysenlyt_ai_adapter.GENERATIONS`)와 **키가 같아야** 한다(양쪽 test_shape 가 잠근다).
GENERATIONS = {
    sensorium_fragrance_1_0_0.VERSION_ID: sensorium_fragrance_1_0_0,
    sensorium_expo_0_1_2.VERSION_ID: sensorium_expo_0_1_2,
    sensorium_icad_0_1_0.VERSION_ID: sensorium_icad_0_1_0,
}

# ── ⚠️ 하위호환 shim — **v1.4.0 사이클 동안만** (2026-09-27 검증팀 P1) ─────────────────────────
#   통합 레포 `main`·`dev`(개편 전 코드)와 옛 어댑터 사본은 `from heysenlyt_ai_port import RecipeParam` 같은 톱레벨 이름을
#   쓰고, requirements 가 이 포트를 **브랜치** `@v1.4.0` 으로 핀한다. 이 이름들이 없으면 포트 push 직후부터 prod/dev 재빌드
#   (핫픽스 포함)가 ImportError 로 막힌다. 그래서 옛 이름을 **향장향·향연 세대의 것으로 그대로** 내보낸다 — 옛 코드는 세대가
#   하나였고 그 하나가 이 둘이다(식향 어댑터가 향장향 RecipePort 를 상속해도 메서드가 더 있을 뿐이라 동작 같음).
#   ⛔ 새 코드는 이 이름을 쓰지 않는다(세대 모듈에서 가져온다 — 아래 `__all__` 에도 넣지 않는다). 통합 `main` 이 세대 축
#   코드로 승격되면 이 블록을 **지운다**(다음 폴더 버전 v1.5.0 에는 없어야 한다).
from heysenlyt_ai_port.sensorium_fragrance_1_0_0 import (  # noqa: E402,F401 — shim
    ConversationParam, ConversationPort, ConverseReply, Demographics,
    Palette, RecipeParam, RecipePort, RecipeReply, RegenerateParam,
)
from heysenlyt_ai_port.sensorium_icad_0_1_0 import (  # noqa: E402,F401 — shim (옛 이름 = Icad 접두)
    ComposeParam as IcadComposeParam, ComposePort as IcadComposePort, ComposePrior as IcadPrior,
    ComposeReply as IcadComposeReply, ComposeTurn as IcadTurn,
)
LEGACY_TOP_LEVEL_NAMES = (
    "ConversationParam", "ConversationPort", "ConverseReply", "Demographics", "Palette",
    "RecipeParam", "RecipePort", "RecipeReply", "RegenerateParam",
    "IcadComposeParam", "IcadComposePort", "IcadPrior", "IcadComposeReply", "IcadTurn",
)

__all__ = [
    "GENERATIONS",
    "LlmError", "LlmPort", "LlmResponseError", "LlmTimeoutError", "LlmUnavailableError", "PortContractError",
    "Stamp", "VersionInfo", "VersionPort", "base_version", "generation_folder",
    "sensorium_expo_0_1_2", "sensorium_fragrance_1_0_0", "sensorium_icad_0_1_0",
]
