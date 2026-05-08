# 자비스 원-스텝 설치 — Windows (PowerShell 5+)
# Usage:
#   iwr https://raw.githubusercontent.com/no0m0321/jarvis/main/install.ps1 -UseBasicParsing | iex
#   또는 git clone 후 ./install.ps1
#
# install.sh와 의미적으로 동등. macOS 전용 절차(brew portaudio, Swift HUD 빌드)는 Windows에서 skip.

$ErrorActionPreference = "Stop"

function Write-Info  { param([string]$msg) Write-Host "▶ $msg" -ForegroundColor Green }
function Write-Warn  { param([string]$msg) Write-Host "⚠ $msg" -ForegroundColor Yellow }
function Write-Err   { param([string]$msg) Write-Host "✗ $msg" -ForegroundColor Red; exit 1 }

# 1) Python 3.11+ 확인
$py = $null
foreach ($cmd in @("py -3.11", "py -3.12", "py -3", "python3", "python")) {
    try {
        $ver = & cmd /c "$cmd --version 2>&1"
        if ($LASTEXITCODE -eq 0 -and $ver -match "Python\s+3\.(9|1[0-9])") {
            $py = $cmd
            Write-Info "Python found: $cmd ($ver)"
            break
        }
    } catch { continue }
}
if (-not $py) {
    Write-Warn "Python 3.9+ 미설치. 설치 방법:"
    Write-Warn "  winget install Python.Python.3.11"
    Write-Warn "  또는 https://www.python.org/downloads/windows/ 에서 다운로드"
    Write-Err "Python 3.9+ 가 필요합니다"
}

# 2) 저장소 위치 결정 + clone
$RepoUrl = "https://github.com/no0m0321/jarvis.git"
$RepoDir = if ($env:JARVIS_HOME) { $env:JARVIS_HOME } else { Join-Path $env:USERPROFILE "jarvis" }

if (Test-Path (Join-Path $RepoDir ".git")) {
    Write-Info "기존 저장소 업데이트: $RepoDir"
    git -C $RepoDir pull --ff-only
} else {
    Write-Info "저장소 clone: $RepoDir"
    git clone $RepoUrl $RepoDir
}
Set-Location $RepoDir

# 3) venv + 패키지 설치
$VenvDir = Join-Path $RepoDir ".venv"
if (-not (Test-Path $VenvDir)) {
    Write-Info "venv 생성"
    & cmd /c "$py -m venv .venv"
    if ($LASTEXITCODE -ne 0) { Write-Err "venv 생성 실패" }
}
$VenvPip = Join-Path $VenvDir "Scripts\pip.exe"
$VenvJarvis = Join-Path $VenvDir "Scripts\jarvis.exe"
if (-not (Test-Path $VenvPip)) { Write-Err "venv pip 없음: $VenvPip" }

Write-Info "Python 패키지 설치 (editable + dev)"
& $VenvPip install -q --upgrade pip
& $VenvPip install -q -e ".[dev]"
if ($LASTEXITCODE -ne 0) { Write-Err "pip install 실패" }

# 4) .env 초기화
if (-not (Test-Path ".env")) {
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env"
        Write-Warn ".env 생성됨 — ANTHROPIC_API_KEY를 채우시오: $RepoDir\.env"
    }
}

# 5) HUD 빌드 — Windows에서는 skip
if (Test-Path "hud-overlay") {
    Write-Warn "HUD overlay (Swift)는 Windows 미지원 — skip. (P3 cross-platform 작업 후 지원)"
}

# 6) PATH에 jarvis.exe 추가 안내
$LocalBin = Join-Path $env:LOCALAPPDATA "Programs\jarvis"
if (-not (Test-Path $LocalBin)) {
    New-Item -ItemType Directory -Force -Path $LocalBin | Out-Null
}
# .bat 래퍼 생성 (PATH에 venv를 직접 안 넣고, 짧은 진입점만 노출)
$BatPath = Join-Path $LocalBin "jarvis.bat"
@"
@echo off
"$VenvJarvis" %*
"@ | Out-File -FilePath $BatPath -Encoding ASCII -Force
Write-Info "jarvis.bat 생성: $BatPath"

# 사용자 PATH에 LocalBin 포함되어 있는지 확인 (없으면 안내만)
$UserPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($UserPath -notlike "*$LocalBin*") {
    Write-Warn "$LocalBin 을 PATH에 추가해야 합니다."
    Write-Warn "  PowerShell:  [Environment]::SetEnvironmentVariable('Path', [Environment]::GetEnvironmentVariable('Path', 'User') + ';$LocalBin', 'User')"
    Write-Warn "  또는 시스템 환경 변수 편집 → 사용자 변수 Path 에 $LocalBin 추가"
}

# 7) 첫 실행 안내
Write-Host ""
Write-Host "✔ 설치 완료" -ForegroundColor Green
Write-Host @"
다음 단계:
  1. $RepoDir\.env 에 ANTHROPIC_API_KEY 채우기
  2. jarvis init                — 첫 실행 마법사 (마이크/권한)
  3. jarvis doctor              — 진단
  4. jarvis daemon install      — wake daemon (Windows Task Scheduler) 등록
  5. jarvis ask "안녕"          — 동작 확인

문서: $RepoDir\README.md
Windows 한정 사항: $RepoDir\docs\TODO_WINDOWS.md
"@
