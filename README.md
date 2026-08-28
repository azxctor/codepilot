# CodePilot

CodePilot is a Python prototype for a local interactive coding agent CLI.

Current milestone:

- `codepilot init` creates a local `.codepilot/config.toml`.
- `codepilot` and `codepilot chat` start an interactive shell.
- `/status`, `/plan`, and `/exit` are available in the shell.
- `codepilot run "<task>"` sends one task through the same conversation agent.
- The default OpenAI-compatible endpoint is Kimi Coding at `https://api.kimi.com/coding/v1` with model `kimi-k3`.
- The conversation agent can execute read-only workspace tools through JSON tool requests: `list_files`, `read_file`, and `search_text`.

Before using the LLM locally, set the API key in your shell:

```bash
export MOONSHOT_API_KEY="your-api-key"
```

`CODEPILOT_API_KEY` is still accepted as a legacy fallback. The key is intentionally not stored in the repository. File tools, approvals, and session recovery are planned in later milestones.

Check the local configuration without printing the full secret:

```bash
env PYTHONPATH=src python3 -m codepilot doctor
```

## Troubleshooting

If Python reports `CERTIFICATE_VERIFY_FAILED` while `curl` can access the same API, the local Python OpenSSL certificate store is not trusting the certificate chain. CodePilot uses `certifi` for the stdlib `urllib` fallback path. In custom network environments, point CodePilot to an explicit CA bundle:

```bash
export CODEPILOT_CA_BUNDLE="/path/to/ca-bundle.pem"
```

`SSL_CERT_FILE` is also honored when `CODEPILOT_CA_BUNDLE` is not set.
