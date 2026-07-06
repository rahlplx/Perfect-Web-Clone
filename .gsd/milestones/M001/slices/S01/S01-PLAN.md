# S01: Reverse Engineering & Audit

## Objective
Mine OSS projects for framework-agnostic code generation patterns. Full backend audit for all React/JSX hardcodes.

## Tasks

### T01: OSS Reverse Engineering — Mine 5+ Projects
Search GitHub for OSS projects solving framework-agnostic code generation
- language-mcp
- web-cloner 
- repo2vec
- codegen-lab
- gpt-engineer
Extract applicable patterns

### T02: Full Backend Audit — React/JSX/JS Reference Scan
Recursive scan of all *.py files in backend/ for:
- "JSX" / "jsx" references
- "React" / "react" references
- "JS" / ".js" hardcoded extensions
- Hardcoded "import React" patterns
Catalog every finding with file:line

### T03: Pattern Classification & Fix Priority
Map OSS patterns to codebase gaps. Assign priority to each finding.
