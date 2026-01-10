"""
AI Divider - Intelligent Page Section Division using LLM
AI 分区器 - 使用 LLM 进行智能页面分区

Features:
- Extract top-level divs from DOM tree
- Call Claude API with screenshot + div summary
- Parse and validate LLM response
- Retry mechanism (max 3 times)
- Result caching by URL hash
"""

import asyncio
import hashlib
import json
import re
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional, Tuple

# LLM clients
from anthropic import AsyncAnthropic
from openai import AsyncOpenAI

# Local imports
from .models import ElementInfo, ElementRect
import code_gen_config as config

# Setup logger
logger = logging.getLogger(__name__)


# ==================== Data Models ====================

@dataclass
class TopLevelDivSummary:
    """
    Top-level div summary for LLM input
    """
    index: int
    tag: str
    id: Optional[str]
    classes: List[str]
    rect: Dict[str, float]  # {x, y, width, height}
    inner_html_length: int
    estimated_tokens: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AIDivisionInfo:
    """
    AI division result
    """
    id: str
    name: str
    type: str  # header, footer, navigation, hero, content, features, cta, testimonial, pricing, contact, sidebar, section
    description: str
    div_indices: List[int]
    rect: Dict[str, float]  # merged bounding box
    estimated_tokens: int
    priority: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ValidationResult:
    """
    Validation result for AI divisions
    """
    is_mutually_exclusive: bool = True
    covers_full_page: bool = True
    large_divisions: List[Dict[str, Any]] = field(default_factory=list)
    missing_indices: List[int] = field(default_factory=list)
    overlapping_indices: List[int] = field(default_factory=list)


@dataclass
class AIDivisionResult:
    """
    Complete AI division result
    """
    success: bool
    divisions: List[AIDivisionInfo] = field(default_factory=list)
    validation: Optional[ValidationResult] = None
    from_cache: bool = False
    processing_time_ms: int = 0
    error: Optional[str] = None
    retry_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "divisions": [d.to_dict() for d in self.divisions],
            "validation": asdict(self.validation) if self.validation else None,
            "from_cache": self.from_cache,
            "processing_time_ms": self.processing_time_ms,
            "error": self.error,
            "retry_count": self.retry_count,
        }


@dataclass
class CachedDivision:
    """
    Cached AI division result
    """
    url_hash: str
    url: str
    result: AIDivisionResult
    created_at: datetime = field(default_factory=datetime.now)

    def is_expired(self, ttl_hours: int = 24) -> bool:
        return datetime.now() - self.created_at > timedelta(hours=ttl_hours)


# ==================== Cache Manager ====================

class AIDividerCache:
    """
    In-memory cache for AI division results
    Cache key includes both URL and mode (visual vs layout-only)
    """

    def __init__(self, max_size: int = 100, ttl_hours: int = 24):
        self._cache: Dict[str, CachedDivision] = {}
        self._max_size = max_size
        self._ttl_hours = ttl_hours

    def _hash_key(self, url: str, use_screenshot: bool = True) -> str:
        """Generate SHA256 hash for URL + mode"""
        mode = "visual" if use_screenshot else "layout"
        key = f"{url}:{mode}"
        return hashlib.sha256(key.encode()).hexdigest()[:16]

    def get(self, url: str, use_screenshot: bool = True) -> Optional[AIDivisionResult]:
        """Get cached result by URL and mode"""
        cache_key = self._hash_key(url, use_screenshot)
        cached = self._cache.get(cache_key)

        if cached is None:
            return None

        if cached.is_expired(self._ttl_hours):
            del self._cache[cache_key]
            return None

        # Mark as from cache
        result = cached.result
        result.from_cache = True
        return result

    def set(self, url: str, result: AIDivisionResult, use_screenshot: bool = True) -> None:
        """Cache result by URL and mode"""
        # Evict oldest if at capacity
        if len(self._cache) >= self._max_size:
            oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k].created_at)
            del self._cache[oldest_key]

        cache_key = self._hash_key(url, use_screenshot)
        self._cache[cache_key] = CachedDivision(
            url_hash=cache_key,
            url=url,
            result=result,
        )

    def clear(self) -> None:
        """Clear all cache"""
        self._cache.clear()

    def get_by_hash(self, url_hash: str) -> Optional[AIDivisionResult]:
        """Get cached result by URL hash"""
        cached = self._cache.get(url_hash)
        if cached and not cached.is_expired(self._ttl_hours):
            result = cached.result
            result.from_cache = True
            return result
        return None


