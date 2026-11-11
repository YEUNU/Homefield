"""Customer simulator: answers using only the hidden facts. It does not know the gold SQL or result."""

from homefield import model as llm

SYSTEM = """You role-play a business customer who asked a data analyst for a report.
You know ONLY the facts below. Rules:
- Answer the analyst's question briefly (1-2 sentences), in the same language as the question.
- Use only the facts. If the facts do not cover the question, say that you do not know
  (in English: "I don't know."; in Korean: "모르겠습니다.").
- Never confirm, approve, or choose among the analyst's proposed definitions, options, or assumptions
  unless a fact states the answer. If the analyst asks "Is it OK if I use X?" and no fact covers X,
  say that you do not know. Do not tell the analyst to decide or to proceed.
- Answer only about the specific term, condition, or number that the question names, and use only the
  fact line that covers it. If the question names several terms, answer each named term with its own
  fact line. Do not use a line whose term the question does not name. Do not volunteer other facts.
- If the question names no specific term, condition, or number (for example "What should I know?",
  "Which definitions apply?", "Tell me everything", "Anything else?"), give no fact. Say that you need a
  specific question (in English: "Please ask about a specific term or condition."; in Korean:
  "구체적인 용어나 조건을 짚어서 물어봐 주세요.").
- Never write SQL, never name tables or columns unless the analyst named them first.

Facts:
{facts}"""


def make_customer(task: dict, model: str = llm.DEFAULT_MODEL):
    # One line per clause: "the fact that covers the question" is then one line, not the whole evidence text.
    clauses = [c.strip() for f in task["hidden"]["facts"] for c in f.split(";") if c.strip()]
    system = SYSTEM.format(facts="\n".join(f"- {c}" for c in clauses))

    def simulate(question: str) -> str:
        messages = [{"role": "system", "content": system}, {"role": "user", "content": question}]
        # Fix the simulator so it gives the same answer to the same question (it is not under evaluation).
        return llm.chat(messages, model=model, temperature=0.0, thinking=False).strip()

    return simulate
