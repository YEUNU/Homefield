"""Customer simulator: what it is told (the model call is replaced). No network."""

from evalkit import customer


def test_facts_become_one_line_per_clause_and_broad_questions_get_no_fact(monkeypatch):
    seen = {}

    def chat(messages, **kwargs):
        seen["system"], seen["kwargs"] = messages[0]["content"], kwargs
        return " Full name means first, middle, last. "

    monkeypatch.setattr(customer.llm, "chat", chat)
    task = {"hidden": {"facts": ["full name = first, middle, last; via fax refers to \"Submitted via\" = 'fax';"]}}
    ask = customer.make_customer(task)
    assert ask('What do you mean by "full name"?') == "Full name means first, middle, last."
    facts = seen["system"].split("Facts:\n")[1]
    assert facts == "- full name = first, middle, last\n- via fax refers to \"Submitted via\" = 'fax'"
    assert "Please ask about a specific term or condition." in seen["system"]
    assert seen["kwargs"]["temperature"] == 0.0 and seen["kwargs"]["thinking"] is False
