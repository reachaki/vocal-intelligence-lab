# Audits

This folder stores independent technical review notes for the project.

Each review examines a specific implementation phase or pushed change and records an objective assessment. A review checks:

- implementation quality and correctness
- validation evidence (tests, synthetic checks, and real-audio checks where applicable)
- risks and known limitations
- readiness for the next phase

## Conventions

- One review note per reviewed change, named `YYYY-MM-DD-<short-sha>-review.md`.
- Each note records the reviewed commit, the checks run, the findings, and a verdict of **pass**, **pass with notes**, or **fail**.
- Review notes are documentation only. They do not modify implementation code, tests, or configuration.

Reviews are recorded here so that progress and quality decisions stay transparent and traceable over time.
