---
status: 확정
updated: 2026-11-08
audience: 배포
---
# 비교 하네스 연결 방법

evalkit이 각 하네스를 로컬 OpenAI 호환 모델에 연결하는 방법이다. 어댑터 구현은 `evalkit/adapters.py`, 하네스 목록과 선정 기준은 `docs/EVALUATION.md` §6.

- 기준 모델: `google/gemma-4-31B-it`.
- 모든 하네스 설정은 에피소드 폴더 안에 격리한다 (설정 디렉터리 환경변수 또는 `HOME`). 사용자 기존 설정을 건드리지 않는다.
- 키는 `.env`의 `LOCAL_LLM_API_KEY`, 서버 주소는 `LOCAL_LLM_BASE_URL`(`.../v1`)과 `LOCAL_LLM_HOST`(그 앞부분).

## 필요한 서버 API
| API | 쓰는 하네스 |
|---|---|
| OpenAI `/v1/chat/completions` (도구 호출, 스트리밍) | `bare`, `opencode`, `qwen`, `goose`, `mini`, `openhands` |
| OpenAI `/v1/responses` | `codex` |
| Anthropic `/v1/messages` | `claude` |

## 하네스별 연결
| ID | 하네스 | 연결 방식 | 주의 |
|---|---|---|---|
| `bare` | Homefield (`homefield/`) | `homefield/model.py`가 `.env`를 읽는다 | 저장소 루트를 `PYTHONPATH`에 둔다 |
| `claude` | Claude Code | `ANTHROPIC_BASE_URL`, `ANTHROPIC_AUTH_TOKEN`, `ANTHROPIC_MODEL` | 모델 이름 경고(`unrecognized_model`)는 무시해도 된다. `-p` 비대화 모드 |
| `codex` | Codex CLI | `config.toml` 공급자, `wire_api = "responses"` | 샌드박스에서 `sandbox_workspace_write.network_access=true`가 있어야 `ask_user`가 된다 |
| `opencode` | OpenCode | `@ai-sdk/openai-compatible` 공급자, `OPENCODE_CONFIG` | `permission`에서 bash·edit 허용 |
| `qwen` | Qwen Code | `OPENAI_BASE_URL`, `OPENAI_API_KEY`, `OPENAI_MODEL`, `--auth-type openai` | `-p --yolo`. 설정 격리는 `HOME` |
| `goose` | Goose CLI (Homebrew `block-goose-cli`) | `GOOSE_PROVIDER=openai`, `OPENAI_HOST`, `OPENAI_BASE_PATH=v1/chat/completions` | `goose run --no-session -t`, `GOOSE_MODE=auto` |
| `mini` | mini-swe-agent | litellm `openai/<모델>`, `OPENAI_API_BASE` | Python 3.12 필요, `--with mcp` 필요. 종료 명령으로 제출하는 규약이라 답은 답 파일로 받는다 |
| `openhands` | OpenHands CLI | `LLM_MODEL=openai/<모델>`, `LLM_BASE_URL`, `--override-with-envs` | headless + `--yolo`. CLI는 Docker 없이 돈다 |

## 명령 예
```bash
# bare (Homefield)
PYTHONPATH=<저장소> python3 -m homefield -p "<과제>"

# claude (Claude Code)
CLAUDE_CONFIG_DIR=<격리> ANTHROPIC_BASE_URL=$LOCAL_LLM_HOST ANTHROPIC_AUTH_TOKEN=$LOCAL_LLM_API_KEY \
ANTHROPIC_MODEL=google/gemma-4-31B-it ANTHROPIC_SMALL_FAST_MODEL=google/gemma-4-31B-it \
npx -y @anthropic-ai/claude-code -p "<과제>" --allowedTools "Bash,Read,Write,Edit,Glob,Grep"

# codex (Codex CLI): $CODEX_HOME/config.toml
#   model = "google/gemma-4-31B-it"; model_provider = "local"
#   [model_providers.local] base_url = "$LOCAL_LLM_BASE_URL"; env_key = "LOCAL_LLM_API_KEY"; wire_api = "responses"
CODEX_HOME=<격리> npx -y @openai/codex exec --skip-git-repo-check -s workspace-write \
  -c sandbox_workspace_write.network_access=true "<과제>"

# opencode (OpenCode): OPENCODE_CONFIG가 가리키는 파일에 openai-compatible 공급자 정의
OPENCODE_CONFIG=<격리>/opencode.json XDG_CONFIG_HOME=<격리> npx -y opencode-ai run "<과제>"

# qwen (Qwen Code)
HOME=<격리> OPENAI_BASE_URL=$LOCAL_LLM_BASE_URL OPENAI_API_KEY=$LOCAL_LLM_API_KEY OPENAI_MODEL=google/gemma-4-31B-it \
npx -y @qwen-code/qwen-code -p "<과제>" --yolo --auth-type openai

# goose (Goose)
HOME=<격리> GOOSE_PROVIDER=openai GOOSE_MODEL=google/gemma-4-31B-it GOOSE_MODE=auto GOOSE_DISABLE_KEYRING=1 \
OPENAI_HOST=$LOCAL_LLM_HOST OPENAI_BASE_PATH=v1/chat/completions OPENAI_API_KEY=$LOCAL_LLM_API_KEY \
goose run --no-session -t "<과제>"

# mini (mini-swe-agent)
OPENAI_API_BASE=$LOCAL_LLM_BASE_URL OPENAI_API_KEY=$LOCAL_LLM_API_KEY MSWEA_COST_TRACKING=ignore_errors \
uvx --python 3.12 --from mini-swe-agent --with mcp mini -m openai/google/gemma-4-31B-it -t "<과제>" -y -l 0 --exit-immediately

# openhands (OpenHands)
LLM_MODEL=openai/google/gemma-4-31B-it LLM_BASE_URL=$LOCAL_LLM_BASE_URL LLM_API_KEY=$LOCAL_LLM_API_KEY \
uvx --python 3.12 openhands --headless --yolo --override-with-envs --exit-without-confirmation -t "<과제>"
```

## 실행 환경
- Docker: Docker Desktop (CLI `~/.docker/bin/docker`). 컨테이너 격리 실행에 쓴다.
- 필요 도구: `node`/`npx`, `uv`/`uvx`, Homebrew `block-goose-cli`.

## 미구현
- `terminus` (Terminal-Bench 실행 틀 필요), `bird-official`.
