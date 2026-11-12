---
status: stable
updated: 2026-11-12
audience: public
---
# How to connect comparison harnesses

This document describes how evalkit connects each harness to a local OpenAI-compatible model. The adapter code is in `evalkit/adapters.py`. The harness list and the selection criteria are in `docs/EVALUATION.md` §6.

- Reference model: `google/gemma-4-31B-it`.
- Each episode folder isolates all harness settings (config directory environment variable or `HOME`). The harnesses do not change existing user settings.
- The key is `LOCAL_LLM_API_KEY` in `.env`. The server address is `LOCAL_LLM_BASE_URL` (`.../v1`) and `LOCAL_LLM_HOST` (the part before `/v1`).

## Required server APIs
| API | Harnesses that use it |
|---|---|
| OpenAI `/v1/chat/completions` (tool calls, streaming) | `bare`, `opencode`, `pi`, `omp`, `hermes` |
| OpenAI `/v1/responses` | `codex` |
| Anthropic `/v1/messages` | `claude` |

## Connection for each harness
| ID | Harness | Connection method | Notes |
|---|---|---|---|
| `bare` | Homefield (`homefield/`) | `homefield/model.py` reads `.env` | Put the repository root in `PYTHONPATH` |
| `claude` | Claude Code | `ANTHROPIC_BASE_URL`, `ANTHROPIC_AUTH_TOKEN`, `ANTHROPIC_MODEL` | You can ignore the model name warning (`unrecognized_model`). Use the non-interactive `-p` mode |
| `codex` | Codex CLI | Provider in `config.toml`, `wire_api = "responses"` | In the sandbox, `ask_user` works only if `sandbox_workspace_write.network_access=true` is set |
| `opencode` | OpenCode | `@ai-sdk/openai-compatible` provider, `OPENCODE_CONFIG` | Allow bash and edit in `permission` |
| `pi` | Pi (`@earendil-works/pi-coding-agent`) | Custom provider in `models.json` (`api: openai-completions`), found by `PI_CODING_AGENT_DIR` | `-p --no-session --model local/<model>`. `PI_OFFLINE=1` stops catalog refreshes |
| `omp` | oh-my-pi (`@oh-my-pi/pi-coding-agent`) | Custom provider in `models.yml`, found by `PI_CODING_AGENT_DIR`; `apiKey` names the environment variable | Needs the Bun runtime; `npx -p bun` fetches it. `-p --no-session --auto-approve` |
| `hermes` | Hermes Agent (PyPI `hermes-agent`) | `config.yaml` in `HERMES_HOME`: `model.provider: custom`, `model.base_url`, `model.api_key: ${LOCAL_LLM_API_KEY}` | `hermes chat -Q --yolo -q`. Needs Python 3.12 |

## Command examples
```bash
# bare (Homefield)
PYTHONPATH=<repo> python3 -m homefield -p "<task>"

# claude (Claude Code)
CLAUDE_CONFIG_DIR=<isolated dir> ANTHROPIC_BASE_URL=$LOCAL_LLM_HOST ANTHROPIC_AUTH_TOKEN=$LOCAL_LLM_API_KEY \
ANTHROPIC_MODEL=google/gemma-4-31B-it ANTHROPIC_SMALL_FAST_MODEL=google/gemma-4-31B-it \
npx -y @anthropic-ai/claude-code -p "<task>" --allowedTools "Bash,Read,Write,Edit,Glob,Grep"

# codex (Codex CLI): $CODEX_HOME/config.toml
#   model = "google/gemma-4-31B-it"; model_provider = "local"
#   [model_providers.local] base_url = "$LOCAL_LLM_BASE_URL"; env_key = "LOCAL_LLM_API_KEY"; wire_api = "responses"
CODEX_HOME=<isolated dir> npx -y @openai/codex exec --skip-git-repo-check -s workspace-write \
  -c sandbox_workspace_write.network_access=true "<task>"

# opencode (OpenCode): define an openai-compatible provider in the file that OPENCODE_CONFIG points to
OPENCODE_CONFIG=<isolated dir>/opencode.json XDG_CONFIG_HOME=<isolated dir> npx -y opencode-ai run "<task>"

# pi (Pi): <isolated dir>/models.json
#   {"providers": {"local": {"baseUrl": "$LOCAL_LLM_BASE_URL", "api": "openai-completions",
#     "apiKey": "$LOCAL_LLM_API_KEY", "models": [{"id": "google/gemma-4-31B-it"}]}}}
PI_CODING_AGENT_DIR=<isolated dir> PI_OFFLINE=1 PI_TELEMETRY=0 \
npx -y @earendil-works/pi-coding-agent -p --no-session --model local/google/gemma-4-31B-it "<task>"

# omp (oh-my-pi): <isolated dir>/models.yml with the same provider; apiKey: LOCAL_LLM_API_KEY (name of the variable)
PI_CODING_AGENT_DIR=<isolated dir> \
npx -y -p bun -p @oh-my-pi/pi-coding-agent omp -p --no-session --auto-approve --model local/google/gemma-4-31B-it "<task>"

# hermes (Hermes Agent): <isolated dir>/config.yaml
#   model: {default: google/gemma-4-31B-it, provider: custom, base_url: $LOCAL_LLM_BASE_URL, api_key: ${LOCAL_LLM_API_KEY}}
HERMES_HOME=<isolated dir> uvx --python 3.12 --from hermes-agent hermes chat -Q --yolo -q "<task>"
```

## Run environment
- Docker: Docker Desktop (CLI `~/.docker/bin/docker`). It is used for container-isolated runs.
- Required tools: `node`/`npx` (Node.js 22.19 or later, for `pi`), `uv`/`uvx`.

## Not implemented
- `terminus` (needs the Terminal-Bench run framework), `bird-official`.
