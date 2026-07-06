# Pattern Classification — OSS Mining → Codebase Gaps

## Pattern 1: Prompt-Per-Stack Injection (screenshot-to-code) → HIGHEST VALUE
**Applies to:** worker_agent.py (both agent/ and boxlite/)
**Current state:** Workers are told "You are an HTML → JSX CONVERTER"
**Target state:** Workers receive framework-specific conversion rules from framework_config

## Pattern 2: Spec Files as Intermediate Representation (ai-website-cloner) → MEDIUM VALUE
**Applies to:** task_contract.py → code generation bridge
**Current state:** TaskContract contains everything inline
**Target state:** Extract component specs into framework-agnostic intermediate format

## Pattern 3: File Extension Resolution via Config (GPT-Engineer style) → HIGHEST VALUE
**Applies to:** All file path generation (mcp_tools, task_contract, boxlite worker)
**Current state:** .jsx hardcoded in 20+ locations
**Target state:** All file paths use framework_config.file_extension
