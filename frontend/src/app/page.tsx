"use client";

import {
  Header,
  HeroWithInput,
  Logos,
  FeaturesList,
  FeaturesAccordion,
  Features,
  ShowcasesGallery,
  Footer,
  QuantumScene,
} from "@/components/landing";
import { Header as HeaderType, Section } from "@/types/landing";

// Header configuration matching reference project
const headerConfig: HeaderType = {
  id: "header",
  brand: {
    title: "", // Empty since SVG contains the text
    logo: {
      src: "/logo.svg",
      alt: "Nexting",
      width: 180,
      height: 48,
    },
    url: "/",
  },
  nav: {
    items: [
      {
        title: "Tools",
        icon: "Wrench",
        children: [
          {
            title: "Web Extractor",
            description: "Extract webpage structure and styles",
            url: "/extractor",
            icon: "Globe",
          },
          {
            title: "Clone Agent",
            description: "AI-powered code generation",
            url: "/agent",
            icon: "Bot",
          },
        ],
      },
      {
        title: "About",
        url: "/about",
        icon: "User",
      },
      {
        title: "Docs",
        url: "/docs",
        icon: "BookOpenText",
      },
      {
        title: "GitHub",
        url: "https://github.com/ericshang98",
        target: "_blank",
        icon: "Github",
      },
    ],
  },
  buttons: [],
  user_nav: {
    show_name: true,
    show_credits: false,
    show_sign_out: true,
    items: [
      {
        title: "Settings",
        url: "/settings/profile",
        icon: "Settings",
      },
    ],
  },
  show_sign: true,
  show_theme: true,
  show_locale: false,
};

// Hero section configuration
const heroConfig: Section = {
  id: "hero",
  block: "hero-with-input",
  title: "Perfect means 100% web clone",
  highlight_text: "100%",
  description:
    "Others guess from screenshots. We extract the real code — DOM, styles, components, interactions. Get pixel-perfect, maintainable output in seconds.",
  announcement: {
    title: "See the Difference →",
    url: "#comparison",
  },
  buttons: [],
};

