# Architectural Decisions

## ADR-1: OSS Mining Before Fixing
Mine mature OSS projects first to discover patterns, then apply. Don't fix blind.

## ADR-2: Worker Agent Fallback Refactor
The `worker_agent.py` fallback at line ~769 must be framework-aware. This is the highest-risk change.

## ADR-3: File Extension Dynamic Resolution
All hardcoded `.jsx`/`.tsx` extensions must use `framework_config.file_extension` instead.

## ADR-4: Docstring Sweep
All "JSX" / "React" references in docstrings become framework-agnostic language.
