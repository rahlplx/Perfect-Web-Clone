# OSS Reverse Engineering: Framework-Agnostic Code Generation Patterns

**Date:** 2026-07-07
**Scope:** 8 OSS projects analyzed for multi-framework code generation patterns
**Relevance:** Patterns applicable to Perfect Web Clone's worker-agent prompt injection, file extension resolution, package.json generation, and template systems

---

## 1. Screenshot-to-Code (abi/screenshot-to-code)
- **URL:** https://github.com/abi/screenshot-to-code
- **Stars:** 73k+
- **License:** MIT
- **Architecture:** FastAPI backend + React/Vite frontend + LLM prompt pipeline

### How They Handle Multi-Framework Code Generation
Uses **prompt-per-stack** pattern: a single `SYSTEM_PROMPT` string with conditional `# Stack-specific instructions` sections. The user picks a stack (HTML+Tailwind, React+Tailwind, Vue+Tailwind, Bootstrap, Ionic), and the prompt is conditionally assembled to inject the correct CDN scripts, component patterns, and conventions.

**Key pattern — conditional prompt injection:**
```python
SYSTEM_PROMPT = """
## Stack-specific instructions

## Tailwind
- Use this script: <script src="https://cdn.tailwindcss.com"></script>

## React
- Use these scripts: React 18 UMD + Babel standalone
- For JSX, use the babel standalone transform

## Vue
- Use: Vue 3 global build
- Pattern: const { createApp, ref } = Vue

## Bootstrap
- Use: bootstrap CSS CDN
"""
```

### Patterns Applicable to Our Codebase
- **Prompt-per-stack model**: Each framework variant gets its own prompt section with exact conventions, imports, and script tags
- **Stack-specific CDN/package injection**: Scripts and dependencies are injected conditionally per stack choice
- **CDN-first for zero-config**: All stacks are loaded via CDN UMD builds so generated code runs standalone
- **Babel/transform logic per stack**: React needs Babel for JSX, Vue doesn't — each stack declares its transform requirements

### Source reference
- `backend/prompts/system_prompt.py` — the full 200+ line system prompt with stack-specific blocks
- `backend/prompts/__init__.py` — exports the prompt

---

## 2. Open Lovable (firecrawl/open-lovable)
- **URL:** https://github.com/firecrawl/open-lovable
- **Stars:** 27k+
- **License:** MIT
- **Architecture:** Next.js app + Firecrawl scraping + AI providers (Claude/GPT/Gemini/Groq) + E2B sandbox

### How They Handle Website-to-Code Conversion
The tool is **React-only (hardcoded stack)** — it clones any URL into a React/Next.js app. The architecture is:

1. **Firecrawl API** scrapes the target URL extracting all HTML, CSS, JS
2. **AI Provider** (user chooses) interprets the scraped content and generates React components
3. **E2B Sandbox** (optional) runs generated code in isolation
4. **Fast Apply** (MorphLLM) for rapid iterative edits

### Patterns Applicable to Our Codebase
- **Scraper-then-generate pipeline**: Extract the source DOM structure first, *then* feed to LLM for code generation — separates concerns
- **Multiple AI provider support**: Abstracted provider layer lets users choose cost/quality tradeoffs
- **Sandboxed execution**: Generated code runs in isolated sandbox before deployment
- **File-based project generation**: Each component gets its own file with proper imports — not a single HTML blob

### Source reference
- `app/page.tsx` — main UI (892 lines, chat interface)
- `lib/ai/` — AI provider abstractions
- `lib/sandbox/` — sandbox execution layer
- `lib/build-validator.ts` — build validation

---

## 3. AI Website Cloner Template (JCodesMore/ai-website-cloner-template)
- **URL:** https://github.com/JCodesMore/ai-website-cloner-template
- **Stars:** 26k+
- **License:** MIT
- **Architecture:** Pre-scaffolded Next.js 16 + shadcn/ui + Tailwind v4 + agent skill (`.claude/skills/clone-website/SKILL.md`)

### How It Handles Multi-Framework Code Generation
This project is **single-framework (Next.js 16)** but what's revolutionary is the **agent-as-orchestrator pattern**:

