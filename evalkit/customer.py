"""Customer simulator: answers using only the hidden facts. It does not know the gold SQL or result."""

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
        # Fix the simulator so it gives the same answer to the same question (it is not under evaluation).
        return llm.chat(messages, model=model, temperature=0.0, thinking=False).strip()

    return simulate
