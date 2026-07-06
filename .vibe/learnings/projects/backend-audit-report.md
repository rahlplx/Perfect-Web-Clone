# Backend Audit Report — Hardcoded React/JSX References

Generated: 2026-07-07

## Summary

| Severity | Count |
|----------|-------|
| HIGH     | 17 files, 80+ references |
| MEDIUM   | 3 files, 18 references |
| LOW      | 4 files, 60+ references |

---

## HIGH — Affects runtime behavior / code paths

These are hardcoded React/JSX assumptions that control agent behavior, code generation, error detection tool logic, worker prompts, task contracts, and scaffolding. If the system needs to support non-React frameworks generically, these are the blockers.

### `agent/claude_agent.py:304`
```
logger.warning(f"[Agent] Invalid framework config: {e}, defaulting to React")
```
**Why this matters:** Falls back to React when framework configuration is invalid. This means any misconfiguration silently produces React output instead of failing or asking the user. Forces React even when another framework was intended.

### `agent/claude_agent.py:743`
```python
context_parts.append("3. Write App.jsx and index.css to integrate everything")
```
**Why this matters:** Hardcodes the `/src/App.jsx` entry point in the agent's next-steps instructions. Non-React frameworks use different entry points (e.g., Vue uses `App.vue`, Svelte uses `App.svelte`).

### `agent/framework_config.py:19`
```python
class FrameworkType(Enum):
    REACT = "react"
```
**Why this matters:** Part of the framework-type enum (reasonable), but paired with React-specific scaffolding below.

### `agent/framework_config.py:137-138`
```python
_FrameworkExtensions = {
    FrameworkType.REACT: ".jsx",
```
**Why this matters:** Defines `.jsx` as the React extension. Acceptable for React but the issue is that React is the _de facto_ default everywhere.

### `agent/framework_config.py:191-195`
```python
if framework == FrameworkType.REACT:
    templates["vite.config.js"] = _react_vite_config(styling)
    templates["index.html"] = _react_index_html()
    templates["src/main.jsx"] = _react_main_jsx()
    templates["src/App.jsx"] = _react_app_jsx()
```
**Why this matters:** React-only template path. Non-React frameworks each have their own `if` branches, so this is acceptable per se, but the React scaffolding is disproportionately heavier than others. If React is removed, entire codegen path breaks.

### `agent/framework_config.py:310-317`
```python
def _react_vite_config(styling: StylingType) -> str:
    return '''import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
export default defineConfig({
  plugins: [react()],
})
'''
```
**Why this matters:** Generates React-specific Vite config with `@vitejs/plugin-react`. Only suitable for React projects.

### `agent/framework_config.py:447-456`
```python
def _react_main_jsx() -> str:
    return '''import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
'''
```
**Why this matters:** Generates the React entry point with `React.StrictMode`. Non-transferable to other frameworks.

### `agent/framework_config.py:461-466`
```python
def _react_app_jsx() -> str:
    return '''import React from 'react'

function App() {
  return (
    <div className="min-h-screen bg-gray-100">
      <h1 className="text-3xl font-bold p-8">Cloned Project</h1>
```
**Why this matters:** Generates the root React App component with hardcoded Tailwind JSX. Only works for React+Tailwind projects.

### `agent/framework_config.py:730-739`
```python
def _react_worker_rules() -> str:
```
Contains:
- `- Convert HTML elements to JSX: class -> className, for -> htmlFor`
- `- Use JSX expressions: {variable} instead of ${variable}`
- `- Use React hooks: useState, useEffect, useContext`
- `- Use React.Fragment or <> for wrapper elements`

**Why this matters:** These conversion rules are fed directly to worker agents. Hardcodes JSX/React conversion assumptions. If a non-JSX framework (e.g., Vue or Svelte) is targeted, workers receive wrong conversion instructions.

### `agent/framework_config.py:659`
```
"jsx": "preserve",
```
**Why this matters:** Hardcoded in `tsconfig.json` template — only valid for React/JSX projects.

