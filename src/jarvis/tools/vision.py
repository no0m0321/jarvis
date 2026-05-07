"""비전 도구 — Claude vision으로 이미지/화면/웹캠 분석 + OCR.

Cross-platform (macOS/Windows/Linux):
- vision_analyze: 이미지 파일 분석 — 모든 OS
- vision_screen:  화면 캡처(mss) → Claude vision — 모든 OS
- camera_describe: 웹캠 1프레임(opencv) → Claude vision — 모든 OS
- ocr_image: tesseract → macOS shortcuts (mac만) → Claude vision fallback
"""
from __future__ import annotations

import base64
import io
import os
import subprocess
import tempfile
from pathlib import Path

from jarvis.platform import IS_MACOS
from jarvis.tools.registry import REGISTRY, Tool


# ──────────────────── 공통 헬퍼 ────────────────────
def _read_image_b64(path: str) -> tuple[str, str]:
    """이미지 파일 → base64 + media_type."""
    p = Path(path).expanduser()
    if not p.exists():
        raise FileNotFoundError(f"이미지 없음: {p}")
    ext = p.suffix.lower().lstrip(".")
    media_map = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png", "gif": "gif", "webp": "webp"}
    media_type = f"image/{media_map.get(ext, 'jpeg')}"
    return base64.b64encode(p.read_bytes()).decode(), media_type


def _vision_call(b64: str, media_type: str, question: str, max_tokens: int = 1024) -> str:
    """Claude vision API 호출."""
    try:
        from anthropic import Anthropic
    except ImportError:
        return "ERROR: anthropic SDK 미설치"
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        return "ERROR: ANTHROPIC_API_KEY 미설정"
    try:
        client = Anthropic(api_key=key)
        msg = client.messages.create(
            model=os.environ.get("JARVIS_VISION_MODEL", "claude-opus-4-7"),
            max_tokens=max_tokens,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": b64}},
                    {"type": "text", "text": question},
                ],
            }],
        )
        return "".join(b.text for b in msg.content if b.type == "text")
    except Exception as e:
        return f"ERROR: vision call failed: {type(e).__name__}: {e}"


def _capture_screen_bytes() -> tuple[bytes, str] | None:
    """현재 화면을 PNG bytes로. 실패 시 None."""
    if IS_MACOS:
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            tmp = f.name
        try:
            subprocess.run(["screencapture", "-x", "-t", "png", tmp], check=True, timeout=10)
            data = Path(tmp).read_bytes()
            return (data, "image/png")
        except Exception:
            return None
        finally:
            try:
                os.unlink(tmp)
            except Exception:
                pass
    # Windows / Linux: mss
    try:
        import mss
        from PIL import Image
        with mss.mss() as sct:
            shot = sct.grab(sct.monitors[0])  # all displays
            img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
            buf = io.BytesIO()
            img.save(buf, format="PNG", optimize=True)
            return (buf.getvalue(), "image/png")
    except Exception:
        return None


def _capture_webcam_bytes() -> tuple[bytes, str] | None:
    """웹캠 한 프레임을 PNG bytes로. 실패 시 None.

    OpenCV (cv2.VideoCapture) — 모든 OS에서 작동.
    """
    try:
        import cv2  # type: ignore
        from PIL import Image
    except ImportError:
        return None
    cap = None
    try:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            return None
        # warmup — 첫 1~2프레임은 노출 미조정 흑백 가능
        for _ in range(3):
            cap.read()
        ok, frame = cap.read()
        if not ok or frame is None:
            return None
        # BGR → RGB
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(rgb)
        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        return (buf.getvalue(), "image/png")
    except Exception:
        return None
    finally:
        if cap is not None:
            cap.release()


# ──────────────────── 도구 핸들러 ────────────────────
def _vision_analyze(image_path: str, question: str = "이 이미지에 무엇이 보이는가?") -> str:
    """Claude vision으로 이미지 분석."""
    try:
        b64, media_type = _read_image_b64(image_path)
    except Exception as e:
        return f"ERROR: 이미지 로드 실패: {e}"
    return _vision_call(b64, media_type, question)


