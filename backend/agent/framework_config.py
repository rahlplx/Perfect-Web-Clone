"""Framework Configuration Module.

Single source of truth for all framework configurations.
Supports: React, Vue, Svelte, Astro, HTML, Next.js
Styling: Tailwind, CSS Modules, Plain CSS

Security:
- ALLOWED_VITE_PLUGINS: Whitelist of permitted Vite plugins
- KNOWN_SAFE_PACKAGES: Whitelist of permitted packages
- validate_framework_config(): Validates config against allowlists
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional, Any


class FrameworkType(Enum):
    REACT = "react"
    VUE = "vue"
    SVELTE = "svelte"
    ASTRO = "astro"
    HTML = "html"
    NEXTJS = "nextjs"


class StylingType(Enum):
    TAILWIND = "tailwind"
    CSS_MODULES = "css_modules"
    PLAIN_CSS = "plain_css"


@dataclass(frozen=True)
class FrameworkConfig:
    framework: FrameworkType
    styling: StylingType
    file_extension: str
    vite_plugin: Optional[str]
    package_dependencies: Dict[str, Any] = field(default_factory=dict)

    def __hash__(self):
        return hash((
            self.framework,
            self.styling,
            self.file_extension,
            self.vite_plugin,
        ))


ALLOWED_VITE_PLUGINS = frozenset([
    "@vitejs/plugin-react",
    "@vitejs/plugin-vue",
    "@sveltejs/vite-plugin-svelte",
    None,
])

KNOWN_SAFE_PACKAGES = frozenset([
    "react", "react-dom", "@types/react", "@types/react-dom",
    "vue", "@vue/compiler-sfc",
    "svelte", "svelte-check",
    "astro", "@astrojs/tailwind",
    "next", "react", "react-dom",
    "tailwindcss", "postcss", "autoprefixer",
    "typescript", "@types/node",
    "vite",
    "@vitejs/plugin-react", "@vitejs/plugin-vue",
    "@sveltejs/vite-plugin-svelte",
])


_REACT_DEPS = {
    "dependencies": {"react": "^18.2.0", "react-dom": "^18.2.0"},
    "devDependencies": {
        "vite": "^5.0.0",
        "@vitejs/plugin-react": "^4.0.0",
        "@types/react": "^18.2.0",
        "@types/react-dom": "^18.2.0",
    },
}

_VUE_DEPS = {
    "dependencies": {"vue": "^3.4.0"},
    "devDependencies": {
        "vite": "^5.0.0",
        "@vitejs/plugin-vue": "^5.0.0",
        "@vue/compiler-sfc": "^3.4.0",
    },
}

_SVELTE_DEPS = {
    "dependencies": {"svelte": "^4.0.0"},
    "devDependencies": {
        "vite": "^5.0.0",
        "@sveltejs/vite-plugin-svelte": "^3.0.0",
        "svelte-check": "^3.6.0",
    },
}

_ASTRO_DEPS = {
    "dependencies": {"astro": "^4.0.0"},
    "devDependencies": {},
}

_ASTRO_TAILWIND_DEPS = {
    "dependencies": {"@astrojs/tailwind": "^5.0.0"},
    "devDependencies": {},
}

_HTML_DEPS = {
    "dependencies": {},
    "devDependencies": {"vite": "^5.0.0"},
}

_NEXTJS_DEPS = {
    "dependencies": {"next": "^14.0.0", "react": "^18.2.0", "react-dom": "^18.2.0"},
    "devDependencies": {
        "@types/react": "^18.2.0",
        "@types/node": "^20.0.0",
    },
}

_TAILWIND_DEV_DEPS = {
    "tailwindcss": "^3.4.0",
    "postcss": "^8.4.0",
    "autoprefixer": "^10.4.0",
}

_FrameworkBaseDeps = {
    FrameworkType.REACT: _REACT_DEPS,
    FrameworkType.VUE: _VUE_DEPS,
    FrameworkType.SVELTE: _SVELTE_DEPS,
    FrameworkType.ASTRO: _ASTRO_DEPS,
    FrameworkType.HTML: _HTML_DEPS,
    FrameworkType.NEXTJS: _NEXTJS_DEPS,
}

_FrameworkExtensions = {
    FrameworkType.REACT: ".jsx",
    FrameworkType.VUE: ".vue",
    FrameworkType.SVELTE: ".svelte",
    FrameworkType.ASTRO: ".astro",
    FrameworkType.HTML: ".html",
    FrameworkType.NEXTJS: ".tsx",
}

_FrameworkVitePlugins = {
    FrameworkType.REACT: "@vitejs/plugin-react",
    FrameworkType.VUE: "@vitejs/plugin-vue",
    FrameworkType.SVELTE: "@sveltejs/vite-plugin-svelte",
    FrameworkType.ASTRO: None,
    FrameworkType.HTML: None,
    FrameworkType.NEXTJS: None,
}


def get_framework_config(framework: FrameworkType, styling: StylingType) -> FrameworkConfig:
    if not isinstance(framework, FrameworkType):
        raise ValueError(f"Invalid framework: {framework}")
    if not isinstance(styling, StylingType):
        raise ValueError(f"Invalid styling: {styling}")

    base_deps = _FrameworkBaseDeps[framework]
    ext_deps = dict(base_deps.get("dependencies", {}))
    ext_dev_deps = dict(base_deps.get("devDependencies", {}))

    if styling == StylingType.TAILWIND:
        ext_dev_deps.update(_TAILWIND_DEV_DEPS)

    if framework == FrameworkType.ASTRO and styling == StylingType.TAILWIND:
        ext_deps.update(_ASTRO_TAILWIND_DEPS.get("dependencies", {}))

    return FrameworkConfig(
        framework=framework,
        styling=styling,
        file_extension=_FrameworkExtensions[framework],
        vite_plugin=_FrameworkVitePlugins[framework],
        package_dependencies={
            "dependencies": ext_deps,
            "devDependencies": ext_dev_deps,
        },
    )


def get_sandbox_template(framework: FrameworkType, styling: StylingType) -> Dict[str, str]:
    config = get_framework_config(framework, styling)
    pkg_json = _generate_package_json(config)
    templates: Dict[str, str] = {
        "package.json": pkg_json,
    }

    if framework == FrameworkType.REACT:
        templates["vite.config.js"] = _react_vite_config(styling)
        templates["index.html"] = _react_index_html()
        templates["src/main.jsx"] = _react_main_jsx()
        templates["src/App.jsx"] = _react_app_jsx()
        if styling == StylingType.TAILWIND:
            templates["tailwind.config.js"] = _tailwind_config()
            templates["postcss.config.js"] = _postcss_config()
            templates["src/index.css"] = _tailwind_css()
        elif styling == StylingType.CSS_MODULES:
            templates["src/App.module.css"] = _css_modules_example()
        else:
            templates["src/App.css"] = _plain_css_example()

    elif framework == FrameworkType.VUE:
        templates["vite.config.js"] = _vue_vite_config(styling)
        templates["index.html"] = _vue_index_html()
        templates["src/main.js"] = _vue_main_js()
        templates["src/App.vue"] = _vue_app_vue(styling)
        if styling == StylingType.TAILWIND:
            templates["tailwind.config.js"] = _tailwind_config()
            templates["postcss.config.js"] = _postcss_config()
            templates["src/style.css"] = _tailwind_css()

    elif framework == FrameworkType.SVELTE:
        templates["vite.config.js"] = _svelte_vite_config(styling)
        templates["index.html"] = _svelte_index_html()
        templates["src/main.js"] = _svelte_main_js()
        templates["src/App.svelte"] = _svelte_app_svelte(styling)
        if styling == StylingType.TAILWIND:
            templates["tailwind.config.js"] = _tailwind_config()
            templates["postcss.config.js"] = _postcss_config()
            templates["src/app.css"] = _tailwind_css()

    elif framework == FrameworkType.ASTRO:
        templates["astro.config.mjs"] = _astro_config(styling)
        templates["src/pages/index.astro"] = _astro_index(styling)
        templates["src/layouts/Layout.astro"] = _astro_layout(styling)
        if styling == StylingType.TAILWIND:
            templates["tailwind.config.js"] = _tailwind_config()
            templates["postcss.config.js"] = _postcss_config()

    elif framework == FrameworkType.HTML:
        templates["index.html"] = _html_index(styling)
        if styling == StylingType.TAILWIND:
            templates["tailwind.config.js"] = _tailwind_config()
            templates["postcss.config.js"] = _postcss_config()
            templates["src/style.css"] = _tailwind_css()
        elif styling == StylingType.CSS_MODULES:
            templates["src/style.css"] = _css_modules_example()
        else:
            templates["src/style.css"] = _plain_css_example()

    elif framework == FrameworkType.NEXTJS:
        templates["next.config.js"] = _nextjs_config()
        templates["pages/index.tsx"] = _nextjs_index()
        templates["pages/_app.tsx"] = _nextjs_app()
        templates["tsconfig.json"] = _nextjs_tsconfig()
        if styling == StylingType.TAILWIND:
            templates["tailwind.config.js"] = _tailwind_config()
            templates["postcss.config.js"] = _postcss_config()
            templates["styles/globals.css"] = _tailwind_css()
        elif styling == StylingType.CSS_MODULES:
            templates["styles/Home.module.css"] = _css_modules_example()

    return templates


def get_worker_conversion_rules(framework: FrameworkType) -> str:
    rules = {
        FrameworkType.REACT: _react_worker_rules(),
        FrameworkType.VUE: _vue_worker_rules(),
        FrameworkType.SVELTE: _svelte_worker_rules(),
        FrameworkType.ASTRO: _astro_worker_rules(),
        FrameworkType.HTML: _html_worker_rules(),
        FrameworkType.NEXTJS: _nextjs_worker_rules(),
    }
    return rules[framework]


def validate_framework_config(config: FrameworkConfig) -> bool:
    if config.vite_plugin not in ALLOWED_VITE_PLUGINS:
        raise ValueError(f"Plugin not allowed: {config.vite_plugin}")

    for pkg in config.package_dependencies.get("dependencies", {}):
        if pkg not in KNOWN_SAFE_PACKAGES:
            raise ValueError(f"Package not allowed: {pkg}")

    for pkg in config.package_dependencies.get("devDependencies", {}):
        if pkg not in KNOWN_SAFE_PACKAGES:
            raise ValueError(f"Package not allowed: {pkg}")

    return True


def _generate_package_json(config: FrameworkConfig) -> str:
    import json
    pkg = {
        "name": "cloned-project",
        "private": True,
        "version": "0.0.0",
        "type": "module",
        "scripts": {
            "dev": "vite",
            "build": "vite build",
            "preview": "vite preview",
        },
        "dependencies": config.package_dependencies.get("dependencies", {}),
        "devDependencies": config.package_dependencies.get("devDependencies", {}),
    }
    if config.framework == FrameworkType.NEXTJS:
        pkg["scripts"] = {
            "dev": "next dev",
            "build": "next build",
            "start": "next start",
        }
    return json.dumps(pkg, indent=2)


def _react_vite_config(styling: StylingType) -> str:
    return '''import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
})
'''


def _vue_vite_config(styling: StylingType) -> str:
    return '''import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
})
'''


def _svelte_vite_config(styling: StylingType) -> str:
    return '''import { defineConfig } from 'vite'
import { svelte } from '@sveltejs/vite-plugin-svelte'

export default defineConfig({
  plugins: [svelte()],
})
'''


def _astro_config(styling: StylingType) -> str:
    if styling == StylingType.TAILWIND:
        return '''import { defineConfig } from 'astro/config';
import tailwind from '@astrojs/tailwind';

export default defineConfig({
  integrations: [tailwind()],
});
'''
    return '''import { defineConfig } from 'astro/config';

export default defineConfig({});
'''


def _nextjs_config() -> str:
    return '''/** @type {import('next').NextConfig} */
const nextConfig = {}

module.exports = nextConfig
'''


def _react_index_html() -> str:
    return '''<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Cloned Project</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
'''


def _vue_index_html() -> str:
    return '''<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Cloned Project</title>
  </head>
  <body>
    <div id="app"></div>
    <script type="module" src="/src/main.js"></script>
  </body>
</html>
'''


def _svelte_index_html() -> str:
    return '''<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Cloned Project</title>
  </head>
  <body>
    <div id="app"></div>
    <script type="module" src="/src/main.js"></script>
  </body>
</html>
'''


def _html_index(styling: StylingType) -> str:
    if styling == StylingType.TAILWIND:
        return '''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Cloned Project</title>
  <link rel="stylesheet" href="/src/style.css" />
</head>
<body>
  <div id="app"></div>
  <script>
    console.log('Cloned project loaded');
  </script>
</body>
</html>
'''
    return '''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Cloned Project</title>
  <link rel="stylesheet" href="/src/style.css" />
</head>
<body>
  <div id="app"></div>
  <script>
    console.log('Cloned project loaded');
  </script>
</body>
</html>
'''


def _react_main_jsx() -> str:
    return '''import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
'''


def _react_app_jsx() -> str:
    return '''function App() {
  return (
    <div className="min-h-screen bg-gray-100">
      <h1 className="text-3xl font-bold p-8">Cloned Project</h1>
    </div>
  )
}

export default App
'''


def _vue_main_js() -> str:
    return '''import { createApp } from 'vue'
import App from './App.vue'
import './style.css'

createApp(App).mount('#app')
'''


def _vue_app_vue(styling: StylingType) -> str:
    if styling == StylingType.TAILWIND:
        return '''<template>
  <div class="min-h-screen bg-gray-100">
    <h1 class="text-3xl font-bold p-8">Cloned Project</h1>
  </div>
</template>

<script setup>
</script>
'''
    return '''<template>
  <div class="container">
    <h1>Cloned Project</h1>
  </div>
</template>

<script setup>
</script>

<style scoped>
.container {
  min-height: 100vh;
  background-color: #f3f4f6;
  padding: 2rem;
}

h1 {
  font-size: 1.875rem;
  font-weight: 700;
}
</style>
'''


def _svelte_main_js() -> str:
    return '''import App from './App.svelte'

const app = new App({
  target: document.getElementById('app'),
})

export default app
'''


def _svelte_app_svelte(styling: StylingType) -> str:
    if styling == StylingType.TAILWIND:
        return '''<div class="min-h-screen bg-gray-100">
  <h1 class="text-3xl font-bold p-8">Cloned Project</h1>
</div>

<script>
</script>
'''
    return '''<div class="container">
  <h1>Cloned Project</h1>
</div>

<script>
</script>

<style>
.container {
  min-height: 100vh;
  background-color: #f3f4f6;
  padding: 2rem;
}

h1 {
  font-size: 1.875rem;
  font-weight: 700;
}
</style>
'''


def _astro_index(styling: StylingType) -> str:
    return '''---
import Layout from '../layouts/Layout.astro';
---

<Layout title="Cloned Project">
  <main>
    <h1>Cloned Project</h1>
  </main>
</Layout>
'''


def _astro_layout(styling: StylingType) -> str:
    if styling == StylingType.TAILWIND:
        return '''---
interface Props {
  title: string;
}

const { title } = Astro.props;
---

<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{title}</title>
  </head>
  <body class="min-h-screen bg-gray-100">
    <slot />
  </body>
</html>
'''
    return '''---
interface Props {
  title: string;
}

const { title } = Astro.props;
---

<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{title}</title>
  </head>
  <body>
    <slot />
  </body>
</html>

<style>
  body {
    min-height: 100vh;
    background-color: #f3f4f6;
  }
</style>
'''


def _nextjs_index() -> str:
    return '''export default function Home() {
  return (
    <main className="min-h-screen bg-gray-100">
      <h1 className="text-3xl font-bold p-8">Cloned Project</h1>
    </main>
  )
}
'''


def _nextjs_app() -> str:
    return '''import type { AppProps } from 'next/app'
import '../styles/globals.css'

export default function App({ Component, pageProps }: AppProps) {
  return <Component {...pageProps} />
}
'''


def _nextjs_tsconfig() -> str:
    return '''{
  "compilerOptions": {
    "target": "es5",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [{"name": "next"}],
    "paths": {"@/*": ["./*"]}
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
'''


def _tailwind_config() -> str:
    return '''/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
'''


def _postcss_config() -> str:
    return '''export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
'''


def _tailwind_css() -> str:
    return '''@tailwind base;
@tailwind components;
@tailwind utilities;
'''


def _css_modules_example() -> str:
    return '''.container {
  min-height: 100vh;
  background-color: #f3f4f6;
  padding: 2rem;
}

h1 {
  font-size: 1.875rem;
  font-weight: 700;
}
'''


def _plain_css_example() -> str:
    return '''.container {
  min-height: 100vh;
  background-color: #f3f4f6;
  padding: 2rem;
}

h1 {
  font-size: 1.875rem;
  font-weight: 700;
}
'''


def _react_worker_rules() -> str:
    return """REACT CONVERSION RULES:
