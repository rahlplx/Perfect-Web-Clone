/**
 * Codegen Configuration
 */

export const CODEGEN_CONFIG = {
  // Backend API URL
  API_URL: process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:5100",

  // Claude API settings
  CLAUDE_API_KEY: process.env.CLAUDE_PROXY_API_KEY || "",
  CLAUDE_BASE_URL: process.env.CLAUDE_PROXY_BASE_URL || "https://api.anthropic.com/v1/messages",
  CLAUDE_MODEL: process.env.CLAUDE_PROXY_MODEL || "claude-3-5-sonnet-20241022",

  // Extraction settings
  DEFAULT_VIEWPORT_WIDTH: 1920,
  DEFAULT_VIEWPORT_HEIGHT: 1080,
  MAX_EXTRACTION_TIMEOUT: 60000,

  // Token estimation
  CHARS_PER_TOKEN: 4,
  MAX_TOKENS_PER_SECTION: 8000,
} as const;
