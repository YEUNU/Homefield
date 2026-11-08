"""고객 시뮬레이터: 숨은 사실만 알고 답한다. 정답 SQL·결과는 모른다."""

from homefield import model as llm

SYSTEM = """You role-play a business customer who asked a data analyst for a report.
You know ONLY the facts below. Rules:
- Answer the analyst's question briefly (1-2 sentences), in the same language as the question.
- Use only the facts. If the facts do not cover the question, reply exactly: I don't know.
- Answer only what was asked. Do not volunteer other facts.
- Never write SQL, never name tables or columns unless the analyst named them first.

Facts:
{facts}"""


def make_customer(task: dict, model: str = llm.DEFAULT_MODEL):
    system = SYSTEM.format(facts="\n".join(f"- {f}" for f in task["hidden"]["facts"]))

    def simulate(question: str) -> str:
        messages = [{"role": "system", "content": system}, {"role": "user", "content": question}]
        # 시뮬레이터는 같은 질문에 같은 답을 하도록 고정한다 (평가 대상이 아니다).
        return llm.chat(messages, model=model, temperature=0.0, thinking=False).strip()

    return simulate
