---
status: stable
updated: 2026-11-08
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
| OpenAI `/v1/chat/completions` (tool calls, streaming) | `bare`, `opencode`, `qwen`, `goose`, `mini`, `openhands` |
| OpenAI `/v1/responses` | `codex` |
| Anthropic `/v1/messages` | `claude` |

## Connection for each harness
| ID | Harness | Connection method | Notes |
|---|---|---|---|
| `bare` | Homefield (`homefield/`) | `homefield/model.py` reads `.env` | Put the repository root in `PYTHONPATH` |
| `claude` | Claude Code | `ANTHROPIC_BASE_URL`, `ANTHROPIC_AUTH_TOKEN`, `ANTHROPIC_MODEL` | You can ignore the model name warning (`unrecognized_model`). Use the non-interactive `-p` mode |
| `codex` | Codex CLI | Provider in `config.toml`, `wire_api = "responses"` | In the sandbox, `ask_user` works only if `sandbox_workspace_write.network_access=true` is set |
| `opencode` | OpenCode | `@ai-sdk/openai-compatible` provider, `OPENCODE_CONFIG` | Allow bash and edit in `permission` |
| `qwen` | Qwen Code | `OPENAI_BASE_URL`, `OPENAI_API_KEY`, `OPENAI_MODEL`, `--auth-type openai` | `-p --yolo`. `HOME` isolates the settings |
| `goose` | Goose CLI (Homebrew `block-goose-cli`) | `GOOSE_PROVIDER=openai`, `OPENAI_HOST`, `OPENAI_BASE_PATH=v1/chat/completions` | `goose run --no-session -t`, `GOOSE_MODE=auto` |
| `mini` | mini-swe-agent | litellm `openai/<model>`, `OPENAI_API_BASE` | Needs Python 3.12 and `--with mcp`. The protocol submits with an exit command, so the answer comes from the answer file |
| `openhands` | OpenHands CLI | `LLM_MODEL=openai/<model>`, `LLM_BASE_URL`, `--override-with-envs` | Headless + `--yolo`. The CLI runs without Docker |

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

# qwen (Qwen Code)
HOME=<isolated dir> OPENAI_BASE_URL=$LOCAL_LLM_BASE_URL OPENAI_API_KEY=$LOCAL_LLM_API_KEY OPENAI_MODEL=google/gemma-4-31B-it \
npx -y @qwen-code/qwen-code -p "<task>" --yolo --auth-type openai

# goose (Goose)
HOME=<isolated dir> GOOSE_PROVIDER=openai GOOSE_MODEL=google/gemma-4-31B-it GOOSE_MODE=auto GOOSE_DISABLE_KEYRING=1 \
OPENAI_HOST=$LOCAL_LLM_HOST OPENAI_BASE_PATH=v1/chat/completions OPENAI_API_KEY=$LOCAL_LLM_API_KEY \
goose run --no-session -t "<task>"

# mini (mini-swe-agent)
OPENAI_API_BASE=$LOCAL_LLM_BASE_URL OPENAI_API_KEY=$LOCAL_LLM_API_KEY MSWEA_COST_TRACKING=ignore_errors \
uvx --python 3.12 --from mini-swe-agent --with mcp mini -m openai/google/gemma-4-31B-it -t "<task>" -y -l 0 --exit-immediately

# openhands (OpenHands)
LLM_MODEL=openai/google/gemma-4-31B-it LLM_BASE_URL=$LOCAL_LLM_BASE_URL LLM_API_KEY=$LOCAL_LLM_API_KEY \
uvx --python 3.12 openhands --headless --yolo --override-with-envs --exit-without-confirmation -t "<task>"
```

## Run environment
- Docker: Docker Desktop (CLI `~/.docker/bin/docker`). It is used for container-isolated runs.
- Required tools: `node`/`npx`, `uv`/`uvx`, Homebrew `block-goose-cli`.

## Not implemented
- `terminus` (needs the Terminal-Bench run framework), `bird-official`.
