#!/usr/bin/env bash
# 자비스 원-스텝 설치 — macOS only
# Usage:  curl -fsSL https://raw.githubusercontent.com/no0m0321/jarvis/main/install.sh | bash
#         또는 git clone 후  ./install.sh
set -euo pipefail

GREEN='\033[0;32m'; YELLOW='\033[0;33m'; RED='\033[0;31m'; NC='\033[0m'
say()  { printf "${GREEN}▶ %s${NC}\n" "$*"; }
warn() { printf "${YELLOW}⚠ %s${NC}\n" "$*"; }
die()  { printf "${RED}✗ %s${NC}\n" "$*" >&2; exit 1; }

[[ "$(uname)" == "Darwin" ]] || die "macOS only (Linux/Windows은 P3 cross-platform 작업 후 지원)"

REPO_URL="https://github.com/no0m0321/jarvis.git"
REPO_DIR="${JARVIS_HOME:-$HOME/jarvis}"

# 1) Homebrew 의존성 (Python 3.9+, portaudio for sounddevice)
if ! command -v brew >/dev/null 2>&1; then
  die "Homebrew 미설치 — https://brew.sh"
fi
say "Homebrew 의존성 확인"
brew list portaudio >/dev/null 2>&1 || brew install portaudio
brew list python@3.11 >/dev/null 2>&1 || brew install python@3.11

# 2) 저장소 clone (이미 있으면 pull)
if [[ -d "$REPO_DIR/.git" ]]; then
  say "기존 저장소 업데이트: $REPO_DIR"
  git -C "$REPO_DIR" pull --ff-only
else
  say "저장소 clone: $REPO_DIR"
  git clone "$REPO_URL" "$REPO_DIR"
fi
cd "$REPO_DIR"

# 3) venv + 패키지 설치
if [[ ! -d ".venv" ]]; then
  say "venv 생성"
  python3 -m venv .venv
fi
say "Python 패키지 설치 (editable + dev)"
./.venv/bin/pip install -q --upgrade pip
./.venv/bin/pip install -q -e ".[dev]"

# 4) .env 초기화
if [[ ! -f ".env" ]]; then
  cp .env.example .env
  warn ".env 생성됨 — ANTHROPIC_API_KEY를 채우시오: $REPO_DIR/.env"
fi

# 5) JarvisHUD 빌드 (Swift)
if [[ -d "hud-overlay" ]]; then
  say "JarvisHUD overlay 빌드 (Swift release)"
  (cd hud-overlay && swift build -c release) || warn "HUD 빌드 실패 — 수동: cd hud-overlay && swift build -c release"
fi

# 6) PATH에 jarvis 심볼릭 (선택)
LOCAL_BIN="$HOME/.local/bin"
mkdir -p "$LOCAL_BIN"
ln -sf "$REPO_DIR/.venv/bin/jarvis" "$LOCAL_BIN/jarvis"
case ":$PATH:" in
  *":$LOCAL_BIN:"*) ;;
  *) warn "$LOCAL_BIN 을 PATH에 추가하시오 (~/.zshrc 또는 ~/.bashrc):  export PATH=\"$LOCAL_BIN:\$PATH\"" ;;
esac

# 7) 첫 실행 안내
cat <<EOF

${GREEN}✔ 설치 완료${NC}
다음 단계:
  1. $REPO_DIR/.env 에 ANTHROPIC_API_KEY 채우기
  2. jarvis init           — 첫 실행 마법사 (마이크/권한/daemon 등록)
  3. jarvis doctor         — 진단
  4. jarvis daemon install — wake daemon 백그라운드 실행
  5. jarvis ask "안녕"     — 동작 확인

문서: $REPO_DIR/README.md
EOF
