from backend.api import routes


def test_runs_route_returns_list(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("DB_PATH", str(tmp_path / "validation.db"))

    result = routes.runs()

    assert result == []

