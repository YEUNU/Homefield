# Homefield

Homefield is an agent harness for Forward Deployed Engineer (FDE) workflows. The goal is not to replace the FDE. The goal is to increase the throughput of one FDE.

This repository has two parts:

- **The harness core (`homefield/`).** The current stage is M0: a model-independent tool-call loop.
- **The harness comparison tool (`evalkit/`).** It changes only the harness and keeps the model the same. It measures how little interaction cost a harness needs to solve an ambiguous data-analysis request.

## Documents
- Evaluation protocol: [docs/EVALUATION.md](docs/EVALUATION.md)
- Connecting comparison harnesses: [docs/HARNESSES.md](docs/HARNESSES.md)
- Test datasets: [docs/DATASETS.md](docs/DATASETS.md)
- Rules for documents, code, experiments, Git, and release: [docs/RULES.md](docs/RULES.md)

## Getting started
```bash
git config core.hooksPath .githooks
cp .env.example .env        # address and key of an OpenAI-compatible LLM server
scripts/check_llm.sh        # check the connection
scripts/ci.sh              # local CI (ruff, pytest, rules, gitleaks)
python3 -m evalkit.run --task tasks/smoke-revenue --harness bare
python3 -m homefield -p "<task>"   # standalone run
```

## License
[LICENSE](LICENSE)
