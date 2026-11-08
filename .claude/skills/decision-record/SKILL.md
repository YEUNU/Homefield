---
name: decision-record
description: Record a design decision or an unconfirmed assumption for the FDE harness as a short ADR in internal/decisions/. Use when the user and Claude settle a design choice, reject an alternative, or proceed on an assumption that was not confirmed.
---

# Decision Record

결정과 가정을 `internal/decisions/NNNN-<slug>.md`로 남긴다. 번호는 기존 최대값 + 1이다.

## 형식
```markdown
---
status: accepted | assumed | deprecated | superseded
updated: YYYY-MM-DD
audience: internal
---
# NNNN. <제목>
- 영향 범위: 코어 | 어댑터 | 도메인 팩 | eval | P1–P5

## 맥락
<왜 결정이 필요했는가. 2–4문장.>

## 후보
| 후보 | 근거 | 신뢰도 |
|---|---|---|

## 결정
<한 문장.>

## 결과·재검토 조건
<무엇이 바뀌면 다시 본다.>
```

## 규칙
- 사용자가 확인하지 않은 선택은 상태를 `assumed`로 둔다. (불확실성 원장과 같은 원칙.)
- 근거에는 출처(논문·문서 링크)를 붙인다. 재현되지 않은 수치는 "(미재현)"으로 표시한다.
- 기존 결정을 뒤집으면 새 문서를 만들고, 옛 문서 상태를 `superseded`로 바꾼다.
