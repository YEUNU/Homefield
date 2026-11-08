# 로컬 LLM (온프레미스)

- 주소: `http://192.168.10.10/v1` (nginx 뒤 OpenAI 호환 프록시. 오류 형식으로 보아 LiteLLM으로 추정.)
- 인증: 개인 API 키 필요. `Authorization: Bearer $LOCAL_LLM_API_KEY`. 키·사용량 관리는 서버 첫 페이지의 링크에서 한다.
- 키는 `.env`에 둔다 (`.env.example` 참고). `.env`는 git에서 제외한다.

## 엔드포인트
| 경로 | 용도 |
|---|---|
| `GET /v1/models` | 모델 ID 목록. 모델 이름은 Hugging Face ID(`<기관>/<모델명>`)를 그대로 쓴다. |
| `GET /model_group/info` | 모델별 mode, 문맥 길이, 이미지·도구 지원 |
| `POST /v1/chat/completions` | 채팅 |
| `POST /v1/embeddings` | 임베딩 |
| `POST /v1/systemone` | 판단 모델(`mode: "decisions"`) 전용. 글을 생성하지 않고 보기별 확률을 낸다. |

## 주의 (서버 안내문 요약)
- thinking 모델은 느리다. `max_tokens`가 작으면 답이 비어 끝날 수 있다.
- 긴 답은 `"stream": true`를 쓴다.
- 빠른 직답: 요청에 `"chat_template_kwargs": {"enable_thinking": false}`를 넣는다.
- `/v1/systemone`: `state`(판단할 글) + `questions`. 질문 유형 `choice`, `noul`(예/아니오), `score`, `box`(영상 위치). 요청당 질문 128개, 입력 약 8만 토큰. 이미지 입력은 아직 안 된다.

## 하네스 관점 메모
- 판단 모델의 보기별 확률은 불확실성 원장의 "신뢰도" 입력으로 쓸 수 있다 (가설, 미검증).
- 연결 확인: `scripts/llm_check.sh`.
