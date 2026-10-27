# Taste

## Code changes

- Prefers additive, minimal edits: when adding functionality, do not modify or refactor existing logic — add only what is needed and leave prior code untouched. Confidence: 0.85

## Workflow

- Prefers incremental/progressive persistence: save results to disk after each completed unit of work (write combination-by-combination) rather than accumulating everything and saving once at the end. Confidence: 0.75
- Wants requirements reviewed/confirmed back before implementation starts, rather than jumping straight to writing code. Confidence: 0.65
- Prefers the agent to actually run and trace the code to diagnose problems empirically, rather than guessing at causes/selectors from static reasoning. Confidence: 0.7
- Wants work done quickly with only the necessary tests — favors a single focused run over exhaustive probing/coverage. Confidence: 0.7