1. **Agent skill** defines a multi-phase pipeline as executable instructions
2. Phase 1: **Reconnaissance** — Chrome MCP screenshots, `getComputedStyle()` extraction, interaction sweep
3. Phase 2: **Foundation** — fonts, colors, globals, asset downloads
4. Phase 3: **Component Specs** — writes detailed `*.spec.md` files with exact CSS values
5. Phase 4: **Parallel Build** — dispatches sub-agents in git worktrees, one per section
6. Phase 5: **Assembly & QA** — merges worktrees, visual diff against original

**Key innovation — spec files as intermediate representation:**
Each component gets a `docs/research/components/<name>.spec.md` file containing:
- Exact `getComputedStyle()` values (not approximations)
- DOM structure (element tree)
- States & behaviors (scroll-driven, click-driven, hover states)
- Per-state content (for tabs, carousels, etc.)
- Asset references (images, icons, fonts)
- Responsive behavior at 3 breakpoints

### Patterns Applicable to Our Codebase
- **Spec files as a universal intermediate format**: Components are described in a framework-agnostic `.spec.md` before any code is generated. The spec could be fed to different code generators for different frameworks
- **getComputedStyle() extraction script**: A reusable JS snippet that extracts ALL CSS properties from any DOM element — this is framework-agnostic by nature
- **Parallel builder dispatch in worktrees**: Each section gets its own isolated builder agent, enabling parallelism
- **Interaction model detection**: Explicitly identifies scroll-driven vs click-driven vs time-driven interactivity BEFORE building
- **Asset-first extraction**: Images, SVGs, fonts are downloaded before any code generation begins
- **Multi-platform agent support**: Same skill file synced to `.claude/`, `.cursor/`, `.codex/`, `.opencode/`, `.windsurf/`, `.continue/`, `.gemini/`

### Source reference
- `.claude/skills/clone-website/SKILL.md` — 473-line skill definition (full pipeline)
- `AGENTS.md` — project instructions for AI agents
- `scripts/sync-skills.mjs` — cross-platform skill syncing
- `scripts/sync-agent-rules.sh` — cross-platform agent rule syncing

---

## 4. GPT-Engineer (AntonOsika/gpt-engineer)
- **URL:** https://github.com/gpt-engineer-org/gpt-engineer
- **Stars:** 55k+
- **License:** MIT
- **Architecture:** Python CLI + LLM + preprompt system

### How It Handles Multi-Framework Code Generation
Uses a **preprompt system** — text files that define the AI agent's behavior. The key prompt is `generate`:

```
Think step by step and reason yourself to the correct decisions...
You will start with the "entrypoint" file, then go to the ones that are 
imported by that file, and so on.
...
Follow a language and framework appropriate best practice file naming convention.
Make sure that files contain all imports, types etc.
Include module dependency or package manager dependency definition file.
```

Framework specificity is handled through:
1. **Natural language in the prompt** — user describes the framework in their `prompt` file
2. **Preprompt customization** — users can override `preprompts/` folder with framework-specific versions (`--use-custom-preprompts`)
3. **Convention-based file naming** — prompt says "follow framework appropriate best practice file naming convention"

### Patterns Applicable to Our Codebase
- **Prompt-as-configuration**: The entire generation behavior is defined by text prompts, not code — enabling per-framework customization without code changes
- **Entrypoint-first, dependency-later file ordering**: Start with the entrypoint file, then files it imports, recursive
- **Package manifest generation**: Explicit instruction to "Include module dependency or package manager dependency definition file"
- **Self-validation**: "Before you finish, double check that all parts of the architecture is present in the files"

### Source reference
- `gpt_engineer/preprompts/generate` — the core code generation prompt
- `gpt_engineer/preprompts/` — directory of all preprompts (clarify, spec, respec, fix_code, etc.)

---

## 5. Telosys Code Generator
- **URL:** https://www.telosys.org/
- **Stars:** N/A (non-GitHub tool)
- **License:** OSS
- **Architecture:** Java CLI + Velocity templates + model files (JSON/DB)

### How It Handles Multi-Framework Code Generation
Uses a **template-engine pattern**: models are defined as text files (from DB or JSON), and code is generated by applying Velocity templates. The templates are framework-specific:

```
Model (DB tables / JSON) → Template (Velocity) → Output (any language/framework)
```

**Key aspects:**
- Templates are plain text files, one per output artifact
- "No lock in" — templates can be used for bootstrapping or full lifecycle
- Supports Java, JavaScript, Python, Node.js, PHP, Go, C#, Angular, Vue, React
- Model created from database tables or JSON documents