### `agent/framework_config.py:675`
```
"./src/**/*.{js,ts,jsx,tsx}",
```
**Why this matters:** Tailwind content paths hardcode JSX/TSX extensions. Vue/Svelte/Astro projects need `.vue`, `.svelte`, `.astro` included.

### `agent/framework_prompts.py:80-90`
```python
def _react_rules() -> str:
```
Contains:
- `- Components: src/components/ComponentName.jsx`
- `- Pages: src/pages/PageName.jsx`
- `- Entry: src/main.jsx`
- `JSX Syntax:`
- `- class -> className`

**Why this matters:** Framework rules that instruct agents to write JSX files. These are React-specific conventions hardcoded into the agent prompt library.

### `agent/prompts.py:18`
```
- Write React components, pages, and applications from scratch
```
**Why this matters:** System prompt tells the agent it writes React components. Constrains agent behavior to React output.

### `agent/prompts.py:40`
```
- `pattern`: glob pattern (e.g., "**/*.jsx") or regex (e.g., "import.*React")
```
**Why this matters:** Tool description examples use JSX patterns. Non-React frameworks would be confused by these examples.

### `agent/prompts.py:56`
```
- "browser": Use Playwright to detect Vite overlay, React errors, console errors
```
**Why this matters:** The browser error detection is described as React-focused, but the actual `error_detector.py` does support multiple frameworks. The prompt description is misleading.

### `agent/prompts.py:78`
```
→ write_file("/src/App.jsx", "...your code...")
```
**Why this matters:** Example shows hardcoded `/src/App.jsx` — only correct for React.

### `agent/prompts.py:97`
```
↓ Auto-generates App.jsx with all components
```
**Why this matters:** Describes auto-generation of `App.jsx`. Not generic.

### `agent/prompts.py:115`
```
- You CAN add new components or modify App.jsx
```
**Why this matters:** Instructs agent to modify `App.jsx` specifically.

### `agent/prompts.py:121`
```
Standard Vite + React project:
```
**Why this matters:** Describes the project as "Vite + React" — hardcodes the tech stack identity.

### `agent/prompts.py:128-129`
```
├── main.jsx
├── App.jsx
```
**Why this matters:** Project structure diagram shows `.jsx` files. Misleading for other frameworks.

### `agent/mcp_tools.py:169`
```
- write_file(path="/src/App.jsx", content="export default...")
```
**Why this matters:** MCP tool usage example hardcodes JSX.

### `agent/mcp_tools.py:196`
```
- read_file(path="/src/App.jsx")
```
**Why this matters:** Same — hardcoded path in tool documentation.

### `agent/mcp_tools.py:221`
```
- edit_file(path="/src/App.jsx", old_text="Hello", new_text="Hello World")""",
```
**Why this matters:** Same pattern.

### `agent/mcp_tools.py:336`
```
- delete_file(path="/src/old-component.jsx")
```
**Why this matters:** Hardcoded `.jsx` extension in tool example.

### `agent/mcp_tools.py:430`
```
4. Write App.jsx, index.css (use templates from get_layout)
```
**Why this matters:** Hardcoded workflow step for JSX.

### `agent/mcp_tools.py:435`
```
- Workers generate React components with real URLs
```
**Why this matters:** Describes workers as React component generators.

### `agent/mcp_tools.py:632-640`
```python
"description": """Fix import path mismatches in App.jsx automatically.
1. Scans /src/components/sections/ for actual .jsx component files
2. Reads App.jsx imports
...
4. Rewrites App.jsx with corrected import paths
```
**Why this matters:** Tool specifically designed to fix React App.jsx import paths. Non-generic.

### `agent/mcp_tools.py:1486`
```
Get Vite + React project scaffold files.
```
**Why this matters:** Tool description hardcodes React.