// Page content configuration
const pageConfig = {
  logos: {
    title: "Export to Your Favorite Framework",
    items: [
      { title: "Next.js", image: { src: "/logos/nextjs.svg", alt: "Next.js" } },
      { title: "React", image: { src: "/logos/react.svg", alt: "React" } },
      { title: "TailwindCSS", image: { src: "/logos/tailwindcss.svg", alt: "TailwindCSS" } },
      { title: "Vue", image: { src: "/logos/vue.svg", alt: "Vue" } },
      { title: "TypeScript", image: { src: "/logos/typescript.svg", alt: "TypeScript" } },
    ],
  },

  comparison: {
    id: "comparison",
    label: "The Difference",
    title: "Screenshot Tools vs Code Extraction",
    description:
      "Most tools look at your page like a picture and guess the code. We read the actual source — that's why our output is production-ready, not a rough approximation.",
    image: {
      src: "/features/comparison.png",
      alt: "Comparison",
    },
    items: [
      {
        title: "Screenshot Tools",
        description:
          "AI interprets pixels → guesses layout → outputs approximation. Breaks on resize, loses interactions.",
        icon: "ImageOff",
      },
      {
        title: "Perfect Web Clone",
        description:
          "Extracts real DOM → analyzes CSS → preserves structure. Responsive, interactive, maintainable.",
        icon: "CheckCircle",
      },
      {
        title: "Their Output",
        description:
          "Hardcoded pixels, dead interactions, tangled code that needs complete rewrite.",
        icon: "X",
      },
      {
        title: "Our Output",
        description:
          "Clean components, flexible units, preserved animations, code you can actually ship.",
        icon: "Sparkles",
      },
    ],
  },

  problem: {
    id: "problem",
    label: "Why Others Fail",
    title: "The Screenshot Approach is Fundamentally Broken",
    description:
      "When you screenshot a webpage, you capture pixels — not code. No amount of AI can perfectly reconstruct what was lost.",
    items: [
      {
        title: "Lost Responsive Design",
        description:
          "Screenshots are fixed-size images. The AI has no idea about breakpoints, flexible units, or how the layout should adapt. You get hardcoded pixel values that break on every screen size.",
        icon: "Monitor",
        image: { src: "/features/responsive.png", alt: "Responsive" },
      },
      {
        title: "Dead Interactions",
        description:
          "Hover effects, animations, transitions, scroll behaviors — all invisible in a screenshot. You get a static snapshot, not a living webpage.",
        icon: "MousePointerClick",
        image: { src: "/features/interactions.png", alt: "Interactions" },
      },
      {
        title: "Guessed Structure",
        description:
          "AI sees visual patterns and makes assumptions. Semantic HTML, accessibility attributes, component boundaries — all lost. You get divs all the way down.",
        icon: "HelpCircle",
        image: { src: "/features/structure.png", alt: "Structure" },
      },
      {
        title: "Unmaintainable Output",
        description:
          "The generated code is a tangled mess with no logical organization. Every change requires starting from scratch. It's faster to rewrite than to modify.",
        icon: "Code",
        image: { src: "/features/maintainable.png", alt: "Maintainable" },
      },
    ],
  },

  solution: {
    id: "solution",
    title: "Why Multi-Agent Architecture?",
    description:
      "Traditional single-model approaches fail on complex pages. Our multi-agent system breaks down the problem — each agent specializes in one layer, then they collaborate to reconstruct the complete page from a single URL.",
    items: [
      {
        title: "DOM Structure Agent",
        description:
          "Handles massive, deeply nested DOM trees that would overwhelm a single model. Extracts semantic structure, hierarchy, and component boundaries piece by piece.",
        icon: "Layers",
      },
      {
        title: "Style Analysis Agent",
        description:
          "Processes thousands of CSS rules in parallel. Captures computed styles, CSS variables, breakpoints, and theme tokens without context limits.",
        icon: "Palette",
      },
      {
        title: "Component Detection Agent",
        description:
          "Analyzes patterns across the entire codebase. Identifies reusable components and outputs modular code — impossible with a single pass.",
        icon: "Code2",
      },
      {
        title: "Code Generation Agent",
        description:
          "Synthesizes outputs from all agents into production-ready code. Handles complex file structures that single models can't manage.",
        icon: "Zap",
      },
    ],
  },

  features: {
    id: "features",
    title: "What You Get",
    description: "Everything screenshot tools promise but can't deliver.",
    items: [
      {
        title: "Pixel-Perfect Accuracy",
        description:
          "We extract exact measurements, not approximations. Your clone matches the original down to the last pixel.",
        icon: "Layers",
      },
      {
        title: "Responsive by Default",
        description:
          "Breakpoints and flexible units are preserved. Your clone works on every screen size automatically.",
        icon: "Smartphone",
      },
      {
        title: "Living Interactions",
        description:
          "Hover effects, transitions, animations — all captured and regenerated. Your clone feels alive.",
        icon: "Zap",
      },
      {
        title: "Clean, Modular Code",
        description:
          "Component-based output with proper naming. Easy to read, easy to maintain, easy to extend.",
        icon: "Code2",
      },
      {
        title: "Multiple Frameworks",
        description:
          "Export to React, Next.js, Vue, or plain HTML. Use your preferred stack.",
        icon: "Layers",
      },
      {
        title: "Theme-Aware",
        description:
          "Dark mode, CSS variables, design tokens — all extracted and applied correctly.",
        icon: "Palette",
      },
    ],
  },

  showcase: {
    id: "showcase",
    label: "Gallery",
    title: "Community Clones",
    description:
      "See what others have built with Perfect Web Clone. Click any card to explore.",
    items: [
      {
        title: "Stripe Homepage",
        description: "Financial infrastructure for the internet",
        source_url: "https://stripe.com",
        url: "/showcase/stripe",
        image: { src: "/showcases/stripe.png", alt: "Stripe Clone" },
      },
      {
        title: "Vercel Dashboard",
        description: "Deploy web projects with zero config",
        source_url: "https://vercel.com",
        url: "/showcase/vercel",
        image: { src: "/showcases/vercel.png", alt: "Vercel Clone" },
      },
      {
        title: "Linear App",
        description: "Issue tracking for modern teams",
        source_url: "https://linear.app",
        url: "/showcase/linear",
        image: { src: "/showcases/linear.png", alt: "Linear Clone" },
      },
      {
        title: "Notion Landing",
        description: "All-in-one workspace",
        source_url: "https://notion.so",
        url: "/showcase/notion",
        image: { src: "/showcases/notion.png", alt: "Notion Clone" },
      },
      {
        title: "Figma Website",
        description: "Collaborative design tool",
        source_url: "https://figma.com",
        url: "/showcase/figma",
        image: { src: "/showcases/figma.png", alt: "Figma Clone" },
      },
      {
        title: "Slack Landing",
        description: "Business communication platform",
        source_url: "https://slack.com",
        url: "/showcase/slack",
        image: { src: "/showcases/slack.png", alt: "Slack Clone" },
      },
    ],
    buttons: [{ title: "View All Clones →", url: "/showcases", variant: "outline" as const }],
  },

  footer: {
    brand: {
      name: "Nexting",
      logo: "/logo.svg",
      description:
        "Open source AI-powered web cloning tool. Extract, analyze, and clone any webpage with AI assistance.",
    },
    nav: [
      {
        title: "Tools",
        children: [
          { title: "Web Extractor", url: "/extractor" },
          { title: "Clone Agent", url: "/agent" },
        ],
      },
      {
        title: "Resources",
        children: [
          { title: "Documentation", url: "/docs" },
          { title: "About", url: "/about" },
        ],
      },
      {
        title: "Links",
        children: [
          { title: "GitHub", url: "https://github.com/ericshang98" },
          { title: "Playwright", url: "https://playwright.dev" },
        ],
      },
    ],
    social: [
      { icon: "Github", url: "https://github.com/ericshang98", title: "GitHub" },
    ],
  },
};

export default function HomePage() {
  return (
    <main className="min-h-screen grid-background">
      <Header header={headerConfig} />

      {/* Hero section with 3D background */}
      <div className="relative min-h-screen overflow-hidden">
        {/* 3D背景 */}
        <QuantumScene />

        {/* 文字内容 - 在3D背景上方 */}
        <div className="relative z-10">
          <HeroWithInput section={heroConfig} />
        </div>
      </div>

      <ShowcasesGallery {...pageConfig.showcase} />

      <Logos {...pageConfig.logos} />

      <FeaturesList {...pageConfig.comparison} className="bg-muted" />

      <FeaturesAccordion {...pageConfig.problem} />

      <Features {...pageConfig.solution} />

      <Features {...pageConfig.features} className="bg-muted" />

      <Footer {...pageConfig.footer} />
    </main>
  );
}
