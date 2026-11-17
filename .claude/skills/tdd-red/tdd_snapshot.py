"""TDD 스냅샷: git 없이 테스트 고정 · 변경 확인 · 되돌리기

- 실행 위치: 모듈 폴더 (tests/ · backend/ 가 있는 곳)
- 저장 위치: .lab/tdd/<unit>/red (tests + backend), .lab/tdd/<unit>/green (backend)

명령
- lock <unit>          RED 고정: tests/ · backend/ 를 red 로 복사 (tdd-red 끝)
- check <unit>         tests/ 가 red 와 같은지 (같으면 종료 코드 0, 다르면 1 + 파일 목록)
- restore <unit>       tests/ 를 red 로 되돌림
- changed <unit>       red 이후 바뀐 backend/ 파일 목록
- save <unit>          GREEN 저장: backend/ 를 green 으로 복사 (tdd-green 끝, 리팩토링 1건 통과 후)
- revert <unit>        backend/ 를 green 으로 되돌림 (리팩토링 실패 시)
"""

import shutil
import sys
from pathlib import Path

ROOT = Path.cwd()
IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")  # Windows 콘솔 기본 cp949 → 한글 깨짐 방지


def files(base: Path) -> dict[str, bytes]:
    """폴더 안 파일 → {상대 경로: 내용}, 줄바꿈 차이 (CRLF · LF) 는 무시"""
    if not base.is_dir():
        return {}
    return {p.relative_to(base).as_posix(): p.read_bytes().replace(b"\r\n", b"\n")
            for p in sorted(base.rglob("*"))
            if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"}


def diff(now: Path, snap: Path) -> list[str]:
    a, b = files(now), files(snap)
    return [f"{'추가' if k not in b else '삭제' if k not in a else '수정'}  {now.name}/{k}"
            for k in sorted(a.keys() | b.keys()) if a.get(k) != b.get(k)]


def copy(src: Path, dest: Path) -> None:
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest, ignore=IGNORE)


def main() -> int:
    if len(sys.argv) != 3 or sys.argv[1] not in ("lock", "check", "restore", "changed", "save", "revert"):
        print(__doc__)
        return 2
    cmd, unit = sys.argv[1], sys.argv[2].lower()
    tests, backend = ROOT / "tests", ROOT / "backend"
    if not tests.is_dir() or not backend.is_dir():
        print("tests/ · backend/ 가 없습니다. 모듈 폴더에서 실행하세요.")
        return 2
    red, green = ROOT / ".lab" / "tdd" / unit / "red", ROOT / ".lab" / "tdd" / unit / "green"
    if cmd == "lock":
        copy(tests, red / "tests")
        copy(backend, red / "backend")
        print(f"RED 고정 완료: {red.relative_to(ROOT).as_posix()} (테스트 파일 {len(files(tests))}개)")
        return 0
    if not red.is_dir():
        print(f"RED 스냅샷 없음 ({unit}) → tdd-red 를 먼저 끝내세요.")
        return 2
    if cmd == "check":
        changed = diff(tests, red / "tests")
        print("\n".join(changed) if changed else "tests/ 변경 없음 (RED 고정본과 동일)")
        return 1 if changed else 0
    if cmd == "restore":
        copy(red / "tests", tests)
        print("tests/ 를 RED 고정본으로 되돌림")
        return 0
    if cmd == "changed":
        changed = diff(backend, red / "backend")
        print("\n".join(changed) if changed else "backend/ 변경 없음")
        return 0
    if cmd == "save":
        copy(backend, green / "backend")
        print(f"GREEN 저장 완료: {green.relative_to(ROOT).as_posix()}")
        return 0
    if not green.is_dir():
        print(f"GREEN 스냅샷 없음 ({unit}) → tdd-green 완료 확인의 save 를 먼저 실행하세요.")
        return 2
    copy(green / "backend", backend)
    print("backend/ 를 GREEN 저장본으로 되돌림")
    return 0


if __name__ == "__main__":
    sys.exit(main())