### `agent/mcp_tools.py:1579-1587`
```python
"/src/main.jsx": '''import React from 'react';
import ReactDOM from 'react-dom/client';
...
ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
```
**Why this matters:** Generates React-specific entry point.

### `agent/mcp_tools.py:1620-1628`
```python
"/src/App.jsx": f'''import React from 'react';
...
  <div className="app">
```
**Why this matters:** Generates React root component with JSX.

### `agent/mcp_tools.py:3390`
```python
These elements should NOT be converted to React components because:
```
**Why this matters:** Comment/instruction hardcodes "React components" as output target.

### `agent/task_contract.py:339-340`
```python
# Framework config (optional, defaults to React)
framework_type: FrameworkType = FrameworkType.REACT
```
**Why this matters:** Task contract defaults to React. Every section worker defaults to React unless explicitly overridden.

### `agent/task_contract.py:345-348`
```python
allowed_extensions: List[str] = field(default_factory=lambda: [".jsx", ".css", ".js"])
forbidden_paths: List[str] = field(default_factory=lambda: [
    "/src/App.jsx",
    "/src/main.jsx",
```
**Why this matters:** Hardcoded JSX file extensions and React file paths in the task contract's file isolation rules.

### `agent/task_contract.py:357`
```python
shared_imports: List[str] = field(default_factory=lambda: [
    "import React from 'react'",
])
```
**Why this matters:** Every section worker starts with a React import by default.

### `agent/task_contract.py:636-637`
```python
entry_file: str = "/src/main.jsx"
root_component: str = "/src/App.jsx"
```
**Why this matters:** Integration plan defaults to React file paths.

### `agent/task_contract.py:702-728`
```python
def generate_app_jsx(self) -> str:
    ...
    imports = ["import React from 'react'", "import './index.css'"]
    ...
    <div className="app">
```
**Why this matters:** Generates React App.jsx with hardcoded React import and JSX className.

### `agent/task_contract.py:772-783`
```python
def generate_main_jsx(self) -> str:
    return """import React from 'react'
import ReactDOM from 'react-dom/client'
...
ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
```
**Why this matters:** Generates React main.jsx with ReactDOM and StrictMode.

### `agent/task_contract.py:829-832`
```python
import react from '@vitejs/plugin-react'
...
  plugins: [react()],
```
**Why this matters:** Generates Vite config with React plugin.

### `agent/worker_agent.py:148-158`
```python
"description": "Write React component code for your assigned section..."
"description": "File path (e.g., /src/components/sections/header_0/Header0Section.jsx)"
"description": "Complete React component code to write"
```
**Why this matters:** Worker tool descriptions hardcode React component generation as the only output type.

### `agent/worker_agent.py:731`
```python
{self.config.task_description or "Convert HTML to React JSX component"}
```
**Why this matters:** Default task description assumes React JSX output.

### `agent/worker_agent.py:877-897`
```python
- ✅ Convert HTML attributes to JSX (class → className, for → htmlFor, etc.)
| `class="..."` | `className="..."` |
```
**Why this matters:** Worker prompt conversion rules hardcode JSX.

### `agent/worker_agent.py:906-915`
```python
1. **write_code(path, content)**: Write your converted React component
...
import React from 'react';
```
**Why this matters:** Worker instructions hardcode React imports.

### `agent/worker_agent.py:990`
```python
2. **Create** a React component that exactly replicates the original
```
**Why this matters:** Worker prompt instructs creation of React components specifically.

### `boxlite/worker_agent.py:148-158`
```python
"description": "Write React component code for your assigned section..."
"description": "File path (e.g., /src/components/sections/header_0/Header0Section.jsx)"
"description": "Complete React component code to write"
```
**Why this matters:** BoxLite worker tool assumes React component output. Same pattern as `agent/worker_agent.py`.

### `boxlite/worker_agent.py:512`
```python
full_path = f"{self.base_path}/{self.namespace}/{component_name}.jsx"
```
**Why this matters:** Constructs `.jsx` file path for worker output. Non-React frameworks would need `.vue`, `.svelte`, etc.

