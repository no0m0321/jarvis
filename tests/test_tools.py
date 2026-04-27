from jarvis.tools import REGISTRY


def test_registry_populated() -> None:
    names = set(REGISTRY.names())
    expected = {
        "run_shell", "read_file", "write_file", "list_dir", "search_files",
        "fetch_url", "notify", "say", "open_url",
    }
    assert expected.issubset(names), f"missing: {expected - names}"


def test_specs_valid() -> None:
    for spec in REGISTRY.specs():
        assert "name" in spec
        assert "description" in spec
        assert spec["input_schema"]["type"] == "object"
        assert "properties" in spec["input_schema"]


def test_run_shell_smoke() -> None:
    result = REGISTRY.dispatch("run_shell", {"command": "echo jarvis"})
    assert "jarvis" in result
    assert "exit_code=0" in result


def test_list_dir_smoke() -> None:
    result = REGISTRY.dispatch("list_dir", {"path": "."})
    assert result
    assert "ERROR" not in result


def test_search_files_smoke() -> None:
    result = REGISTRY.dispatch("search_files", {"pattern": "*.py", "root": "src"})
    assert "agent.py" in result or "cli.py" in result


def test_unknown_tool_returns_error() -> None:
    result = REGISTRY.dispatch("nonexistent_tool", {})
    assert "unknown tool" in result.lower()


def test_invalid_args_returns_error() -> None:
    result = REGISTRY.dispatch("run_shell", {})
    assert "ERROR" in result or "invalid" in result.lower()