# Global cache instance
ai_divider_cache = AIDividerCache()


# ==================== LLM Prompt Templates ====================

SYSTEM_PROMPT = """You are a web page section analyzer. Divide the page into NON-OVERLAPPING semantic sections.

## CRITICAL RULES (MUST FOLLOW)
1. **NO OVERLAP**: Each element index can ONLY appear in ONE section. Never duplicate indices.
2. **COMPLETE COVERAGE**: Every index from 0 to max_index MUST be assigned to exactly one section.
3. **TOP TO BOTTOM ORDER**: Sections must be ordered by their vertical position on the page.
4. **TOKEN LIMIT**: Each section should ideally be under 10,000 tokens. Split large sections if needed.

## YOUR TASK
1. Look at the element list with positions (y-coordinate shows vertical position)
2. Group CONSECUTIVE elements into semantic sections based on their purpose
3. Elements close together vertically (similar y values) often belong to the same section
4. Return the div_indices for each section - indices must be MUTUALLY EXCLUSIVE

## SECTION TYPES (use exactly these values)
header, navigation, hero, features, content, testimonial, pricing, cta, contact, footer, sidebar, section

## OUTPUT FORMAT (JSON only, no markdown)
{
  "divisions": [
    {
      "name": "Header",
      "type": "header",
      "description": "Navigation bar",
      "div_indices": [0],
      "priority": 1
    },
    {
      "name": "Hero",
      "type": "hero",
      "description": "Main banner",
      "div_indices": [1, 2],
      "priority": 2
    }
  ]
}

## EXAMPLE - CORRECT (no overlap)
Elements: [0] header y:0, [1] div y:100, [2] section y:500, [3] section y:1000, [4] footer y:1500
Answer: Header [0], Hero [1], Features [2], Content [3], Footer [4]

## EXAMPLE - WRONG (has overlap)
Header [0, 1], Hero [1, 2] ← WRONG! Index 1 appears twice!"""


USER_PROMPT_TEMPLATE = """Divide this page into NON-OVERLAPPING sections.

## PAGE INFO
- URL: {url}
- Page size: {viewport_width}x{page_height}px
- Total elements: {total_divs} (indices 0 to {max_index})

## ELEMENT LIST (sorted by vertical position)
{div_summary}

## REQUIREMENTS
1. ASSIGN EVERY INDEX (0 to {max_index}) to exactly ONE section
2. NO DUPLICATES - each index appears in only one section
3. Order sections top-to-bottom by y-position
4. Large sections (>10K tokens) should be split

## OUTPUT
Return ONLY valid JSON with div_indices arrays that are MUTUALLY EXCLUSIVE."""


# ==================== AI Divider Class ====================

