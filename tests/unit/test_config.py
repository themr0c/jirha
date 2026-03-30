from jirha.config import _load_env_file


def test_load_env_file(tmp_path):
    env = tmp_path / ".env"
    env.write_text("JIRA_EMAIL=test@example.com\nJIRA_API_TOKEN=token123\n")
    result = _load_env_file(env)
    assert result == {"JIRA_EMAIL": "test@example.com", "JIRA_API_TOKEN": "token123"}


def test_load_env_file_missing(tmp_path):
    result = _load_env_file(tmp_path / "nonexistent.env")
    assert result == {}


def test_load_env_file_skips_comments_and_blanks(tmp_path):
    env = tmp_path / ".env"
    env.write_text("# comment\n\nKEY=value\nANOTHER=val=with=equals\n")
    result = _load_env_file(env)
    assert result == {"KEY": "value", "ANOTHER": "val=with=equals"}
