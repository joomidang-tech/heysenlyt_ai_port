"""VersionPort + VersionInfo — 버전을 알려주는 약속과 그 값. 의존성 0.

세대 무관 계약이라 패키지 최상위에 둔다(2026-09-27). 세대 id ↔ 폴더명 변환도 여기 — 세 층(포트·어댑터·통합코드)이
  같은 규칙으로 폴더를 찾는다.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from heysenlyt_ai_port.errors import PortContractError


@dataclass(frozen=True)
class VersionInfo:
    """AI 세대 버전 — 주문 도장(kernelVersion)의 출처. 도장 3필드 = model·mode·released_at.

    계보: v1.2.0 워크오더 "커널 버전 코드 소유"(2026-07-20) — 버전의 진실은 문서가 아니라
    코드가 들고 다닌다. lib/expo/stamp.ts(EXPO_STAMP·FRAGRANCE_STAMP)의 일반화.
    """

    model_id: str  # 예 "fragrance-rule" — 도장의 model 축 근원
    domain: str  # "fragrance" | "flavor"
    version: str  # "1.0.0"
    spec: str = ""  # 대상 기기 스펙 (예 "senlyt-shop"/"expo") — 비면 미지정
    notes: str = ""  # 체인지로그 한 줄
    # ⚠️ 신규 필드는 항상 끝에 추가 — 위치인자 소비자가 있어도 계약이 안 깨지게
    released_at: str = ""  # 그 세대가 나온 날 (도장의 released_at)
    model_type: str = ""  # "llm-pipeline"


@dataclass(frozen=True)
class Stamp:
    """산출물 도장 — "어느 세대·방식이 이걸 만들었나"를 결과에 찍는 값(2026-09-29 dict → 클래스).

    레시피·대화·향연 결과가 모두 이 네 칸을 싣는다. web 이 영속하는 값이라 와이어 키(snake_case)를 그대로 쓴다.
    kernel_version 은 `{model}+{mode}+{released_at}` 한 문자열(v1.2.0 stampVersion 과 같은 형식).
    ⛔ 네 칸 모두 **비어 있으면 안 된다** — 빈 도장은 "누가 만들었는지 모른다"를 조용히 영속한다.
    """

    model: str
    mode: str
    released_at: str
    kernel_version: str

    def __post_init__(self) -> None:
        for name in ("model", "mode", "released_at", "kernel_version"):
            v = getattr(self, name)
            if not isinstance(v, str) or not v.strip():
                raise PortContractError(f"Stamp.{name} 는 비어 있지 않은 문자열이어야 한다: {v!r}")

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "Stamp":
        if not isinstance(d, Mapping):
            raise PortContractError(f"Stamp.from_dict: Mapping 이 아니다({type(d).__name__})")
        missing = [k for k in ("model", "mode", "released_at", "kernel_version") if k not in d]
        if missing:
            raise PortContractError(f"Stamp.from_dict: 필수 키 누락 {missing}")
        return cls(model=d["model"], mode=d["mode"], released_at=d["released_at"],
                   kernel_version=d["kernel_version"])

    def to_dict(self) -> dict[str, str]:
        return {"model": self.model, "mode": self.mode, "released_at": self.released_at,
                "kernel_version": self.kernel_version}


class VersionPort(ABC):
    """버전을 알려주는 방법 — 연구소가 상속해 구현한다."""

    @abstractmethod
    def get_version(self) -> VersionInfo:
        ...


# ── 세대 id ↔ 폴더명 (세 층 공통 규칙) ─────────────────────────────────────────
#   web 레지스트리 id(`sensorium-fragrance-1.0.0`) → 파이썬 패키지명(`sensorium_fragrance_1_0_0`).
#   `+tecan` 같은 **기기 변형 접미는 AI 세대가 아니다** — 접어서 base 로 본다(web registry.ts 주석과 같은 규칙).
def base_version(version_id: str | None) -> str | None:
    """`sensorium-fragrance-1.0.0+tecan` → `sensorium-fragrance-1.0.0`. None/빈 값은 None."""
    if not version_id or not isinstance(version_id, str):
        return None
    v = version_id.strip()
    return (v.split("+", 1)[0] or None) if v else None


def generation_folder(version_id: str) -> str:
    """세대 id → 세대 폴더(패키지)명. 규칙 하나: `-` 와 `.` 을 `_` 로. 빈 값·접미뿐인 값은 ValueError(조용히 None 을 만들지 않는다)."""
    base = base_version(version_id)
    if not base:
        raise ValueError(f"세대 id 가 비었다: {version_id!r}")
    return base.replace("-", "_").replace(".", "_")
