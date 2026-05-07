# Homebrew formula — 별도 tap repository에 배치 시 사용:
#   1) https://github.com/no0m0321/homebrew-jarvis 생성
#   2) 이 파일을 Formula/jarvis-voice.rb 로 복사
#   3) PyPI 배포 후 sha256 갱신:  brew fetch jarvis-voice  →  shasum -a 256 ...
#   4) 사용자:  brew tap no0m0321/jarvis && brew install jarvis-voice
#
# 또는 release artifacts 활용 (PyPI 배포 안 할 시):
#   url "https://github.com/no0m0321/jarvis/archive/refs/tags/v0.2.0.tar.gz"
class JarvisVoice < Formula
  include Language::Python::Virtualenv

  desc "Voice-first personal AI assistant (Claude-powered, Korean/English wake word)"
  homepage "https://github.com/no0m0321/jarvis"
  url "https://files.pythonhosted.org/packages/source/j/jarvis-voice/jarvis-voice-0.2.0.tar.gz"
  sha256 "REPLACE_WITH_SHA256_AFTER_PYPI_UPLOAD"
  license "MIT"

  depends_on "portaudio"
  depends_on "python@3.11"

  # 주요 의존성만 — pip resolver가 transitive dependencies 처리
  resource "anthropic" do
    url "https://files.pythonhosted.org/packages/source/a/anthropic/anthropic-0.40.0.tar.gz"
    sha256 "REPLACE"
  end

  def install
    virtualenv_install_with_resources
  end

  test do
    assert_match "jarvis", shell_output("#{bin}/jarvis version")
  end
end