class AIDivider:
    """
    AI-powered page section divider using Gemini or Claude API
    """

    MAX_RETRIES = 3
    LARGE_DIVISION_THRESHOLD = 10000  # chars, approximately 2500 tokens

    def __init__(self):
        # Determine which provider to use
        self.provider = config.AI_DIVIDER_PROVIDER  # "gemini" or "claude"
        self.client = None
        self.model = None
        self._init_client()

    def _init_client(self):
        """Initialize LLM client based on config"""
        logger.info(f"AI Divider: initializing (provider={self.provider})")
        logger.info(f"AI Divider: USE_CLAUDE_PROXY={config.USE_CLAUDE_PROXY}")
        logger.info(f"AI Divider: CLAUDE_PROXY_BASE_URL={config.CLAUDE_PROXY_BASE_URL}")
        logger.info(f"AI Divider: CLAUDE_PROXY_MODEL={config.CLAUDE_PROXY_MODEL}")
        logger.info(f"AI Divider: API_KEY set={bool(config.CLAUDE_PROXY_API_KEY)}")

        # Try Gemini first if configured
        if self.provider == "gemini" and config.USE_GEMINI_PROXY and config.GEMINI_PROXY_API_KEY:
            base_url = config.GEMINI_PROXY_BASE_URL
            if not base_url.endswith("/v1"):
                base_url = base_url.rstrip("/") + "/v1"

            self.client = AsyncOpenAI(
                api_key=config.GEMINI_PROXY_API_KEY,
                base_url=base_url,
            )
            self.model = config.GEMINI_PROXY_MODEL
            logger.info(f"AI Divider using Gemini proxy: {base_url}, model: {self.model}")
            return

        # Use Claude proxy
        if config.USE_CLAUDE_PROXY and config.CLAUDE_PROXY_API_KEY and config.CLAUDE_PROXY_BASE_URL:
            proxy_base_url = config.CLAUDE_PROXY_BASE_URL

            # Handle Anthropic native format URLs (e.g., https://yinli.one/v1/messages)
            # The Anthropic SDK automatically appends /messages, so we remove it
            if "/messages" in proxy_base_url.lower():
                original_url = proxy_base_url
                proxy_base_url = re.sub(r'/v1/messages', '', proxy_base_url, flags=re.IGNORECASE)
                proxy_base_url = re.sub(r'/messages', '', proxy_base_url, flags=re.IGNORECASE)
                logger.info(f"AI Divider: converted URL from {original_url} to {proxy_base_url}")

            self.client = AsyncAnthropic(
                api_key=config.CLAUDE_PROXY_API_KEY,
                base_url=proxy_base_url,
            )
            self.model = config.CLAUDE_PROXY_MODEL
            self.provider = "claude"
            logger.info(f"AI Divider initialized: Claude proxy at {proxy_base_url}, model={self.model}")
            return

        if config.ANTHROPIC_API_KEY:
            self.client = AsyncAnthropic(api_key=config.ANTHROPIC_API_KEY)
            self.model = "claude-3-5-sonnet-20241022"
            self.provider = "claude"
            logger.info("AI Divider initialized: direct Anthropic API")
            return

        logger.error("AI Divider: No LLM API key configured!")
        logger.error("Please set USE_CLAUDE_PROXY=true and CLAUDE_PROXY_API_KEY, CLAUDE_PROXY_BASE_URL")

    # Maximum tokens per element - elements larger than this will be split into children
    MAX_ELEMENT_TOKENS = 10000

    def extract_top_level_divs(self, dom_tree: Dict[str, Any]) -> List[TopLevelDivSummary]:
        """
        Extract top-level div summaries from DOM tree
        Smart extraction:
        - Recursively unwrap containers until we find meaningful sections
        - Split large elements (>10K tokens) into their children
        """
        summaries = []

        # Skip non-visual elements
        skip_tags = {"script", "style", "link", "meta", "noscript", "template"}

        # Semantic tags that are likely to be section boundaries
        semantic_tags = {"header", "nav", "main", "section", "article", "aside", "footer", "form"}

        def find_body(node: Dict[str, Any]) -> Optional[Dict[str, Any]]:
            """Find body element"""
            tag = node.get("tag", "").lower()
            if tag == "body":
                return node
            for child in node.get("children", []):
                result = find_body(child)
                if result:
                    return result
            return None

        def get_visible_children(node: Dict[str, Any]) -> List[Dict[str, Any]]:
            """Get visible children of a node, filtering out non-visual elements"""
            children = []
            for child in node.get("children", []):
                tag = child.get("tag", "").lower()
                if tag in skip_tags:
                    continue
                if not child.get("is_visible", True):
                    continue
                rect = child.get("rect", {})
                if rect.get("width", 0) == 0 or rect.get("height", 0) == 0:
                    continue
                children.append(child)
            return children

        def unwrap_single_child_containers(node: Dict[str, Any], max_depth: int = 10) -> List[Dict[str, Any]]:
            """
            Recursively unwrap containers that have only 1-2 children.
            Returns the list of children at the first level with >= 3 children,
            or when we find semantic tags.
            """
            children = get_visible_children(node)
            logger.info(f"AI Divider: unwrap depth check - found {len(children)} visible children")

            # If we have enough children (>= 3), or we've reached max depth, stop here
            if len(children) >= 3 or max_depth <= 0:
                return children

            # If no children, return empty
            if not children:
                return []

            # Check if any child is a semantic tag - if so, we're at the right level
            for child in children:
                tag = child.get("tag", "").lower()
                if tag in semantic_tags:
                    logger.info(f"AI Divider: found semantic tag '{tag}', stopping unwrap")
                    return children

            # If only 1-2 children, check if we should go deeper
            if len(children) <= 2:
                first_child = children[0]
                first_child_children = get_visible_children(first_child)

                # If the first child has more children, unwrap into it
                if len(first_child_children) >= 1:
                    tag = first_child.get("tag", "").lower()
                    logger.info(f"AI Divider: unwrapping single container '{tag}', going deeper...")
                    return unwrap_single_child_containers(first_child, max_depth - 1)

            return children

        def collect_sections(children: List[Dict[str, Any]], depth: int = 0) -> None:
            """
            Collect meaningful sections from children.
            For semantic tags, include them directly.
            For non-semantic containers with few siblings, go deeper.
            For large elements (>10K tokens), split into children.
            """
            max_depth = 10  # Prevent infinite recursion

            for child in children:
                tag = child.get("tag", "").lower()
                rect = child.get("rect", {})
                inner_html_length = child.get("inner_html_length", 0)
                estimated_tokens = inner_html_length // 4
                child_children = get_visible_children(child)

                # Skip elements with tiny height
                if rect.get("height", 0) < 50:
                    continue

                # Check if element is too large and has children to split into
                if estimated_tokens > self.MAX_ELEMENT_TOKENS and child_children and depth < max_depth:
                    logger.info(
                        f"AI Divider: Element '{tag}' has {estimated_tokens} tokens (>{self.MAX_ELEMENT_TOKENS}), "
                        f"splitting into {len(child_children)} children"
                    )
                    collect_sections(child_children, depth + 1)
                    continue

                # Semantic tags are always good boundaries
                if tag in semantic_tags:
                    add_summary(child, tag, rect, inner_html_length)
                # Regular divs with significant height
                elif rect.get("height", 0) > 100:
                    # If this div has many children, it's likely a section container
                    if len(child_children) >= 2 or len(children) >= 3:
                        add_summary(child, tag, rect, inner_html_length)
                    # If few siblings and this element has children, recurse
                    elif len(children) < 3 and child_children:
                        logger.info(f"AI Divider: diving into '{tag}' with {len(child_children)} children")
                        collect_sections(child_children, depth + 1)
                    else:
                        add_summary(child, tag, rect, inner_html_length)

        def add_summary(child: Dict[str, Any], tag: str, rect: Dict, inner_html_length: int) -> None:
            """Add a TopLevelDivSummary to the list"""
            summaries.append(TopLevelDivSummary(
                index=len(summaries),
                tag=tag,
                id=child.get("id"),
                classes=child.get("classes", [])[:5],
                rect={
                    "x": rect.get("x", 0),
                    "y": rect.get("y", 0),
                    "width": rect.get("width", 0),
                    "height": rect.get("height", 0),
                },
                inner_html_length=inner_html_length,
                estimated_tokens=inner_html_length // 4,
            ))
            logger.info(f"AI Divider: added [{len(summaries)-1}] {tag}#{child.get('id') or ''} rect={rect}")

        # Start from body
        body = find_body(dom_tree)
        if not body:
            logger.warning("AI Divider: no body element found in DOM tree")
            return summaries

        # Unwrap single-child containers to find the real content level
        logger.info("AI Divider: starting element extraction...")
        content_children = unwrap_single_child_containers(body)

        if not content_children:
            logger.warning("AI Divider: no visible content children found")
            return summaries

        logger.info(f"AI Divider: found {len(content_children)} content children after unwrapping")

        # Collect sections from the content level
        collect_sections(content_children)

        # If we still only got 1 element, try going one level deeper
        if len(summaries) == 1:
            logger.info("AI Divider: only 1 element found, trying to go deeper...")
            single_element = content_children[0] if content_children else None
            if single_element:
                deeper_children = get_visible_children(single_element)
                if len(deeper_children) >= 2:
                    summaries.clear()
                    collect_sections(deeper_children)

        logger.info(f"AI Divider: extracted {len(summaries)} elements for analysis")
        return summaries

    def format_div_summary(self, divs: List[TopLevelDivSummary]) -> str:
        """
        Format div summary for LLM prompt - clear and easy to read
        """
        lines = []
        for d in divs:
            # Build element identifier
            tag_str = d.tag
            if d.id:
                tag_str += f"#{d.id}"
            if d.classes:
                tag_str += f".{d.classes[0]}"

            # Position info
            y_pos = int(d.rect['y'])
            height = int(d.rect['height'])

            # Token estimate
            token_str = f"~{d.estimated_tokens/1000:.1f}K" if d.estimated_tokens >= 1000 else f"~{d.estimated_tokens}"

            lines.append(
                f"[{d.index}] {tag_str} — y:{y_pos}px, h:{height}px, {token_str} tokens"
            )
        return "\n".join(lines)

    async def analyze(
        self,
        url: str,
        screenshot: Optional[str],
        dom_tree: Dict[str, Any],
        viewport_width: int = 1920,
        viewport_height: int = 1080,
        page_height: int = 1080,
        use_cache: bool = True,
        use_screenshot: bool = True,
    ) -> AIDivisionResult:
        """
        Main entry point: analyze page and return AI divisions

        Args:
            url: Page URL
            screenshot: Base64 encoded screenshot (can be None if use_screenshot=False)
            dom_tree: DOM tree dict from Playwright extractor
            viewport_width: Viewport width
            viewport_height: Viewport height
            page_height: Full page height
            use_cache: Whether to use cache
            use_screenshot: Whether to include screenshot in LLM call (default True)
                           Set to False to use layout data only (avoids image size limits)

        Returns:
            AIDivisionResult with divisions and validation
        """
        start_time = datetime.now()

        # Check cache first (cache key includes mode: visual vs layout-only)
        if use_cache:
            cached = ai_divider_cache.get(url, use_screenshot)
            if cached:
                logger.info(f"AI Divider: cache hit for {url} (mode={'visual' if use_screenshot else 'layout'})")
                return cached

        # Check if client is available
        if self.client is None:
            return AIDivisionResult(
                success=False,
                error="No LLM API key configured. Please configure ANTHROPIC_API_KEY or Claude proxy settings.",
            )

        # Extract top-level divs
        top_level_divs = self.extract_top_level_divs(dom_tree)

        if not top_level_divs:
            return AIDivisionResult(
                success=False,
                error="No visible top-level elements found in DOM tree",
            )

        logger.info(f"AI Divider: extracted {len(top_level_divs)} top-level divs from {url}")

        # Screenshot is optional - we can analyze with layout data only
        if not screenshot and use_screenshot:
            logger.info("AI Divider: No screenshot provided, switching to layout-only mode")
            use_screenshot = False

        # Build prompt
        div_summary = self.format_div_summary(top_level_divs)
        max_index = len(top_level_divs) - 1
        user_prompt = USER_PROMPT_TEMPLATE.format(
            url=url,
            viewport_width=viewport_width,
            page_height=page_height,
            total_divs=len(top_level_divs),
            div_summary=div_summary,
            max_index=max_index,
        )

        logger.info(f"AI Divider: sending request to LLM (provider={self.provider}, model={self.model})")
        logger.debug(f"AI Divider prompt:\n{user_prompt}")

        # Call LLM with retry
        last_error = None
        retry_count = 0

        for attempt in range(self.MAX_RETRIES):
            try:
                # Always pass screenshot - it's the primary reference
                response_text = await self._call_llm(user_prompt, screenshot)
                logger.info(f"AI Divider: received response from LLM (attempt {attempt + 1})")
                divisions = self._parse_response(response_text, top_level_divs)
                validation = self._validate_divisions(divisions, top_level_divs, page_height)

                processing_time = int((datetime.now() - start_time).total_seconds() * 1000)

                result = AIDivisionResult(
                    success=True,
                    divisions=divisions,
                    validation=validation,
                    processing_time_ms=processing_time,
                    retry_count=retry_count,
                )

                # Cache successful result (cache key includes mode)
                if use_cache:
                    ai_divider_cache.set(url, result, use_screenshot)

                return result

            except Exception as e:
                last_error = str(e)
                retry_count = attempt + 1
                logger.warning(f"AI Divider attempt {attempt + 1} failed: {e}")

                if attempt < self.MAX_RETRIES - 1:
                    # Exponential backoff
                    await asyncio.sleep(2 ** attempt)

        # All retries failed
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        return AIDivisionResult(
            success=False,
            error=f"AI analysis failed after {self.MAX_RETRIES} retries: {last_error}",
            retry_count=retry_count,
            processing_time_ms=processing_time,
        )

    def _resize_image_if_needed(self, screenshot_base64: str, max_dimension: int = 7500) -> str:
        """
        Resize image if any dimension exceeds max_dimension.
        Anthropic API has a limit of 8000 pixels per dimension.
        We use 7500 to leave some margin.
        """
        import base64
        from io import BytesIO

        try:
            # Import PIL
            from PIL import Image

            # Decode base64
            image_data = base64.b64decode(screenshot_base64)
            image = Image.open(BytesIO(image_data))

            width, height = image.size
            logger.info(f"Original image size: {width}x{height}")

            # Check if resize is needed
            if width <= max_dimension and height <= max_dimension:
                return screenshot_base64

            # Calculate new size maintaining aspect ratio
            if width > height:
                new_width = max_dimension
                new_height = int(height * (max_dimension / width))
            else:
                new_height = max_dimension
                new_width = int(width * (max_dimension / height))

            logger.info(f"Resizing image to: {new_width}x{new_height}")

            # Resize
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # Convert back to base64
            buffer = BytesIO()
            image.save(buffer, format="PNG", optimize=True)
            resized_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

            return resized_base64

        except ImportError:
            logger.warning("PIL not installed, cannot resize image. Install with: pip install Pillow")
            return screenshot_base64
        except Exception as e:
            logger.warning(f"Failed to resize image: {e}")
            return screenshot_base64

    async def _call_llm(self, user_prompt: str, screenshot: Optional[str] = None) -> str:
        """
        Call LLM API with optional vision capability
        Supports both Gemini (OpenAI format) and Claude (Anthropic format)

        Args:
            user_prompt: The text prompt with div summary
            screenshot: Optional base64 encoded screenshot (can be None for text-only mode)
        """
        # Clean screenshot data URL if present
        if screenshot and "," in screenshot:
            screenshot = screenshot.split(",")[1]

        # Resize image if needed
        if screenshot:
            screenshot = self._resize_image_if_needed(screenshot)

        if self.provider == "gemini":
            return await self._call_gemini(user_prompt, screenshot)
        else:
            return await self._call_claude(user_prompt, screenshot)

    async def _call_gemini(self, user_prompt: str, screenshot: Optional[str] = None) -> str:
        """Call Gemini API using OpenAI-compatible format"""
        # Build message content
        content = []

        # Add image if provided
        if screenshot:
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{screenshot}"
                }
            })

        # Add text prompt
        content.append({
            "type": "text",
            "text": user_prompt
        })

        # Call using OpenAI format
        response = await self.client.chat.completions.create(
            model=self.model,
            max_tokens=4096,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": content}
            ]
        )
        return response.choices[0].message.content

    async def _call_claude(self, user_prompt: str, screenshot: Optional[str] = None) -> str:
        """Call Claude API using Anthropic format"""
        # Build message content
        content = []

        # Add image if provided (screenshot is primary reference)
        if screenshot:
            logger.info(f"AI Divider: including screenshot in request (size: {len(screenshot)} chars)")
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": screenshot
                }
            })

        # Add text prompt
        content.append({
            "type": "text",
            "text": user_prompt
        })

        logger.info(f"AI Divider: calling Claude API (model={self.model})")

        try:
            # Call using Anthropic format
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                messages=[
                    {"role": "user", "content": content}
                ]
            )
            logger.info(f"AI Divider: Claude API response received")
            return response.content[0].text
        except Exception as e:
            logger.error(f"AI Divider: Claude API error: {e}")
            raise

    def _parse_response(self, response: str, divs: List[TopLevelDivSummary]) -> List[AIDivisionInfo]:
        """
        Parse LLM response into AIDivisionInfo list

        Tool Logic:
        1. LLM returns JSON with div_indices for each section
        2. We look up the rect for each div_index from our divs list
        3. Merge all rects to get the section's bounding box
        """
        logger.info(f"AI Divider: parsing LLM response...")
        logger.info(f"AI Divider: raw response preview:\n{response[:1000]}...")

        # Log available divs for reference
        logger.info(f"AI Divider: available {len(divs)} elements:")
        for d in divs:
            logger.info(f"  [{d.index}] {d.tag}#{d.id or ''}.{d.classes[0] if d.classes else ''} -> rect={d.rect}")

        # Try to extract JSON from response
        try:
            data = json.loads(response)
        except json.JSONDecodeError:
            # Try to find JSON in response (may have markdown or extra text)
            json_match = re.search(r'\{[\s\S]*\}', response)
            if not json_match:
                raise ValueError(f"No valid JSON found in LLM response: {response[:200]}")
            data = json.loads(json_match.group())

        divisions = []
        raw_divisions = data.get("divisions", [])

        logger.info(f"AI Divider: LLM returned {len(raw_divisions)} divisions")

        for idx, d in enumerate(raw_divisions):
            div_indices = d.get("div_indices", [])
            name = d.get("name", f"Section {idx + 1}")

            logger.info(f"AI Divider: Division '{name}' has div_indices={div_indices}")

            # Validate indices - must be within range
            valid_indices = [i for i in div_indices if 0 <= i < len(divs)]

            if not valid_indices:
                logger.warning(f"AI Divider: Division '{name}' has no valid indices (got {div_indices}, max is {len(divs)-1})")
                # Use fallback - assign sequential index
                if idx < len(divs):
                    valid_indices = [idx]
                    logger.info(f"AI Divider: Using fallback index [{idx}] for '{name}'")
                else:
                    continue

            # Get rects for each valid index
            rects_to_merge = []
            for i in valid_indices:
                rect = divs[i].rect
                logger.info(f"AI Divider:   Index [{i}] -> rect={rect}")
                rects_to_merge.append(rect)

            # Merge rects from included divs
            merged_rect = self._merge_rects(rects_to_merge)
            total_tokens = sum(divs[i].estimated_tokens for i in valid_indices)

            logger.info(f"AI Divider: Division '{name}' -> merged_rect={merged_rect}")

            divisions.append(AIDivisionInfo(
                id=f"ai-division-{idx + 1}",
                name=name,
                type=d.get("type", "section"),
                description=d.get("description", ""),
                div_indices=valid_indices,
                rect=merged_rect,
                estimated_tokens=total_tokens,
                priority=d.get("priority", idx + 1),
            ))

        logger.info(f"AI Divider: parsed {len(divisions)} valid divisions")

        # Post-process: fix overlapping and split large sections
        divisions = self._fix_overlapping_and_split(divisions, divs)

        return divisions

    def _fix_overlapping_and_split(
        self,
        divisions: List[AIDivisionInfo],
        divs: List[TopLevelDivSummary]
    ) -> List[AIDivisionInfo]:
        """
        Post-process divisions to ensure:
        1. No overlapping indices (remove duplicates, keep first occurrence)
        2. All indices are assigned (add missing to nearest section)
        3. No section exceeds 10K tokens (split if needed)
        """
        if not divisions:
            return divisions

        logger.info("AI Divider: Post-processing - fixing overlaps and splits...")

        # Step 1: Remove duplicate indices (keep first occurrence)
        used_indices = set()
        for division in divisions:
            unique_indices = []
            for idx in division.div_indices:
                if idx not in used_indices:
                    unique_indices.append(idx)
                    used_indices.add(idx)
            division.div_indices = unique_indices

        # Step 2: Add missing indices to nearest section by y-position
        all_indices = set(range(len(divs)))
        missing_indices = all_indices - used_indices

        if missing_indices:
            logger.info(f"AI Divider: Adding {len(missing_indices)} missing indices: {sorted(missing_indices)}")

            for missing_idx in sorted(missing_indices):
                missing_rect = divs[missing_idx].rect
                missing_y = missing_rect.get("y", 0)

                # Find the division with the closest y-position
                best_division = None
                best_distance = float('inf')

                for division in divisions:
                    if division.div_indices:
                        # Get the y-range of this division
                        div_rects = [divs[i].rect for i in division.div_indices if i < len(divs)]
                        if div_rects:
                            min_y = min(r.get("y", 0) for r in div_rects)
                            max_y = max(r.get("y", 0) + r.get("height", 0) for r in div_rects)

                            # Distance to this division's range
                            if min_y <= missing_y <= max_y:
                                distance = 0
                            else:
                                distance = min(abs(missing_y - min_y), abs(missing_y - max_y))

                            if distance < best_distance:
                                best_distance = distance
                                best_division = division

                if best_division:
                    best_division.div_indices.append(missing_idx)
                    best_division.div_indices.sort()
                    logger.info(f"AI Divider: Added index [{missing_idx}] to '{best_division.name}'")

        # Step 3: Recalculate rects and tokens for all divisions
        for division in divisions:
            if division.div_indices:
                rects = [divs[i].rect for i in division.div_indices if i < len(divs)]
                division.rect = self._merge_rects(rects)
                division.estimated_tokens = sum(
                    divs[i].estimated_tokens for i in division.div_indices if i < len(divs)
                )

        # Step 4: Split divisions that exceed 10K tokens
        MAX_TOKENS = 10000
        final_divisions = []

        for division in divisions:
            if division.estimated_tokens <= MAX_TOKENS:
                final_divisions.append(division)
            else:
                # Split this division
                logger.info(f"AI Divider: Splitting '{division.name}' ({division.estimated_tokens} tokens)")
                split_divisions = self._split_large_division(division, divs, MAX_TOKENS)
                final_divisions.extend(split_divisions)

        # Re-number IDs and priorities
        for i, division in enumerate(final_divisions):
            division.id = f"ai-division-{i + 1}"
            division.priority = i + 1

        logger.info(f"AI Divider: Post-processing complete, {len(final_divisions)} divisions")
        return final_divisions

    def _split_large_division(
        self,
        division: AIDivisionInfo,
        divs: List[TopLevelDivSummary],
        max_tokens: int
    ) -> List[AIDivisionInfo]:
        """
        Split a large division into smaller parts, each under max_tokens.
        Split by consecutive indices to maintain visual coherence.
        """
        if not division.div_indices:
            return [division]

        # Sort indices by y-position
        sorted_indices = sorted(
            division.div_indices,
            key=lambda i: divs[i].rect.get("y", 0) if i < len(divs) else 0
        )

        split_parts = []
        current_indices = []
        current_tokens = 0
        part_num = 1

        for idx in sorted_indices:
            if idx >= len(divs):
                continue

            idx_tokens = divs[idx].estimated_tokens

            # If adding this index would exceed max, start a new part
            if current_indices and current_tokens + idx_tokens > max_tokens:
                # Save current part
                split_parts.append(self._create_split_part(
                    division, current_indices, divs, part_num
                ))
                part_num += 1
                current_indices = []
                current_tokens = 0

            current_indices.append(idx)
            current_tokens += idx_tokens

        # Add the last part
        if current_indices:
            split_parts.append(self._create_split_part(
                division, current_indices, divs, part_num
            ))

        logger.info(f"AI Divider: Split '{division.name}' into {len(split_parts)} parts")
        return split_parts

    def _create_split_part(
        self,
        original: AIDivisionInfo,
        indices: List[int],
        divs: List[TopLevelDivSummary],
        part_num: int
    ) -> AIDivisionInfo:
        """Create a split part from original division"""
        rects = [divs[i].rect for i in indices if i < len(divs)]
        total_tokens = sum(divs[i].estimated_tokens for i in indices if i < len(divs))

        return AIDivisionInfo(
            id=f"{original.id}-part{part_num}",
            name=f"{original.name} (Part {part_num})" if part_num > 1 else original.name,
            type=original.type,
            description=original.description,
            div_indices=indices,
            rect=self._merge_rects(rects),
            estimated_tokens=total_tokens,
            priority=original.priority,
        )

    def _merge_rects(self, rects: List[Dict[str, float]]) -> Dict[str, float]:
        """
        Merge multiple rects into a bounding box
        """
        if not rects:
            return {"x": 0, "y": 0, "width": 0, "height": 0}

        min_x = min(r.get("x", 0) for r in rects)
        min_y = min(r.get("y", 0) for r in rects)
        max_right = max(r.get("x", 0) + r.get("width", 0) for r in rects)
        max_bottom = max(r.get("y", 0) + r.get("height", 0) for r in rects)

        return {
            "x": min_x,
            "y": min_y,
            "width": max_right - min_x,
            "height": max_bottom - min_y,
        }

    def _validate_divisions(
        self,
        divisions: List[AIDivisionInfo],
        divs: List[TopLevelDivSummary],
        page_height: int
    ) -> ValidationResult:
        """
        Validate divisions for mutual exclusivity and full coverage
        """
        validation = ValidationResult()

        # Check mutual exclusivity
        used_indices = set()
        overlapping = []

        for d in divisions:
            for idx in d.div_indices:
                if idx in used_indices:
                    overlapping.append(idx)
                used_indices.add(idx)

        if overlapping:
            validation.is_mutually_exclusive = False
            validation.overlapping_indices = list(set(overlapping))
            logger.warning(f"AI Divider: overlapping indices detected: {overlapping}")

        # Check full coverage
        all_indices = set(range(len(divs)))
        missing = all_indices - used_indices

        if missing:
            validation.covers_full_page = False
            validation.missing_indices = list(missing)
            logger.warning(f"AI Divider: missing indices: {missing}")

        # Check large divisions (> 10K chars)
        for d in divisions:
            estimated_chars = d.estimated_tokens * 4
            if estimated_chars > self.LARGE_DIVISION_THRESHOLD:
                validation.large_divisions.append({
                    "id": d.id,
                    "name": d.name,
                    "estimated_tokens": d.estimated_tokens,
                    "estimated_chars": estimated_chars,
                    "suggestion": "Consider splitting into sub-sections for better processing",
                })

        return validation


# ==================== Module-level Instance ====================

# Create singleton instance
ai_divider = AIDivider()