### Patterns Applicable to Our Codebase
- **Model-template separation**: The "what" (model/data) is separated from the "how" (template/framework) — perfect for multi-framework generation
- **Template libraries per framework**: Maintain a library of templates for each target framework
- **DB-first model generation**: Can derive models from existing database schemas

---

## 6. Yellicode
- **URL:** https://www.yellicode.com/
- **Stars:** N/A
- **License:** OSS (MIT-like)
- **Architecture:** Node.js CLI + TypeScript templates

### How It Handles Multi-Framework Code Generation
Uses **TypeScript-as-template-engine**: templates are written in TypeScript and use the Yellicode API to generate output. Models are JSON documents.

**Key aspects:**
- Templates are TypeScript files (type-safe code generation)
- Cross-platform (Node.js)
- Extensible via NPM packages
- Can target any programming language or framework
- Uses JSON models for input data

### Patterns Applicable to Our Codebase
- **TypeScript for templates**: Using the same language for both templates and generated code
- **NPM-based template distribution**: Templates as packages for sharing and versioning

---

## 7. TabbyML / Continue.dev
- **Tabby:** https://www.tabbyml.com/ — self-hosted AI code completion
- **Continue:** https://continue.dev/ — open-source AI code assistant (26k+ stars)

### How They Handle Multi-Framework Code Completion
**Tabby** uses a repository-level context engine that:
1. Indexes the entire codebase at clone time
2. Computes code embeddings for cross-file context
3. Serves completion via an open-weight model (StarCoder-based)
4. Framework awareness comes from the model's training data, not explicit framework configs

**Continue** uses a different approach:
- **Model-agnostic architecture** — supports 50+ AI models
- **Context providers** — plugins that inject codebase context (files, directories, git, web)
- **.prompt files** — custom prompt templates for different tasks (e.g., `/test`, `/review`, `/explain`)
- **Agent Mode** — writes multi-file changes autonomously

### Patterns Applicable to Our Codebase
- **Repository-level indexing** (Tabby): Pre-index the codebase before generating code to ensure cross-file consistency
- **.prompt files** (Continue): Declarative prompt templates stored alongside code, version-controlled
- **Context providers** (Continue): Pluggable context from different sources (files, git, issues, web)
- **Model-agnostic provider layer** (Both): Abstract the LLM provider so users can swap between local/free/paid models

---

## 8. OpenAI Code Generation (Codex / GPT-5.5)
- **URL:** https://developers.openai.com/api/docs/guides/code-generation
- **Paper:** CodeGen (Salesforce) — arXiv:2203.13474

### Pattern — Multi-Turn Program Synthesis (CodeGen approach)
The CodeGen paper introduced a **multi-turn decomposition** pattern:
1. A single problem is broken into subproblems
2. Each subproblem is solved in a separate turn
3. Context carries over between turns
4. Results are composed into the final solution

This is the **theoretical foundation** for the agent-dispatch pattern that ai-website-cloner-template uses.

### Patterns Applicable to Our Codebase
- **Multi-turn decomposition**: Break complex site generation into sub-tasks (hero ↔ features ↔ footer), solve each in a separate LLM turn, compose results
- **Function-calling based tool use**: Codex's function calling to interact with filesystem, git, browser

---

# Top 3 Patterns We Should Adopt

## Pattern 1: Prompt-Per-Stack Injection (from screenshot-to-code)
**What:** Maintain a single generation prompt with conditional `## Stack-specific instructions` sections. When a user selects a target framework, inject only that framework's conventions, imports, CDN scripts, and file naming rules.

**Where to apply:** Worker agent prompt construction  
**File suggestion:** `src/generator/prompts/stacks/` with files like `react.prompt.md`, `vue.prompt.md`, `angular.prompt.md`, `svelte.prompt.md`

```markdown
## Stack: React
- File extensions: .tsx, .ts
- Component pattern: named exports, PascalCase
- Styling: CSS modules or Tailwind (user choice)
- Entry: src/App.tsx
- Package: react, react-dom, typescript, @types/react

## Stack: Vue
- File extensions: .vue, .ts
- Component pattern: SFC <script setup>
- Styling: scoped <style> blocks
- Entry: src/App.vue
- Package: vue, vue-router, typescript
```

## Pattern 2: Spec Files as Intermediate Representation (from ai-website-cloner-template)
**What:** Before generating any code, extract the source website into a structured `.spec.md` file that describes every component's exact CSS values, DOM structure, states, behaviors, and content. This spec file is framework-agnostic. Then feed it to a framework-specific code generator.