def _vision_screen(question: str = "현재 화면에 무엇이 있는가? 한국어로 짧게 (3문장 이하) 설명.") -> str:
    """현재 화면 캡처 → vision 분석. 모든 OS."""
    captured = _capture_screen_bytes()
    if not captured:
        return "ERROR: 화면 캡처 실패 — 화면 녹화 권한 또는 mss/Pillow 설치 확인"
    data, media_type = captured
    b64 = base64.b64encode(data).decode()
    return _vision_call(b64, media_type, question, max_tokens=512)


def _camera_describe(question: str = "지금 카메라에 보이는 장면을 한국어로 짧게 (3문장 이하) 설명.") -> str:
    """웹캠 1프레임 → vision 분석. 모든 OS (OpenCV 필요)."""
    captured = _capture_webcam_bytes()
    if not captured:
        return (
            "ERROR: 웹캠 캡처 실패 — opencv-python 설치 + 카메라 권한 확인 "
            "(macOS: 설정 → 개인정보 보호 → 카메라 / Windows: 설정 → 개인정보 → 카메라)"
        )
    data, media_type = captured
    b64 = base64.b64encode(data).decode()
    return _vision_call(b64, media_type, question, max_tokens=512)


def _ocr_image(image_path: str) -> str:
    """OCR — tesseract → (mac만) shortcuts → Claude vision fallback."""
    p = Path(image_path).expanduser()
    if not p.exists():
        return f"ERROR: 이미지 없음: {p}"

    # 1) tesseract (모든 OS, 사용자가 brew/apt/choco install 한 경우)
    try:
        r = subprocess.run(
            ["tesseract", str(p), "-", "-l", "kor+eng"],
            capture_output=True, text=True, timeout=30,
        )
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    except FileNotFoundError:
        pass

    # 2) macOS Shortcuts "Extract Text from Image"
    if IS_MACOS:
        try:
            r = subprocess.run(
                ["shortcuts", "run", "Extract Text from Image", "-i", str(p)],
                capture_output=True, text=True, timeout=15,
            )
            if r.returncode == 0:
                return r.stdout.strip() or "(텍스트 없음)"
        except FileNotFoundError:
            pass

    # 3) Claude vision fallback
    return _vision_analyze(str(p), "이 이미지의 모든 텍스트를 그대로 추출해서 출력. 텍스트만, 설명 없이.")


# ──────────────────── 등록 ────────────────────
REGISTRY.register(Tool(
    name="vision_analyze",
    description="이미지 파일을 Claude vision으로 분석. 사진 내용 설명, 질문 답변, 차트 해석 등.",
    input_schema={
        "type": "object",
        "properties": {
            "image_path": {"type": "string", "description": "이미지 파일 절대/홈 경로"},
            "question": {"type": "string", "description": "이미지에 대한 질문"},
        },
        "required": ["image_path"],
    },
    handler=_vision_analyze,
))

REGISTRY.register(Tool(
    name="vision_screen",
    description=(
        "현재 화면을 캡처해서 Claude vision으로 분석 (macOS/Windows/Linux). "
        "'화면에 뭐 있어?' '내가 지금 뭐 하고 있어?' 'OO 창 어디?' 같은 발화에 사용."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "question": {"type": "string", "description": "화면에 대한 질문"},
        },
    },
    handler=_vision_screen,
))

REGISTRY.register(Tool(
    name="camera_describe",
    description=(
        "웹캠 1프레임을 캡처해서 Claude vision으로 분석 (macOS/Windows/Linux, OpenCV 필요). "
        "'카메라로 봐', '나 어때 보여' 같은 발화에 사용."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "question": {"type": "string", "description": "장면에 대한 질문"},
        },
    },
    handler=_camera_describe,
))

REGISTRY.register(Tool(
    name="ocr_image",
    description="이미지에서 텍스트 추출 (한국어/영어). tesseract → macOS shortcuts → Claude vision 순서로 fallback.",
    input_schema={
        "type": "object",
        "properties": {"image_path": {"type": "string"}},
        "required": ["image_path"],
    },
    handler=_ocr_image,
))
