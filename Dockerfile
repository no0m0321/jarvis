# 자비스 headless mode — 음성/HUD 제외, 'jarvis ask' / 'jarvis do' / 'jarvis chat'만
# Build:  docker build -t jarvis-voice:latest .
# Run:    docker run --rm -e ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY jarvis-voice:latest ask "안녕"

FROM python:3.11-slim AS builder

# 빌드 의존성 (audio 라이브러리는 headless에서 불필요하지만 sounddevice import에 필요한 portaudio dev만)
RUN apt-get update && apt-get install -y --no-install-recommends \
    portaudio19-dev libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY src/ ./src/

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e ".[openai,memory]"


FROM python:3.11-slim

# Runtime 의존성 (portaudio shared lib만)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libportaudio2 libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Non-root user
RUN useradd -m -u 1000 jarvis
USER jarvis
WORKDIR /home/jarvis

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin/jarvis /usr/local/bin/jarvis
COPY --from=builder /app /app

# Headless mode 표시 — wake/listen/voice 명령은 Linux에서 마이크 접근 불가
ENV JARVIS_HEADLESS=1

ENTRYPOINT ["jarvis"]
CMD ["--help"]