- Convert HTML elements to JSX: class -> className, for -> htmlFor
- Self-close all empty elements: <img />, <br />, <input />
- Use JSX expressions: {variable} instead of ${variable}
- Convert inline styles to style={{camelCase: 'value'}}
- Use React hooks: useState, useEffect, useContext
- Component names must be PascalCase
- Export components as default exports
- Use React.Fragment or <> for wrapper elements
- Event handlers: onClick, onChange, onSubmit (camelCase)
- Boolean attributes: disabled={true} not disabled="true"
"""


def _vue_worker_rules() -> str:
    return """VUE CONVERSION RULES:
- Use Vue 3 Composition API with <script setup>
- Convert to Single File Components (.vue)
- Use v-bind:prop or :prop for dynamic attributes
- Use v-on:event or @event for event handlers
- Use v-if/v-show for conditional rendering
- Use v-for for lists with :key
- Use ref() for reactive primitives
- Use reactive() for reactive objects
- Use computed() for derived state
- Use watch() for side effects
- Props defined with defineProps()
- Emits defined with defineEmits()
- Scoped styles with <style scoped>
"""


def _svelte_worker_rules() -> str:
    return """SVELTE CONVERSION RULES:
- Use Svelte 4 syntax with reactive declarations
- Use {#if}/{:else if}/{:else}/{/if} for conditionals
- Use {#each items as item (item.id)}/{/each} for lists
- Use on:click={handler} for event handlers
- Use bind:value for two-way binding
- Reactive declarations: $: doubled = count * 2
- Use stores: writable, readable, derived
- Use on:mount and on:destroy lifecycle
- Props with export let
- Use {@html content} for raw HTML
- Use <slot> for content projection
- Scoped styles by default
"""


def _astro_worker_rules() -> str:
    return """ASTRO CONVERSION RULES:
- Use frontmatter (---) for server-side code
- Components are .astro files
- Use component syntax: <Component /> for frameworks
- Use client: directives for hydration:
  - client:load - Hydrate on page load
  - client:idle - Hydrate when browser is idle
  - client:visible - Hydrate when visible
  - client:media={query} - Hydrate at media query
  - client:only="react" - Client-only rendering
- Islands architecture: static by default
- Use Astro.props for component props
- Use <slot> for content projection
- Use Astro.url, Astro.request for request info
- Layout components with <slot />
"""


def _html_worker_rules() -> str:
    return """PLAIN HTML/CSS CONVERSION RULES:
- Use semantic HTML5 elements: header, nav, main, section, article, footer
- NO FRAMEWORK dependencies - pure vanilla JavaScript
- Use CSS custom properties (variables) for theming
- Use querySelector/querySelectorAll for DOM manipulation
- Use addEventListener for event handling
- Use fetch() for API calls
- Use IntersectionObserver for scroll effects
- Use CSS Grid and Flexbox for layout
- Use CSS animations/transitions for effects
- Use template literals for dynamic HTML
- Use data-* attributes for state
- Mobile-first responsive design with media queries
"""


def _nextjs_worker_rules() -> str:
    return """NEXT.JS CONVERSION RULES:
- Use App Router (app/) or Pages Router (pages/)
- Server Components by default (no "use client")
- Add "use client" only for interactivity
- Use next/image for optimized images
- Use next/link for client-side navigation
- Use next/font for optimized fonts
- Use next/head for metadata (Pages Router)
- Use generateMetadata() for dynamic metadata (App Router)
- Use server actions for form handling
- Data fetching: fetch() in Server Components
- Use params and searchParams in Server Components
- Use client-side: useState, useEffect, useRef
- Layout.tsx for shared layouts
- Loading.tsx for loading states
- Error.tsx for error boundaries
"""
