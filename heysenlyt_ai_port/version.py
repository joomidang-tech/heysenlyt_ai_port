"""VersionPort + VersionInfo — 버전을 알려주는 약속과 그 값. 의존성 0.

포트와 그 DTO 를 한 파일에 둔다(2026-09-20 구조 개편) — 종전엔 `ports/version_port.py` 와
  `dto/params.py` 로 갈려 있어, 한 계약을 보려면 두 파일을 열어야 했다.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


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


class VersionPort(ABC):
    """버전을 알려주는 방법 — 연구소가 상속해 구현한다."""

    @abstractmethod
    def get_version(self) -> VersionInfo:
        ...
