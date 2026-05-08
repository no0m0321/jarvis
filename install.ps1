# 자비스 원-스텝 설치 — Windows (PowerShell 5+)
# Usage:
#   $env:JARVIS_LANG="ja"; iwr https://raw.githubusercontent.com/no0m0321/jarvis/main/install.ps1 -UseBasicParsing | iex
#   또는 git clone 후:  powershell -ExecutionPolicy Bypass -File install.ps1
#
# install.sh와 의미적으로 동등. macOS 전용 절차(brew portaudio, Swift HUD 빌드)는 Windows에서 skip.
#
# v0.7.0 강화:
# - ExecutionPolicy Restricted 환경 자동 감지 + 안내 (`-ExecutionPolicy Bypass` 권장)
# - Python winget fallback (Python 미설치 시 winget 자동 설치 옵션 제공)
# - pip install retry (네트워크 일시 끊김 복구) — 최대 3회
# - 부분 실패 시 partial 상태 명시 (어디까지 됐는지 사용자에게 표시)

$ErrorActionPreference = "Stop"

function Write-Info  { param([string]$msg) Write-Host "▶ $msg" -ForegroundColor Green }
function Write-Warn  { param([string]$msg) Write-Host "⚠ $msg" -ForegroundColor Yellow }
function Write-Err   { param([string]$msg) Write-Host "✗ $msg" -ForegroundColor Red; exit 1 }

# 0) ExecutionPolicy 검증 — 사용자 환경에서 스크립트가 차단됐는지
$policy = Get-ExecutionPolicy -Scope CurrentUser
if ($policy -eq "Restricted" -or $policy -eq "AllSigned") {
    Write-Warn "현재 ExecutionPolicy: $policy — 스크립트 실행이 제한될 수 있습니다."
    Write-Warn "권장 실행 방법:"
    Write-Warn "  powershell -ExecutionPolicy Bypass -File install.ps1"
    Write-Warn "또는 한 줄 설치 시:"
    Write-Warn "  iwr https://...install.ps1 -UseBasicParsing | iex"
    Write-Warn "(iex는 Restricted를 우회하므로 정상 동작)"
}

# 1) Python 3.11+ 확인 + 미설치 시 winget 자동 설치 옵션
function Find-Python {
    foreach ($cmd in @("py -3.11", "py -3.12", "py -3", "python3", "python")) {
        try {
            $ver = & cmd /c "$cmd --version 2>&1"
            if ($LASTEXITCODE -eq 0 -and $ver -match "Python\s+3\.(9|1[0-9])") {
                return @{ cmd = $cmd; ver = $ver }
            }
        } catch { continue }
    }
    return $null
}

function Install-PythonViaWinget {
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        return $false
    }
    Write-Info "winget으로 Python 3.11 자동 설치 시도..."
    & winget install --id Python.Python.3.11 --accept-source-agreements --accept-package-agreements --silent 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        # PATH 갱신 (winget 설치 후 새 세션 권장이지만 가능한 경우 reload)
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + `
                    [System.Environment]::GetEnvironmentVariable("Path", "User")
        return $true
    }
    return $false
}

function Invoke-PipWithRetry {
    param([string[]]$Args, [int]$MaxRetries = 3)
    for ($i = 1; $i -le $MaxRetries; $i++) {
        & cmd /c "$VenvPip $Args 2>&1" | Out-Null
        if ($LASTEXITCODE -eq 0) { return $true }
        if ($i -lt $MaxRetries) {
            Write-Warn "pip 실패 (시도 $i/$MaxRetries) — $([math]::Pow(2,$i))초 후 재시도..."
            Start-Sleep -Seconds ([math]::Pow(2, $i))
        }
    }
    return $false
}

# 1) Python 3.11+ 확인 — 미설치 시 winget 자동 설치 시도
$pyInfo = Find-Python
if (-not $pyInfo) {
    Write-Warn "Python 3.9+ 미설치 감지."
    if (Install-PythonViaWinget) {
        $pyInfo = Find-Python
    }
}
if (-not $pyInfo) {
    Write-Warn "Python 3.9+ 설치 방법:"
    Write-Warn "  winget install Python.Python.3.11"
    Write-Warn "  또는 https://www.python.org/downloads/windows/ 에서 다운로드"
    Write-Err "Python 3.9+ 가 필요합니다 (winget 자동 설치도 실패)"
}
$py = $pyInfo.cmd
Write-Info "Python found: $py ($($pyInfo.ver))"

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

Write-Info "Python 패키지 설치 (editable + dev) — retry up to 3x"
# upgrade pip with retry
$pipUpgradeOk = $false
for ($i = 1; $i -le 3; $i++) {
    & $VenvPip install -q --upgrade pip
    if ($LASTEXITCODE -eq 0) { $pipUpgradeOk = $true; break }
    if ($i -lt 3) {
        Write-Warn "pip upgrade 실패 (시도 $i/3) — 재시도..."
        Start-Sleep -Seconds ([math]::Pow(2, $i))
    }
}
if (-not $pipUpgradeOk) { Write-Warn "pip upgrade 실패 — 기존 pip로 진행" }

# editable install with retry
$installOk = $false
for ($i = 1; $i -le 3; $i++) {
    & $VenvPip install -q -e ".[dev]"
    if ($LASTEXITCODE -eq 0) { $installOk = $true; break }
    if ($i -lt 3) {
        Write-Warn "pip install 실패 (시도 $i/3) — $([math]::Pow(2,$i))초 후 재시도..."
        Start-Sleep -Seconds ([math]::Pow(2, $i))
    }
}
if (-not $installOk) {
    Write-Err "pip install 실패 (3회 재시도 후) — 네트워크 또는 의존성 문제. 수동: $VenvPip install -e `".[dev]`""
}

# 4) .env 초기화
if (-not (Test-Path ".env")) {
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env"
        Write-Warn ".env 생성됨 — ANTHROPIC_API_KEY를 채우시오: $RepoDir\.env"
    }
}

# 4b) JARVIS_LANG env로 들어왔으면 ~/.jarvis/config.toml에 language 사전 저장
$JarvisLang = $env:JARVIS_LANG
if ($JarvisLang) {
    $JarvisLang = $JarvisLang.ToLower().Trim()
    if ($JarvisLang -in @("ko","en","ja","zh","es","fr","de","pt")) {
        $JarvisHome = Join-Path $env:USERPROFILE ".jarvis"
        if (-not (Test-Path $JarvisHome)) { New-Item -ItemType Directory -Force -Path $JarvisHome | Out-Null }
        $CfgPath = Join-Path $JarvisHome "config.toml"
        $newLine = "language = `"$JarvisLang`""
        if (-not (Test-Path $CfgPath)) {
            $newLine | Out-File -FilePath $CfgPath -Encoding UTF8
            Write-Info "언어 사전 설정: language = `"$JarvisLang`" → $CfgPath"
        } else {
            $content = Get-Content $CfgPath
            if ($content -match '^language') {
                $content -replace '^language.*', $newLine | Set-Content $CfgPath -Encoding UTF8
            } else {
                @($newLine) + $content | Set-Content $CfgPath -Encoding UTF8
            }
            Write-Info "언어 갱신: language = `"$JarvisLang`""
        }
    } else {
        Write-Warn "지원되지 않는 JARVIS_LANG='$JarvisLang' (지원: ko/en/ja/zh/es/fr/de/pt)"
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
