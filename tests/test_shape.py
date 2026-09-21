"""모양 계약 — 포트는 order web 으로 먼저 갈린다(`heysenlyt/` · `icad/` · `shared/`).

통합코드(`heysenlyt-ai/application`)와 어댑터(`heysenlyt_ai_adapter`)가 같은 세 폴더를 갖는다.
어댑터를 통째 복사해 쓰는 구조라, 한 층만 모양이 달라지면 "같은 자리를 열면 된다"가 깨진다.
"""

from __future__ import annotations

import ast
from pathlib import Path

import heysenlyt_ai_port

PKG = Path(heysenlyt_ai_port.__file__).parent
FOLDERS = ("heysenlyt", "icad", "shared")
_IMPORT_ROOT = PKG.parent.resolve()  # 패키지가 놓인 자리(절대 모듈 이름의 기준)


def _imports(py: Path) -> set[str]:
    """이 파일이 import 하는 모듈의 **절대 이름**. 상대 import(`from ..icad import x`)도 절대 이름으로 풀어서 본다 —
    안 풀면 `module="icad"` 로만 보여 방향 규칙을 조용히 빠져나간다(검증 2026-09-21)."""
    out: set[str] = set()
    parts = list(py.resolve().relative_to(_IMPORT_ROOT).with_suffix("").parts)
    pkg = parts[:-1]  # 이 파일이 속한 패키지(`__init__.py` 도 같은 규칙)
    for node in ast.walk(ast.parse(py.read_text(encoding="utf-8"))):
        if isinstance(node, ast.ImportFrom):
            if node.level:
                base = pkg[: len(pkg) - (node.level - 1)]
                names = [node.module] if node.module else [a.name for a in node.names]
                out.update(".".join([*base, n]) for n in names)
            elif node.module:
                out.add(node.module)
        elif isinstance(node, ast.Import):
            out.update(a.name for a in node.names)
    return out


def test_three_folders_and_nothing_else_at_root():
    dirs = sorted(p.name for p in PKG.iterdir() if p.is_dir() and p.name != "__pycache__")
    assert dirs == sorted(FOLDERS)
    files = sorted(p.name for p in PKG.glob("*.py"))
    assert files == ["__init__.py"], "계약 파일은 세 폴더 안에만 둔다"


def test_dependency_direction():
    for folder, forbidden in (("shared", ("heysenlyt", "icad")), ("heysenlyt", ("icad",)), ("icad", ("heysenlyt",))):
        for py in (PKG / folder).rglob("*.py"):
            for mod in _imports(py):
                for f in forbidden:
                    assert not mod.startswith(f"heysenlyt_ai_port.{f}"), f"{folder}/{py.name} → {mod}"


def test_public_surface_is_top_level_only():
    # 내부 배치를 바꿔도 소비자가 안 깨지는 근거 — 이름은 전부 톱레벨에서 나간다.
    for name in heysenlyt_ai_port.__all__:
        assert hasattr(heysenlyt_ai_port, name), name
