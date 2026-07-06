"""Framework-Specific Worker Prompts.

Provides conversion rules for each supported framework.
These rules are injected into worker agent prompts to guide
HTML-to-framework code conversion.
"""

import os
import importlib.util

# Import framework_config without triggering agent __init__
_spec = importlib.util.spec_from_file_location(
    "framework_config",
    os.path.join(os.path.dirname(__file__), "framework_config.py"),
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

FrameworkType = _mod.FrameworkType
StylingType = _mod.StylingType


BASE_WORKER_INSTRUCTIONS = """You are an expert web developer. Your task is to convert extracted
website content (HTML, CSS, visual data) into clean, functional code
in the target framework. You must:

1. Preserve the visual appearance as closely as possible
2. Use semantic HTML and accessible markup
3. Extract actual text content from the page
4. Identify colors, fonts, spacing, and layout
5. Recreate responsive behavior
6. Write clean, maintainable code

IMPORTANT: Output ONLY valid code files. No explanations outside comments.
"""


def get_framework_worker_prompt(framework: FrameworkType, styling: StylingType) -> str:
    """Build complete worker prompt for a given framework and styling."""
    base = BASE_WORKER_INSTRUCTIONS
    framework_rules = get_framework_specific_rules(framework)
    styling_rules = get_styling_rules(styling)

    return f"""{base}

{framework_rules}

{styling_rules}
"""


def get_framework_specific_rules(framework: FrameworkType) -> str:
    """Get framework-specific conversion rules."""
    rules = {
        "react": _react_rules(),
        "vue": _vue_rules(),
        "svelte": _svelte_rules(),
        "astro": _astro_rules(),
        "html": _html_rules(),
        "nextjs": _nextjs_rules(),
    }
    # Handle both enum and string
    key = framework.value if hasattr(framework, 'value') else framework
    return rules[key]


def get_styling_rules(styling: StylingType) -> str:
    """Get styling-specific rules."""
    rules = {
        "tailwind": _tailwind_styling_rules(),
        "css_modules": _css_modules_styling_rules(),
        "plain_css": _plain_css_styling_rules(),
    }
    # Handle both enum and string
    key = styling.value if hasattr(styling, 'value') else styling
    return rules[key]


def _react_rules() -> str:
    return """## REACT CONVERSION RULES

File Structure:
- Components: src/components/ComponentName.jsx
- Pages: src/pages/PageName.jsx
- Styles: src/styles/ (CSS files or CSS Modules)
- Entry: src/main.jsx

JSX Syntax:
- class -> className
- for -> htmlFor
- Self-close empty elements: <img />, <br />, <input />
- Inline styles: style={{ camelCase: 'value' }}
- Boolean attributes: disabled={true} not disabled="true"
- Event handlers: onClick, onChange, onSubmit (camelCase)
- JavaScript expressions in curly braces: {variable}

Component Patterns:
- Functional components with hooks
- useState for local state
- useEffect for side effects
- useContext for global state
- Props destructuring: function Component({ prop1, prop2 })
- Export default at end of file

Import Order:
1. React imports
2. Third-party libraries
3. Local components
4. Styles

Code Quality:
- PropTypes or TypeScript for type checking
- Avoid inline styles when possible
- Extract reusable components
- Use descriptive variable names
"""


def _vue_rules() -> str:
    return """## VUE 3 CONVERSION RULES

File Structure:
- Components: src/components/ComponentName.vue
- Pages: src/views/PageName.vue
- Styles: <style scoped> in .vue files
- Entry: src/main.js

Single File Component Structure:
<template>
  <!-- HTML template -->
</template>

<script setup>
// Composition API
</script>

<style scoped>
/* Scoped styles */
</style>

Template Syntax:
- Dynamic attributes: v-bind:attr or :attr
- Event handlers: v-on:event or @event
- Conditional: v-if / v-else-if / v-else
- List rendering: v-for="item in items" :key="item.id"
- Two-way binding: v-model
- Text interpolation: {{ variable }}
- Raw HTML: v-html (use cautiously)

Composition API:
- ref() for reactive primitives
- reactive() for reactive objects
- computed() for derived state
- watch() / watchEffect() for side effects
- onMounted(), onUnmounted() lifecycle hooks
- defineProps() for props
- defineEmits() for events

Best Practices:
- Use <script setup> syntax (no setup() return)
- Use ref() over reactive() for primitives
- Destructure props with toRefs()
- Use shallowRef() for large objects
"""


def _svelte_rules() -> str:
    return """## SVELTE 4 CONVERSION RULES

File Structure:
- Components: src/lib/components/ComponentName.svelte
- Pages: src/routes/ (if using SvelteKit)
- Styles: <style> in .svelte files (scoped by default)
- Entry: src/main.js

Template Syntax:
- Expressions: {expression}
- Conditional: {#if condition} ... {:else if} ... {:else} ... {/if}
- Each loop: {#each items as item (item.id)} ... {/each}
- Await: {#await promise} ... {:then value} ... {:catch error} ... {/await}
- HTML: {@html content}
- Events: on:click={handler}
- Binding: bind:value={variable}
- Refs: bind:this={element}

Reactive Declarations:
- $: doubled = count * 2 (auto-reactive)
- export let prop (props)
- $: console.log(count) (reactive effect)

Stores:
- import { writable, readable, derived } from 'svelte/store'
- $storeName (auto-subscribed)

Lifecycle:
- onMount(() => { ... })
- onDestroy(() => { ... })
- afterUpdate(() => { ... })

Props and Events:
- export let propName (props)
- createEventDispatcher() for events
- on:click={handleClick}

Styles:
- Scoped by default
- :global() for global styles
- CSS variables supported
"""


def _astro_rules() -> str:
    return """## ASTRO CONVERSION RULES

File Structure:
- Pages: src/pages/index.astro
- Layouts: src/layouts/Layout.astro
- Components: src/components/ComponentName.astro
- Styles: <style> in .astro files or global CSS

Frontmatter (between ---):
---
// JavaScript/TypeScript runs on server
import Component from '../components/Component.astro';
const title = "Page Title";
---

Template:
- HTML with template syntax: {expression}
- Conditional: {condition && <element>}
- Maps: {items.map(item => <element />)}
- Slots: <slot /> for content projection
- Props: interface Props { title: string }

Hydration Directives (for interactive components):
- client:load - Hydrate immediately
- client:idle - Hydrate when browser idle
- client:visible - Hydrate when scrolled into view
- client:media={query} - Hydrate at breakpoint
- client:only="react" - Skip SSR, client-only
- client:tooltip="react" - Hydrate on hover

Islands Architecture:
- Static HTML by default (fast!)
- Only interactive components need client: directives
- Framework components: React, Vue, Svelte, Solid
- Use .astro for layout and static content

Layout Pattern:
---
interface Props { title: string; }
const { title } = Astro.props;
---
<html>
  <head><title>{title}</title></head>
  <body><slot /></body>
</html>

Data Fetching:
- fetch() in frontmatter (server-side)
- Astro.glob() for local files
- getStaticPaths() for dynamic routes
"""


def _html_rules() -> str:
    return """## PLAIN HTML/CSS/JS CONVERSION RULES (NO FRAMEWORK)

File Structure:
- index.html (entry point)
- src/style.css (styles)
- src/main.js (JavaScript)
- src/components/ (optional JS modules)

HTML5 Semantic Elements:
- <header> for page/section headers
- <nav> for navigation
- <main> for primary content
- <article> for independent content
- <section> for thematic grouping
- <aside> for sidebar content
- <footer> for page/section footers
- <figure> + <figcaption> for images
- <details> + <summary> for accordions

CSS Best Practices:
- CSS custom properties for theming:
  :root { --primary: #3b82f6; --bg: #ffffff; }
- CSS Grid for layout: display: grid; grid-template-columns: ...
- Flexbox for alignment: display: flex; align-items: center;
- Media queries for responsive: @media (max-width: 768px)
- Transitions for animations: transition: all 0.3s ease;
- Use rem/em over px for typography

JavaScript (Vanilla):
- document.querySelector() / querySelectorAll()
- element.addEventListener('click', handler)
- element.classList.add/remove/toggle()
- fetch() for API calls
- IntersectionObserver for scroll effects
- template literals for dynamic HTML
- data-* attributes for state

Performance:
- Lazy load images: loading="lazy"
- Preload critical fonts: <link rel="preload">
- Minimize DOM manipulation
- Use event delegation
- Debounce/throttle event handlers

Accessibility:
- ARIA labels and roles
- Alt text for images
- Keyboard navigation
- Focus management
- Color contrast (WCAG AA)
"""


def _nextjs_rules() -> str:
    return """## NEXT.JS CONVERSION RULES

File Structure:
- App Router: app/ directory
- Pages Router: pages/ directory
- Components: src/components/
- Styles: src/styles/ or Tailwind
- Public assets: public/

App Router (Recommended):
- app/layout.tsx - Root layout (required)
- app/page.tsx - Home page
- app/about/page.tsx - /about route
- app/blog/[slug]/page.tsx - Dynamic route
- app/loading.tsx - Loading UI
- app/error.tsx - Error boundary
- app/not-found.tsx - 404 page

Server vs Client Components:
- Server Components (default):
  - Fetch data directly
  - Access backend resources
  - Keep sensitive data on server
  - No useState/useEffect

- Client Components ("use client"):
  - Interactive UI
  - useState, useEffect, useRef
  - Browser APIs
  - Event handlers

Data Fetching:
- Server: async function fetchData() { await fetch(url) }
- Server Actions: "use server" for form handlers
- Loading: export const revalidate = 60 (ISR)

Image Optimization:
- import Image from 'next/image'
- <Image src="/hero.png" width={800} height={600} alt="Hero" />

Font Optimization:
- import { Inter } from 'next/font/google'
- const inter = Inter({ subsets: ['latin'] })

Metadata:
- export const metadata = { title: 'Page', description: '...' }
- Or generateMetadata() for dynamic

Route Handlers:
- app/api/route.ts for API routes
- GET, POST, PUT, DELETE exports
"""


def _tailwind_styling_rules() -> str:
    return """## TAILWIND CSS RULES

Utility-First Approach:
- Use Tailwind utility classes directly in HTML/JSX
- Minimal custom CSS (only for complex animations)
- Responsive: sm:, md:, lg:, xl:, 2xl:
- Hover/focus states: hover:, focus:, active:

Common Patterns:
- Layout: flex, grid, block, inline
- Spacing: p-*, m-*, gap-*, space-*
- Typography: text-*, font-*, leading-*, tracking-*
- Colors: bg-*, text-*, border-* (use design tokens)
- Borders: rounded-*, border-*
- Shadows: shadow-*
- Transitions: transition-, duration-*, ease-*

Responsive Design:
- Mobile-first: base styles + sm/md/lg breakpoints
- Container: container mx-auto
- Grid: grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3

Dark Mode:
- dark: prefix for dark theme
- Example: bg-white dark:bg-gray-900

Customization:
- Extend tailwind.config.js for brand colors
- Add custom utilities if needed
- Use @apply sparingly in global CSS
"""


def _css_modules_styling_rules() -> str:
    return """## CSS MODULES RULES

File Naming:
- ComponentName.module.css
- Import: import styles from './ComponentName.module.css'

Usage:
- <div className={styles.container}>
- <p className={styles.text + ' ' + styles.highlight}>

Benefits:
- Scoped class names (no conflicts)
- Type-safe with TypeScript
- Composable with :global()

Patterns:
- composes: from './other.module.css'
- :global(.class) for global styles
- CSS variables for theming

Best Practices:
- Keep styles close to components
- Use descriptive class names
- Extract shared styles to common modules
- Combine with CSS custom properties for theming
"""


def _plain_css_styling_rules() -> str:
    return """## PLAIN CSS RULES

File Naming:
- ComponentName.css or styles.css
- Import in main entry point

Architecture:
- BEM naming: .block__element--modifier
- CSS custom properties for theming
- Logical property grouping

Organization:
/* Variables */
:root { --primary: #3b82f6; }

/* Reset */
*, *::before, *::after { box-sizing: border-box; }

/* Base */
body { margin: 0; font-family: system-ui; }

/* Components */
.card { ... }
.card__title { ... }

/* Utilities */
.visually-hidden { ... }

/* Responsive */
@media (max-width: 768px) { ... }

Best Practices:
- Mobile-first media queries
- Use rem for font sizes
- Flexbox/Grid for layout
- Transitions for animations
- Avoid !important
- Minimize specificity wars
"""