**Where to apply:** Extraction pipeline → Code generation bridge  
**File suggestion:** `src/extraction/spec-writer.ts` and `src/generation/spec-reader.ts`

```
Source URL → Firecrawl/HTTrack → DOM analysis → Spec file (spec.md) → Framework-specific generator → Code
```

The spec file format:
```markdown
# HeroSection Specification

## Computed Styles
- Container: display: flex, padding: 80px 24px, maxWidth: 1200px
- Heading: fontSize: 48px, fontWeight: 700, color: #1a1a1a
- Button: borderRadius: 8px, background: #0066ff, color: #ffffff

## States
- Button hover: background: #0052cc, transition: all 0.2s ease

## Responsive
- Desktop (>1024px): side-by-side layout
- Mobile (<768px): stacked layout, heading 32px

## Assets
- hero-bg.jpg (public/images/)
- logo.svg (as React component from public/icons/)
```

## Pattern 3: Parallel Builder Dispatch with Worktrees (from ai-website-cloner-template)
**What:** Each section/component gets its own builder agent in an isolated git worktree. The orchestrator extracts specs for section N while builder agents work on sections 0..N-1. After all complete, merge worktrees and run build validation.

**Where to apply:** Code generation parallelism  
**File suggestion:** `src/orchestration/worktree-manager.ts`

```
Orchestrator
├── Extraction Loop (sequential, top-to-bottom)
│   ├── Spec for Hero (written to file)
│   ├── Spec for Features
│   └── Spec for Footer
│
├── Dispatch Loop (parallel)
│   ├── Builder A → worktree/hero → generates HeroSection.tsx
│   ├── Builder B → worktree/features → generates FeaturesSection.tsx
│   └── Builder C → worktree/footer → generates FooterSection.tsx
│
└── Assembly
    ├── Merge worktrees into main
    ├── Generate page.tsx (imports all sections)
    └── npm run build --verify
```

---

## Additional Learnings

### File Extension Resolution Strategy
Both GPT-Engineer and screenshot-to-code handle framework-specific extensions by **declaring them in the prompt**:
- "Use `.tsx` for React components, `.ts` for utilities"  
- "Use `.vue` for Vue SFCs, `.ts` for composables"

**Our approach:** Maintain a `extension-map.json` per framework:
```json
{
  "react": { "component": ".tsx", "style": ".css", "utility": ".ts" },
  "vue": { "component": ".vue", "style": ".scss", "utility": ".ts" },
  "svelte": { "component": ".svelte", "style": ".css", "utility": ".ts" }
}
```

### Package.json Generation
GPT-Engineer instructs the model to "Include module dependency or package manager dependency definition file". The specific dependencies are framework-dependent and are injected via the stack-specific prompt section.

**Our approach:** Maintain a `dependencies-map.json` per framework:
```json
{
  "react": {
    "dependencies": { "react": "^18", "react-dom": "^18" },
    "devDependencies": { "typescript": "^5", "@types/react": "^18" }
  },
  "vue": {
    "dependencies": { "vue": "^3", "vue-router": "^4" },
    "devDependencies": { "typescript": "^5", "vite": "^5" }
  }
}
```

### Agent Skill Syncing Pattern
The cloner-template's approach of writing the skill in ONE canonical location (`.claude/skills/clone-website/SKILL.md`) and syncing to all other platforms (`.cursor/`, `.opencode/`, `.codex/`, `.windsurf/`) via a script is a powerful pattern for multi-agent compatibility.

**Our approach:** One canonical spec in `docs/agents/skills/clone-website/SKILL.md`, synced via `scripts/sync-skills.mjs` to all platform-specific `.x/skills/clone-website/SKILL.md` locations.

---

## Raw Data Sources

| Project | Key File(s) Analyzed |
|---------|----------------------|
| screenshot-to-code | `backend/prompts/system_prompt.py` |
| open-lovable | `app/page.tsx`, `lib/` directory |
| ai-website-cloner-template | `.claude/skills/clone-website/SKILL.md`, `AGENTS.md` |
| gpt-engineer | `gpt_engineer/preprompts/generate` |
| Telosys | Website docs (telosys.org) |
| Yellicode | Website docs (yellicode.com) |
| TabbyML | tabbyml.com docs |
| Continue.dev | blog.continue.dev, docs |
| OpenAI CodeGen | arXiv:2203.13474, platform docs |
