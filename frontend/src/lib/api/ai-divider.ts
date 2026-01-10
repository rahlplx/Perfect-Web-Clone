/**
 * AI Divider API and Utilities
 */

import type {
  ElementInfo,
  AIDivisionResult,
  AIDivisionType,
  TopLevelDivSummary
} from "@/types/extractor";
import { CODEGEN_CONFIG } from "@/config/codegen";

/**
 * Division type colors for visualization
 */
export const DIVISION_TYPE_COLORS: Record<AIDivisionType, string> = {
  header: "#3B82F6",      // blue
  footer: "#6B7280",      // gray
  navigation: "#8B5CF6",  // purple
  hero: "#F59E0B",        // amber
  content: "#10B981",     // emerald
  features: "#06B6D4",    // cyan
  cta: "#EF4444",         // red
  testimonial: "#EC4899", // pink
  pricing: "#F97316",     // orange
  contact: "#14B8A6",     // teal
  sidebar: "#A855F7",     // violet
  section: "#64748B",     // slate
};

/**
 * Extract top-level divs from DOM tree
 */
export function extractTopLevelDivs(domTree: ElementInfo): TopLevelDivSummary[] {
  const results: TopLevelDivSummary[] = [];

  // Find body element
  const body = findBodyElement(domTree);
  if (!body) return results;

  // Extract top-level children
  body.children.forEach((child, index) => {
    if (!child.is_visible) return;

    const estimatedTokens = Math.ceil(child.inner_html_length / CODEGEN_CONFIG.CHARS_PER_TOKEN);

    results.push({
      index,
      tag: child.tag,
      id: child.id || null,
      classes: child.classes,
      rect: {
        x: child.rect.x,
        y: child.rect.y,
        width: child.rect.width,
        height: child.rect.height,
      },
      innerHtmlLength: child.inner_html_length,
      estimatedTokens,
    });
  });

  return results;
}

/**
 * Find body element in DOM tree
 */
function findBodyElement(element: ElementInfo): ElementInfo | null {
  if (element.tag === "body") return element;

  for (const child of element.children) {
    const found = findBodyElement(child);
    if (found) return found;
  }

  return null;
}

/**
 * Analyze page with AI to get semantic divisions
 */
export async function analyzeWithAI(
  url: string,
  screenshot: string,
  domTree: ElementInfo,
  viewportWidth: number,
  viewportHeight: number,
  pageHeight: number,
  useCache: boolean = true
): Promise<AIDivisionResult> {
  const apiUrl = `${CODEGEN_CONFIG.API_URL}/api/ai/divide`;

  try {
    const response = await fetch(apiUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        url,
        screenshot,
        dom_tree: domTree,
        viewport_width: viewportWidth,
        viewport_height: viewportHeight,
        page_height: pageHeight,
        use_cache: useCache,
      }),
    });

    if (!response.ok) {
      throw new Error(`AI analysis failed: ${response.statusText}`);
    }

    const result = await response.json();
    return result as AIDivisionResult;
  } catch (error) {
    return {
      success: false,
      divisions: [],
      validation: null,
      fromCache: false,
      processingTimeMs: 0,
      error: error instanceof Error ? error.message : "Unknown error",
    };
  }
}
