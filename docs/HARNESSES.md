# 비교 하네스 연결 기록

- 확인일: 2026-11-08
- 모델: `google/gemma-4-31B-it` (로컬 서버 `http://<LOCAL_LLM_HOST>`)
- 시험 과제: 파일 3개 폴더에서 "셸로 파일 목록을 보고 `COUNT=<개수>` 한 줄로 답하라". 도구 호출이 실제로 돌아야 풀린다.
- 모든 설정은 사용자 기존 설정과 분리했다 (설정 디렉터리 환경변수로 격리).

## 로컬 서버 API 지원 (실측)
| API | 결과 |
|---|---|
| OpenAI `/v1/chat/completions` + tools | 도구 호출 정상 |
| OpenAI `/v1/chat/completions` stream | 정상 |
| OpenAI `/v1/responses` | 정상 |
| Anthropic `/v1/messages` | 정상 |

## 하네스별 결과
| ID | 하네스 (버전) | 결과 | 연결 방식 | 비고 |
|---|---|---|---|---|
| H1 | mini-swe-agent 2.4.6 | 도구 호출 정상. 제출 형식 불일치 | litellm `openai/<모델>` + `OPENAI_API_BASE` | Python 3.12 필요(3.15에서 의존성 빌드 실패). `--with mcp` 필요. 종료 명령으로 제출하는 규약이라 과제 지시를 맞춰야 한다 |
| H2 | OpenHands CLI (SDK 1.21.0) | `COUNT=3` 정답 | `LLM_MODEL=openai/<모델>`, `LLM_BASE_URL`, `--override-with-envs` | headless + `--yolo`. CLI는 Docker 없이 동작. 격리 실행·GUI는 Docker 사용 |
| H3a | Codex CLI 0.167.0 | `COUNT=3` 정답 | `config.toml` 공급자 `wire_api="responses"` | "모델 메타데이터 없음" 경고. `exec -s workspace-write` |
| H3b | OpenCode (npm `opencode-ai`) | 정답 (`COUNT=4`: 설정 파일 포함) | `@ai-sdk/openai-compatible` 공급자 | `permission.bash=allow` |
| H4 | Claude Code (npm 최신) | `COUNT=3` 정답 | `ANTHROPIC_BASE_URL`, `ANTHROPIC_AUTH_TOKEN`, `ANTHROPIC_MODEL` 등 | "unrecognized_model" 경고. `-p` 비대화 모드 |

## 설정 요약 (키는 `.env`의 `LOCAL_LLM_API_KEY`)
```bash
# H4 Claude Code
CLAUDE_CONFIG_DIR=<격리 폴더> ANTHROPIC_BASE_URL=http://<LOCAL_LLM_HOST> \
ANTHROPIC_AUTH_TOKEN=$LOCAL_LLM_API_KEY ANTHROPIC_MODEL=google/gemma-4-31B-it \
ANTHROPIC_SMALL_FAST_MODEL=google/gemma-4-31B-it ANTHROPIC_DEFAULT_HAIKU_MODEL=google/gemma-4-31B-it \
npx -y @anthropic-ai/claude-code -p "<과제>" --allowedTools "Bash(ls*)"

# H3a Codex CLI: $CODEX_HOME/config.toml
#   model = "google/gemma-4-31B-it"; model_provider = "local"
#   [model_providers.local] base_url = "http://<LOCAL_LLM_HOST>/v1"; env_key = "LOCAL_LLM_API_KEY"; wire_api = "responses"
CODEX_HOME=<격리 폴더> npx -y @openai/codex exec --skip-git-repo-check -s workspace-write "<과제>"

# H3b OpenCode: 작업 폴더의 opencode.json 에 openai-compatible 공급자 정의
XDG_CONFIG_HOME=<격리> XDG_DATA_HOME=<격리> npx -y opencode-ai run "<과제>"

# H1 mini-swe-agent
OPENAI_API_BASE=http://<LOCAL_LLM_HOST>/v1 OPENAI_API_KEY=$LOCAL_LLM_API_KEY MSWEA_COST_TRACKING=ignore_errors \
uvx --python 3.12 --from mini-swe-agent --with mcp mini -m openai/google/gemma-4-31B-it -t "<과제>" -y -l 0 --exit-immediately

# H2 OpenHands
LLM_MODEL=openai/google/gemma-4-31B-it LLM_BASE_URL=http://<LOCAL_LLM_HOST>/v1 LLM_API_KEY=$LOCAL_LLM_API_KEY \
uvx --python 3.12 openhands --headless --yolo --override-with-envs --exit-without-confirmation -t "<과제>"
```

## Docker
- Docker Desktop을 쓴다 (사용자 설치, 서버 29.9.2). CLI 경로 `~/.docker/bin/docker`.
- 처음에 임시로 쓴 Colima·lima·Homebrew docker CLI는 지웠다 (2026-11-08).

## 공통 규약 (evalkit)
- 답 제출: 작업 폴더의 답 파일. 고객 질문: `<bin>/ask_user "질문"`. 제출: `<bin>/submit_answer`.
- 다섯 하네스 모두 이 규약으로 스모크 과제를 완료했다. 결과는 `docs/DIFFERENTIATION.md` §5.
- 실행: `python3 -m evalkit.run --task tasks/smoke-revenue`

## 남은 확인
1. ~~ask_user 공통화~~ → 셸 명령 규약으로 해결.
2. BIRD-Interact 공식 기준선(H5) 실행 환경.
3. 시험은 과제 1개, 1회 실행이다. 안정성(반복 실행 성공률)은 확인하지 않았다.
