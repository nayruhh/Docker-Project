import logging

import pytest

import logging_config


@pytest.fixture(autouse=True)
def isolated_logging(tmp_path, monkeypatch):
    """Write logs to a temp dir and restore the root logger afterwards."""
    monkeypatch.setattr(logging_config, "LOG_DIR", tmp_path)
    monkeypatch.setattr(logging_config, "LOG_FILE", tmp_path / "app.log")
    root = logging.getLogger()
    saved_handlers, saved_level = root.handlers[:], root.level
    yield
    for h in root.handlers[:]:
        root.removeHandler(h)
        h.close()
    root.handlers[:] = saved_handlers
    root.setLevel(saved_level)


def _flush():
    for h in logging.getLogger().handlers:
        h.flush()


def test_creates_console_and_file_handlers():
    logging_config.setup_logging()
    kinds = {type(h).__name__ for h in logging.getLogger().handlers}
    assert kinds == {"StreamHandler", "RotatingFileHandler"}


def test_log_line_is_written_to_file_with_format(tmp_path):
    logging_config.setup_logging()
    logging.getLogger("demo").warning("hello world")
    _flush()
    line = (tmp_path / "app.log").read_text(encoding="utf-8").strip()
    # "YYYY-MM-DD HH:MM:SS | WARNING  | demo:<line> | hello world"
    parts = [p.strip() for p in line.split("|")]
    assert len(parts) == 4
    assert parts[1] == "WARNING"
    assert parts[2].startswith("demo:")
    assert parts[3] == "hello world"


def test_console_respects_log_level_but_file_keeps_debug(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("LOG_LEVEL", "WARNING")
    logging_config.setup_logging()
    log = logging.getLogger("levels")
    log.info("quiet info")
    log.error("loud error")
    _flush()
    out = capsys.readouterr().out
    assert "loud error" in out and "quiet info" not in out
    file_text = (tmp_path / "app.log").read_text(encoding="utf-8")
    assert "loud error" in file_text and "quiet info" in file_text


def test_invalid_log_level_falls_back_to_info(monkeypatch):
    monkeypatch.setenv("LOG_LEVEL", "not-a-level")
    logging_config.setup_logging()
    console = next(h for h in logging.getLogger().handlers if type(h).__name__ == "StreamHandler")
    assert console.level == logging.INFO


def test_calling_setup_twice_does_not_duplicate_handlers():
    logging_config.setup_logging()
    logging_config.setup_logging()
    assert len(logging.getLogger().handlers) == 2