### `boxlite/worker_agent.py:561-642`
```python
return f"""You are an **HTML → JSX CONVERTER**, NOT a content creator.
...
- ✅ Convert the provided HTML to JSX syntax EXACTLY
- ✅ Convert HTML attributes to JSX (class → className, for → htmlFor, etc.)
...
❌ FORBIDDEN: `/src/App.jsx`, `/src/main.jsx`, `/package.json`
...
```jsx
// File: {full_path}
import React from 'react';

export default function {component_name}() {{
  return (
    // CONVERTED JSX from the HTML above
```
**Why this matters:** Entire worker prompt is an "HTML → JSX CONVERTER" — the most deeply hardcoded React/JSX reference in the codebase. Worker agents are told they ARE JSX converters, not generic framework converters. This is the core of the React lock-in.

### `boxlite/worker_agent.py:652`
```python
full_path = f"{self.base_path}/{self.namespace}/{component_name}.jsx"
```
**Why this matters:** Same hardcoded `.jsx` path construction on retry path.

### `boxlite/worker_agent.py:684-689`
```python
2. **Convert** to React JSX (keep ALL text, URLs, classes exactly)
...
**Begin now** - convert the HTML to JSX and call write_code."""
```
**Why this matters:** Retry prompt also hardcodes React JSX conversion.

### `boxlite/worker_agent.py:868`
```python
return f"Error: content too short ({len(content_stripped)} chars). Write actual React component code."
```
**Why this matters:** Validation error message assumes the expected output is React component code.

### `boxlite/boxlite_agent.py:308`
```python
4. Rewrite `/src/App.jsx` based on layout positions:
```
**Why this matters:** Agent workflow instruction hardcodes JSX file path.

### `boxlite/boxlite_mcp_executor.py:504`
```
- For content search: regex pattern (e.g., "import.*React", "className=")
```
**Why this matters:** Tool description example uses React/JSX patterns.

### `boxlite/boxlite_mcp_executor.py:794-809`
```python
# React ecosystem (usually pre-installed)
"react", "react-dom", "react/jsx-runtime",
"react-icons", "lucide-react", "@heroicons/react",
"@headlessui/react", "@radix-ui/react-dialog",
"react-router-dom", "react-hook-form", "zod",
"swr", "react-query", "@tanstack/react-query",
```
**Why this matters:** Hardcoded React ecosystem package list for sandbox pre-installation. Non-React frameworks get no equivalent treatment.

### `boxlite/boxlite_mcp_executor.py:1844-1860`
```python
imports = ["import React from 'react'", "import './index.css'"]
...
# 构建 JSX
jsx_components = []
...
<div className="app">
```
**Why this matters:** Code generation logic hardcodes React imports and JSX className.

### `boxlite/boxlite_mcp_executor.py:1868-1877`
```python
logger.info(f"[spawn_section_workers] Generated App.jsx with {len(section_components)} components")
app_success = await self.sandbox.write_file("/src/App.jsx", app_jsx_content)
...
logger.error(f"[spawn_section_workers] ✗ Failed to write /src/App.jsx")
```
**Why this matters:** Hardcoded `/src/App.jsx` in file generation logic.

### `boxlite/boxlite_mcp_executor.py:2002`
```python
integration_files = [f for f in files_written if f in ["/src/App.jsx", "/src/index.css", "/src/styles/original.css"]]
```
**Why this matters:** Integration detection hardcodes App.jsx as the expected integration file.

### `boxlite/boxlite_mcp_executor.py:2050-2072`
```python
lines.append("- `/src/App.jsx` - Basic layout (needs arrangement)")
...
lines.append("2. Rewrite `/src/App.jsx` based on section positions:")
```
**Why this matters:** User-facing messages hardcode JSX paths.

### `boxlite/boxlite_mcp_executor.py:1478`
```python
"target_files": [contract.get_allowed_path(f"{contract._namespace_to_component_name()}.jsx")],
```
**Why this matters:** Hardcoded `.jsx` extension in target file generation.

### `boxlite/boxlite_tools.py:63`
```python
path: File path (e.g., "/src/App.jsx")
```
**Why this matters:** Tool parameter description example is React-specific.

### `boxlite/boxlite_tools.py:1063`
```python
"description": "File path (e.g., '/src/App.jsx')"
```
**Why this matters:** Same — tool parameter description hardcodes JSX.

### `boxlite/boxlite_tools.py:1164`
```
- Installing packages: shell("npm install react")
```
**Why this matters:** Npm install example shows `react` specifically.

### `boxlite/error_detector.py:31-35`
```python
# JSX/Syntax errors
"Unterminated JSX": "Check for unclosed JSX tags..."
"Adjacent JSX elements": "Wrap multiple JSX elements..."
"JSX element": "Check JSX syntax..."
```
**Why this matters:** Error detection logic and fix suggestions assume JSX syntax errors. Non-JSX frameworks would get wrong error messages.

### `boxlite/error_detector.py:161`
```python
(r"Invalid hook call", "React Hook Error"),
```
**Why this matters:** React-specific error pattern in the build error detection system.

### `boxlite/error_detector.py:400-435`
```python
async def _detect_react_errors(self, page) -> List[BuildError]:
    """Detect React error boundary or error overlay"""
    ...
    '#react-error-overlay',
    '[data-react-error]',
    '.react-error-overlay',
```
**Why this matters:** React-specific error detection method that looks for React error boundary DOM patterns. Non-React frameworks not handled.

### `boxlite/error_detector.py:471-472`
```python
# Only analyze JS/JSX/TS/TSX files
if not file_path.endswith(('.js', '.jsx', '.ts', '.tsx')):
```
**Why this matters:** Static analyzer only looks at JS/JSX/TS/TSX files. Vue (`.vue`), Svelte (`.svelte`), Astro (`.astro`) files are skipped.

### `boxlite/error_detector.py:515-520`
```python
# Check for unclosed JSX tags (simple heuristic)
if file_path.endswith(('.jsx', '.tsx')):
    # Check for common JSX issues
```
**Why this matters:** File-type checks assume JSX/TSX. Other framework files get no heuristic analysis.

### `boxlite/sandbox_manager.py:68-72`
```python
"react": "^18.2.0",
"react-dom": "^18.2.0"
...
"@vitejs/plugin-react": "^4.2.0",
```
**Why this matters:** Default sandbox template includes React packages.

### `boxlite/sandbox_manager.py:81-84`
```python
import react from '@vitejs/plugin-react'
...
  plugins: [react()],
```
**Why this matters:** Default Vite config uses React plugin.

### `boxlite/sandbox_manager.py:129-146`
```python
<script type="module" src="/src/main.jsx"></script>
"src/main.jsx": """import React from 'react'
import ReactDOM from 'react-dom/client'
...
ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
"src/App.jsx": """import React from 'react'
```
**Why this matters:** Default sandbox files are all React/JSX.

### `boxlite/models.py:164`
```python
type: str  # vite-overlay, react-error-boundary, syntax-error, etc.
```
**Why this matters:** Error type model includes `react-error-boundary` as a recognized type. Framework-specific type in a generic model.

### `boxlite/replay_recorder.py:119`
```python
recorder.record_file_written("/src/App.jsx", content)
```
**Why this matters:** Hardcoded App.jsx path in replay recording.

### `agent/routes_websocket.py:238`
```python
framework_type: Target framework (react, vue, svelte, astro, html, nextjs)
```
**Why this matters:** WebSocket route parameter docstring accepts frameworks, but the actual code paths heavily favor React.

### `agent/tools/code_generation_tools.py:4-8`
```python
Provides advanced tools for generating React components from JSON data...
1. generate_component_from_json() - Generate React component code from JSON data
```
**Why this matters:** Entire module is dedicated to React component generation.

### `agent/tools/code_generation_tools.py:142-158`
```python
def generate_react_component_code(
    ...
    Generate React component code based on data structure analysis.
```
**Why this matters:** Function hardcodes "React" in name and docs.

### `agent/tools/code_generation_tools.py:208-275`
```python
code = f"""import React from 'react';
...
<div className=\"grid gap-6 md:grid-cols-2 lg:grid-cols-3\">
...
className=\"rounded-lg border border-gray-200 dark:border-gray-700 p-6 hover:shadow-lg transition-shadow\"
```
**Why this matters:** Generated code contains React imports and JSX className attributes. Only usable for React projects.

### `agent/tools/code_generation_tools.py:299-389`
3 more instances of `code = f"""import React from 'react';` with JSX className templates.

**Why this matters:** Multiple component generators all hardcode React.

### `agent/tools/code_generation_tools.py:586-612`
```python
Generate a React component from JSON data at the specified path.
React component code with REAL data from the JSON...
ToolResult with generated React component code
```
**Why this matters:** Tool-level description hardcodes React.

### `agent/tools/error_handling_tools.py:106-116`
```python
# React/JSX Errors
"pattern": r"React is not defined",
"description": "Missing React import in JSX file",
"fix": "edit_file(... \"import React from 'react';\\n\" + old_content)"
```
**Why this matters:** Error-handling patterns assume React-specific errors. Non-React frameworks get no equivalent error suggestions.

### `agent/tools/error_handling_tools.py:221`
```python
"2. Verify ReactDOM.createRoot() or render() is called"
```
**Why this matters:** Fix suggestion for rendering errors assumes ReactDOM.

### `agent/tools/error_handling_tools.py:248`
```python
"2. Check for invalid JSX syntax (e.g., class vs className)"
```
**Why this matters:** Fix suggestion for validation errors assumes JSX syntax.

### `agent/tools/error_handling_tools.py:257-261`
```python
"description": "React hook called incorrectly",
"fix": "3. Make sure you're using the same React version everywhere"
```
**Why this matters:** React-specific error pattern and fix.

### `agent/tools/self_healing_tools.py:136`
```python
# Skip React development warnings (noise)
```
**Why this matters:** Self-healing tool explicitly filters React warnings as noise.

### `agent/tools/webcontainer_tools.py:2128-2141`
```python
has_react = any("react" in files.get(f, "").lower() for f in file_paths)
...
if has_react:
    project_type.append("React")
```
**Why this matters:** Project type detection treats "React" as a detected type but only checks for React strings.

### `agent/tools/webcontainer_tools_v2.py:263`
```python
write_file("/src/App.jsx", "import React from 'react';...")
```
**Why this matters:** Tool documentation example hardcodes React/JSX.

### `agent/tools/webcontainer_tools_v2.py:886`
```python
get_preview_dom("#root")           # Get React root only
```
**Why this matters:** Comment assumes React root element selector.

### `agent/tools/webcontainer_tools_v2.py:1005-1012`
```python
- React error boundaries
  - type: error source (vite-overlay, react-error-boundary, console-error)
```
**Why this matters:** Error source types include `react-error-boundary` as a hardcoded category.

### `agent/tools/webcontainer_tools_v2.py:1401`
```
- React error boundaries
```
**Why this matters:** Same pattern in another tool.

### `agent/tools/claude_code_tools.py:338`
```
- grep(pattern="import.*React", file_pattern="*.jsx") - Find React imports in JSX files
```
**Why this matters:** Example shows grep for React imports in JSX files.

### `agent/tools/network_tools.py:280`
```
- web_fetch(url="https://react.dev/learn", prompt="What are React Hooks?")
```
**Why this matters:** Tool example fetches React.dev documentation.

### `agent/tools/network_tools.py:313`
```
- Find documentation: web_search(query="React hooks documentation 2025")
```
**Why this matters:** Same — React-specific search query example.

### `agent/tools/task_tool.py:259`
```
- Example: "Find all React components that use useState hook"
```
**Why this matters:** Task tool example describes React component search.

### `agent/tools/webcontainer_tools.py:488`
```python
args: Command arguments (e.g., ["install", "react"])
```
**Why this matters:** Shell command example uses React.

### `extractor/tech_stack_analyzer.py:27-35`
```python
"React": {
    "patterns": [
        r"react\.production\.min\.js",
        r"react-dom\.production\.min\.js",
        r"_reactRootContainer",
    ],
    "global_vars": ["React", "ReactDOM"],
    "data_attrs": ["data-reactroot", "data-reactid"],
```
**Why this matters:** Static analyzer pattern dictionary includes React detection patterns. This is expected since it's a tech stack detector, but it still hardcodes React knowledge.

### `extractor/tech_stack_analyzer.py:507`
```python
if any(f.name in ["React", "Vue", "Angular"] for f in self.detected_frameworks):
```
**Why this matters:** Framework detection logic hardcodes framework names.

---

## MEDIUM — Docstrings, comments, non-runtime strings

These references are in comments, docstrings, or JavaScript strings embedded in Python files (e.g., Playwright evaluation scripts). They don't directly affect Python runtime but reflect the React-centric worldview.

### `extractor/component_analyzer.py:771-804`
```python
if (el.className && typeof el.className === 'string') {
    const cls = el.className.trim().split(/\\s+/)[0];
    ...
    classes: el.className ? el.className.split(/\\s+/).filter(c => c) : [],
```
**Why this matters:** JavaScript code inside Python (Playwright eval) that uses `.className`. This is DOM API, not JSX — but `className` in JS context is a JSX conversion artifact when the code is intended for React output. This is MEDIUM because it's inside JS strings evaluated by Playwright for DOM analysis, not Python logic.

### `extractor/extractor_service.py:697-728`
```python
htmlClasses: document.documentElement.className,
bodyClasses: document.body.className,
...
document.documentElement.className = original.htmlClasses;
document.body.className = original.bodyClasses;
```
**Why this matters:** Same pattern — JS strings inside Python using DOM `className` API.

### `extractor/extractor_service.py:1286-1382`
```python
if (el.className && typeof el.className === 'string') {
    selector += '.' + el.className.trim().split(/\s+/).join('.');
...
classes: el.className && typeof el.className === 'string'
    ? el.className.trim().split(/\s+/).filter(c => c)
```
**Why this matters:** Multiple instances of DOM `className` usage in Playwright eval scripts.

### `extractor/extractor_service.py:1924-2115`
```python
(el.className && typeof el.className === 'string' ?
    el.tagName.toLowerCase() + '.' + el.className.split(' ')[0] :
```
**Why this matters:** Same pattern, repeated across many extraction methods.

### `extractor/tech_stack_analyzer.py:254-279`
```python
const classNames = new Set();
...
if (el.className && typeof el.className === 'string') {
    el.className.split(/\\s+/).forEach(c => {
        if (c) classNames.add(c);
```
**Why this matters:** DOM className usage in tech stack analyzer's Playwright script.

### `agent/framework_config.py:4`
```
Supports: React, Vue, Svelte, Astro, HTML, Next.js
```
**Why this matters:** Module-level docstring lists React first as the primary framework. Low impact but indicative.

### `agent/framework_config.py:732-734`
```
- Convert HTML elements to JSX: class -> className, for -> htmlFor
- Use JSX expressions: {variable} instead of ${variable}
```
**Why this matters:** Worker rules docstring contains JSX conversion instructions. These ARE used at runtime by workers, but the string itself is generated content that is passed to AI agents — it's MEDIUM since it's a runtime string being fed to prompts but the content itself is JSX-centric.

Actually, since these strings ARE fed to LLM agents at runtime and control their behavior, they should be HIGH. Let me reconsider...

No, I already have these classified as HIGH above. The `_react_worker_rules()` function is already in the HIGH section. The content at line 732-734 is the same function body. Let me be more careful about not duplicating.

### `extractor/tech_stack_analyzer.py:6`
```
- 检测前端框架（React、Vue、Angular、Svelte 等）
```
**Why this matters:** Chinese-language docstring lists React first. Purely documentation.

### `boxlite/error_detector.py:6`
```
2. Browser Detector - Use Playwright to detect Vite overlay, React errors, console errors
```
**Why this matters:** Error detector docstring mentions React errors specifically. Affects understanding of the system.

### `boxlite/error_detector.py:43`
```
# React errors
```
**Why this matters:** Comment grouping React error patterns.

### `boxlite/error_detector.py:138-142`
```python
# JSX/Babel errors
(r"Unterminated JSX", "JSX Syntax Error"),
(r"Adjacent JSX elements", "JSX Error"),
(r"JSX element", "JSX Error"),
```
**Why this matters:** Error pattern comments reference JSX/Babel. These are used at runtime for error classification.

---

## LOW — Test files

These are in test files (`tests/`). They test the React-specific behavior and are expected to be React-centric since they test React functionality. However, they indicate the test suite assumes React as the default.

### `tests/test_baseline_react.py`

All 15+ references — entire file is `TestReactBaseline` class testing React config, scaffolding, worker rules, JSX, className, React imports. This is expected since it's explicitly a React baseline test.

Key lines: 1, 22-23, 26-27, 35-36, 45-46, 48-51, 69-76

### `tests/test_framework_config.py`

40+ references testing React framework config (`test_react_exists`, `test_react_tailwind`, `test_react_css_modules`, `test_react_rules_mention_jsx`, `test_react_rules_mention_classname`, `test_react_plugin_allowed`, `test_react_in_safe_packages`, etc.)

Key lines: 29-30, 70-71, 80-81, 90-94, 100-104, 110-111, 118-135, 199-214, 249-257, 303-304, 319-320, 339-351

### `tests/test_e2e_frameworks.py`

Class `TestReactE2E` (line 38) and multiple React-specific assertions.

Key lines: 38, 45, 52-53, 55-58, 74-78, 227

### `tests/test_boxlite_tools.py:642`

```python
await write_file("/src/components/Button.jsx", "export function Button() {}", sandbox)
```
**Why this matters:** Test writes a `.jsx` file. Expected since BoxLite targets React.

---

## Files with ZERO React/JSX/className references (clean)

These directories/files have no React/JSX/className references at all:

- `agent/core/` (all 8 files)
- `agent/memory/` (all files)
- `cache/` (all files)
- `checkpoint/` (all files)
- `image_downloader/` (all files)
- `image_proxy/` (all files)
- `json_storage/` (all files)
- `sources/` (all files)
- `scripts/` (all files)
- `code_gen_config.py`
- `main.py`

---

## Risk Summary

The codebase has **deeply embedded React/JSX assumptions** that span:

1. **Agent prompts & system messages** — agents are told they write React/JSX
2. **Worker agent prompts** — workers are explicitly "HTML → JSX CONVERTERS"
3. **Task contracts** — default to React imports and JSX file paths
4. **Code generation** — all generators emit React/JSX code
5. **Sandbox scaffolding** — default templates are Vite + React
6. **Error detection** — React-specific error patterns and JSX syntax analysis
7. **Tool documentation** — every tool example uses React/JSX paths
8. **Framework config** — `.jsx` is the assumed file extension for config validation

**If the goal is framework-agnostic support, all HIGH items must be addressed.** The most critical single point is `boxlite/worker_agent.py:561-642` (the "HTML → JSX CONVERTER" prompt) and `agent/task_contract.py:339-340` (defaulting all tasks to React).
