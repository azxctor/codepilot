from dataclasses import replace

from codepilot.config import DEFAULT_CONFIG
from codepilot.diagnostics import build_doctor_report


def test_doctor_report_warns_when_config_uses_legacy_api_key_env() -> None:
    config = replace(DEFAULT_CONFIG, api_key_env="CODEPILOT_API_KEY")

    report = build_doctor_report(config, {"CODEPILOT_API_KEY": "kimi-test-key-legacy1234567890"})

    rendered = "\n".join(report)
    assert "configured_api_key_env: CODEPILOT_API_KEY" in rendered
    assert 'migration_hint: set api_key_env to "MOONSHOT_API_KEY"' in rendered
