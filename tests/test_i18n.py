"""i18n 시스템 테스트 — 8개 언어 지원 + persona 분기 + assistant 통합."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from jarvis import i18n, persona


# ─── i18n core ──────────────────────────────────────────────
class TestI18nCore:
    SUPPORTED_8 = ["ko", "en", "ja", "zh", "es", "fr", "de", "pt"]

    def test_supported_langs_count(self) -> None:
        assert len(i18n.SUPPORTED_LANGS) == 8
        assert set(i18n.SUPPORTED_LANGS) == set(self.SUPPORTED_8)

    def test_each_lang_has_meta(self) -> None:
        for code in self.SUPPORTED_8:
            meta = i18n.LANGUAGES[code]
            for key in ["name", "english_name", "native", "flag", "default_title", "tts_voice_macos", "tts_voice_windows"]:
                assert key in meta, f"{code} missing {key}"
                assert meta[key], f"{code}.{key} is empty"

    def test_each_lang_has_first_meeting_greeting(self) -> None:
        for code in self.SUPPORTED_8:
            text = i18n.first_meeting_greeting(code)
            assert text, f"{code} greeting empty"
            # 4가지 핵심 요소 — 도구 이름/카테고리 명시
            assert "personalization_observe" in text
            assert "memory_save" in text

    def test_each_lang_has_respond_in_lang_suffix(self) -> None:
        for code in self.SUPPORTED_8:
            suf = i18n.respond_in_lang_suffix(code)
            assert "ALWAYS respond" in suf or "respond" in suf.lower()

    def test_default_title_per_lang(self) -> None:
        assert i18n.default_title("ko") == "주인님"
        assert i18n.default_title("en") == "Sir"
        assert i18n.default_title("ja") == "ご主人様"
        assert i18n.default_title("zh") == "主人"
        assert i18n.default_title("es") == "Señor"
        assert i18n.default_title("fr") == "Monsieur"
        assert i18n.default_title("de") == "Herr"
        assert i18n.default_title("pt") == "Senhor"

    def test_tts_voice_per_lang(self) -> None:
        assert i18n.tts_voice("ko", "macos") == "Yuna"
        assert i18n.tts_voice("ko", "windows") == "Heami"
        assert i18n.tts_voice("en", "macos") == "Reed"
        assert i18n.tts_voice("ja", "macos") == "Kyoko"
        assert i18n.tts_voice("zh", "windows") == "Huihui"

    def test_is_supported(self) -> None:
        assert i18n.is_supported("ko")
        assert i18n.is_supported("EN")  # case-insensitive
        assert not i18n.is_supported("xx")
        assert not i18n.is_supported("")

    def test_unknown_lang_falls_back_to_default(self) -> None:
        assert i18n.lang_meta("xx") == i18n.lang_meta(i18n.DEFAULT_LANG)
        assert i18n.first_meeting_greeting("xx") == i18n.first_meeting_greeting(i18n.DEFAULT_LANG)


# ─── detect_lang priority ───────────────────────────────────
class TestDetectLang:
    def test_env_jarvis_lang_takes_priority(self, monkeypatch) -> None:
        monkeypatch.setenv("JARVIS_LANG", "ja")
        assert i18n.detect_lang() == "ja"

    def test_env_normalizes_locale_format(self, monkeypatch) -> None:
        # 'ko_KR.UTF-8' / 'ko-KR' / 'ko' 모두 'ko'로
        for val in ["ko_KR.UTF-8", "ko-KR", "ko", "KO_kr"]:
            monkeypatch.setenv("JARVIS_LANG", val)
            assert i18n.detect_lang() == "ko", f"failed for {val}"

    def test_unknown_env_lang_ignored(self, monkeypatch) -> None:
        """알 수 없는 언어는 무시되고 다음 우선순위로."""
        monkeypatch.setenv("JARVIS_LANG", "xx")
        # config 비어있고 locale도 영어/모름 → en fallback (또는 시스템 ko)
        result = i18n.detect_lang()
        assert result in i18n.SUPPORTED_LANGS

    def test_config_toml_used_when_no_env(self, monkeypatch, tmp_path) -> None:
        monkeypatch.delenv("JARVIS_LANG", raising=False)
        # ~/.jarvis/config.toml mock
        from jarvis import user_config
        cfg_dir = tmp_path / ".jarvis"
        cfg_dir.mkdir()
        cfg_path = cfg_dir / "config.toml"
        cfg_path.write_text('language = "fr"\n')
        monkeypatch.setattr(user_config, "_CONFIG_PATH", cfg_path)
        assert i18n.detect_lang() == "fr"

    def test_fallback_to_default_lang(self, monkeypatch) -> None:
        monkeypatch.delenv("JARVIS_LANG", raising=False)
        # config도 없고 locale도 없을 때
        from jarvis import user_config
        monkeypatch.setattr(user_config, "_CONFIG_PATH", Path("/nonexistent/cfg.toml"))
        result = i18n.detect_lang()
        # 시스템 locale에 따라 다를 수 있지만, SUPPORTED_LANGS 안에 있어야
        assert result in i18n.SUPPORTED_LANGS


# ─── persona language branching ─────────────────────────────
class TestPersonaLanguageBranch:
    def test_ko_returns_korean_native(self, monkeypatch) -> None:
        monkeypatch.setenv("JARVIS_LANG", "ko")
        prompt = persona.get_active()
        assert "주인님" in prompt
        assert "한국어" in prompt
        # 영어 directive는 없어야 (네이티브 ko)
        assert "ALWAYS respond" not in prompt

    def test_en_returns_english_native(self, monkeypatch) -> None:
        monkeypatch.setenv("JARVIS_LANG", "en")
        prompt = persona.get_active()
        assert "Sir" in prompt
        assert "English" in prompt
        # ko 흔적 없어야
        assert "주인님" not in prompt

    def test_non_native_lang_uses_english_base_with_directive(self, monkeypatch) -> None:
        """ja/zh/es/fr/de/pt — 영어 base + respond_in_lang_suffix."""
        for code in ["ja", "zh", "es", "fr", "de", "pt"]:
            monkeypatch.setenv("JARVIS_LANG", code)
            prompt = persona.get_active()
            # 영어 jarvis persona base
            assert "J.A.R.V.I.S." in prompt or "Jarvis" in prompt
            # Language directive
            assert "Language directive" in prompt or "ALWAYS respond" in prompt
            # 해당 언어 명시
            meta = i18n.LANGUAGES[code]
            assert meta["english_name"] in prompt or meta["native"] in prompt

    def test_persona_modes_per_lang(self, monkeypatch) -> None:
        """jarvis/casual/formal/creative 모드 각 언어로 작동."""
        for lang in ["ko", "en"]:
            for mode in ["jarvis", "casual", "formal", "creative"]:
                monkeypatch.setenv("JARVIS_LANG", lang)
                monkeypatch.setenv("JARVIS_PERSONA", mode)
                prompt = persona.get_active()
                assert prompt
                assert len(prompt) > 50  # 의미있는 길이


# ─── assistant first-meeting per language ───────────────────
class TestAssistantFirstMeetingI18n:
    @pytest.fixture(autouse=True)
    def isolated_home(self, tmp_path, monkeypatch):
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        from jarvis import observations as obs
        from jarvis import profile as prof
        monkeypatch.setattr(prof, "PROFILE_PATH", tmp_path / ".jarvis" / "profile.json")
        monkeypatch.setattr(obs, "OBSERVATIONS_PATH", tmp_path / ".jarvis" / "observations.jsonl")
        monkeypatch.setattr(obs, "ARCHIVE_PATH", tmp_path / ".jarvis" / "observations.archive.jsonl")
        # 첫 만남 상태
        if (tmp_path / ".jarvis" / "profile.json").exists():
            (tmp_path / ".jarvis" / "profile.json").unlink()
        yield

    def test_first_meeting_korean(self, monkeypatch) -> None:
        monkeypatch.setenv("JARVIS_LANG", "ko")
        from jarvis.assistant import _build_system_prompt
        sp = _build_system_prompt()
        assert "주인님 반갑습니다" in sp
        assert "자비스입니다" in sp
        assert "어떻게 호칭" in sp
        assert "personalization_observe" in sp

    def test_first_meeting_english(self, monkeypatch) -> None:
        monkeypatch.setenv("JARVIS_LANG", "en")
        from jarvis.assistant import _build_system_prompt
        sp = _build_system_prompt()
        assert "Greetings, Sir" in sp
        assert "Jarvis" in sp
        assert "How would you like" in sp
        assert "personalization_observe" in sp

    def test_first_meeting_japanese(self, monkeypatch) -> None:
        monkeypatch.setenv("JARVIS_LANG", "ja")
        from jarvis.assistant import _build_system_prompt
        sp = _build_system_prompt()
        assert "ご主人様" in sp
        assert "자비스" in sp or "jarvis" in sp.lower()
        assert "personalization_observe" in sp

    def test_first_meeting_chinese(self, monkeypatch) -> None:
        monkeypatch.setenv("JARVIS_LANG", "zh")
        from jarvis.assistant import _build_system_prompt
        sp = _build_system_prompt()
        assert "主人" in sp
        assert "您好" in sp or "您" in sp

    def test_first_meeting_spanish(self, monkeypatch) -> None:
        monkeypatch.setenv("JARVIS_LANG", "es")
        from jarvis.assistant import _build_system_prompt
        sp = _build_system_prompt()
        assert "Señor" in sp
        assert "Bienvenido" in sp

    def test_first_meeting_french(self, monkeypatch) -> None:
        monkeypatch.setenv("JARVIS_LANG", "fr")
        from jarvis.assistant import _build_system_prompt
        sp = _build_system_prompt()
        assert "Monsieur" in sp
        assert "Bonjour" in sp

    def test_first_meeting_german(self, monkeypatch) -> None:
        monkeypatch.setenv("JARVIS_LANG", "de")
        from jarvis.assistant import _build_system_prompt
        sp = _build_system_prompt()
        assert "Herr" in sp
        assert "Guten Tag" in sp

    def test_first_meeting_portuguese(self, monkeypatch) -> None:
        monkeypatch.setenv("JARVIS_LANG", "pt")
        from jarvis.assistant import _build_system_prompt
        sp = _build_system_prompt()
        assert "Senhor" in sp
        assert "Bem-vindo" in sp


# ─── CLI lang command ───────────────────────────────────────
class TestCliLangCommand:
    def test_cli_lang_list_runs(self) -> None:
        """jarvis lang --list — 8개 언어 표시."""
        import subprocess
        from pathlib import Path
        repo = Path(__file__).resolve().parents[1]
        venv_jarvis = repo / ".venv" / "bin" / "jarvis"
        if not venv_jarvis.exists():
            pytest.skip("venv jarvis not built")
        r = subprocess.run(
            [str(venv_jarvis), "lang", "--list"],
            capture_output=True, text=True, timeout=10, encoding="utf-8",
        )
        assert r.returncode == 0
        # 8개 언어 코드 모두 표시
        for code in ["ko", "en", "ja", "zh", "es", "fr", "de", "pt"]:
            assert code in r.stdout, f"missing {code}"

    def test_cli_lang_set_unsupported_returns_error(self) -> None:
        """jarvis lang xx — exit 1."""
        import subprocess
        from pathlib import Path
        repo = Path(__file__).resolve().parents[1]
        venv_jarvis = repo / ".venv" / "bin" / "jarvis"
        if not venv_jarvis.exists():
            pytest.skip("venv jarvis not built")
        r = subprocess.run(
            [str(venv_jarvis), "lang", "xx_nonexistent"],
            capture_output=True, text=True, timeout=10, encoding="utf-8",
        )
        assert r.returncode != 0


# ─── messages ─────────────────────────────────────────────────
class TestI18nMessages:
    def test_msg_returns_lang_specific(self) -> None:
        ko_msg = i18n.msg("lang_current", "ko")
        en_msg = i18n.msg("lang_current", "en")
        assert ko_msg != en_msg
        assert "현재 언어" == ko_msg
        assert "Current language" == en_msg

    def test_msg_unknown_key_returns_key(self) -> None:
        result = i18n.msg("totally_nonexistent_key_xyz")
        assert result == "totally_nonexistent_key_xyz"

    def test_msg_unknown_lang_falls_back_to_en(self) -> None:
        result = i18n.msg("lang_current", "xx")
        assert result == "Current language"  # en fallback


# ─── user_config set_value ────────────────────────────────────
class TestUserConfigSetValue:
    def test_set_value_creates_file(self, tmp_path, monkeypatch) -> None:
        from jarvis import user_config
        cfg = tmp_path / ".jarvis" / "config.toml"
        monkeypatch.setattr(user_config, "_CONFIG_PATH", cfg)
        user_config.set_value("language", "ja")
        assert cfg.exists()
        content = cfg.read_text(encoding="utf-8")
        assert 'language = "ja"' in content

    def test_set_value_updates_existing(self, tmp_path, monkeypatch) -> None:
        from jarvis import user_config
        cfg = tmp_path / ".jarvis" / "config.toml"
        cfg.parent.mkdir()
        cfg.write_text('language = "en"\nvoice = "Reed"\n')
        monkeypatch.setattr(user_config, "_CONFIG_PATH", cfg)
        user_config.set_value("language", "fr")
        content = cfg.read_text(encoding="utf-8")
        assert 'language = "fr"' in content
        assert 'language = "en"' not in content
        # 다른 키는 보존
        assert 'voice = "Reed"' in content

    def test_set_value_appends_when_missing(self, tmp_path, monkeypatch) -> None:
        from jarvis import user_config
        cfg = tmp_path / ".jarvis" / "config.toml"
        cfg.parent.mkdir()
        cfg.write_text('voice = "Reed"\n')
        monkeypatch.setattr(user_config, "_CONFIG_PATH", cfg)
        user_config.set_value("language", "de")
        content = cfg.read_text(encoding="utf-8")
        assert 'language = "de"' in content
        assert 'voice = "Reed"' in content

    def test_set_value_preserves_section_headers(self, tmp_path, monkeypatch) -> None:
        from jarvis import user_config
        cfg = tmp_path / ".jarvis" / "config.toml"
        cfg.parent.mkdir()
        cfg.write_text(
            'voice = "Reed"\n\n[hud]\nsilence_threshold = 0.012\n'
        )
        monkeypatch.setattr(user_config, "_CONFIG_PATH", cfg)
        user_config.set_value("language", "es")
        content = cfg.read_text(encoding="utf-8")
        # [hud] 섹션은 유지, language는 root level (section 앞)에 추가
        assert 'language = "es"' in content
        assert "[hud]" in content
        assert "silence_threshold" in content
        # language가 [hud] 헤더 앞에 와야
        lang_idx = content.index('language')
        section_idx = content.index('[hud]')
        assert lang_idx < section_idx
