"use client";

import React, { useState, useCallback, useMemo, useEffect } from "react";
import {
  Brain,
  Loader2,
  AlertCircle,
  CheckCircle,
  RefreshCw,
  ZoomIn,
  ZoomOut,
  Maximize2,
  Clock,
  Layers,
  AlertTriangle,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type {
  ElementInfo,
  PageMetadata,
  AIDivision,
  AIDivisionResult,
} from "@/types/playwright";
import {
  analyzeWithAI,
  extractTopLevelDivs,
  DIVISION_TYPE_COLORS,
} from "@/lib/api/ai-divider";

/**
 * AI Div Tab Props
 */
interface AIDivTabProps {
  screenshot: string | null;
  fullPageScreenshot?: string | null;
  domTree: ElementInfo | null;
  metadata: PageMetadata | null;
  url: string;
  cachedResult?: AIDivisionResult | null;
  onResultChange?: (result: AIDivisionResult | null) => void;
}

/**
 * Division Overlay Component
 * Renders a single division overlay on the screenshot
 */
function DivisionOverlay({
  division,
  scale,
  offset,
  isSelected,
  onClick,
}: {
  division: AIDivision;
  scale: number;
  offset: { x: number; y: number };
  isSelected: boolean;
  onClick: () => void;
}) {
  const colors = DIVISION_TYPE_COLORS[division.type] || DIVISION_TYPE_COLORS.section;

  const style: React.CSSProperties = {
    position: "absolute",
    left: division.rect.x * scale + offset.x,
    top: division.rect.y * scale + offset.y,
    width: division.rect.width * scale,
    height: division.rect.height * scale,
    pointerEvents: "auto",
  };

  // Check if this is a large division (warning)
  const isLarge = division.estimatedTokens > 2500; // ~10K chars

  return (
    <div
      style={style}
      onClick={onClick}
      className={cn(
        "cursor-pointer transition-all duration-200",
        "border-2 border-dashed",
        colors.border,
        isSelected ? "border-solid border-[3px]" : "",
        isSelected ? colors.bg : "hover:bg-white/10 dark:hover:bg-black/10"
      )}
    >
      {/* Label */}
      <div
        className={cn(
          "absolute -top-6 left-0 px-2 py-0.5 rounded text-xs font-medium whitespace-nowrap",
          "bg-neutral-900/90 dark:bg-neutral-100/90",
          colors.text
        )}
      >
        <span className={cn("inline-block w-2 h-2 rounded-full mr-1.5", colors.bg.replace("/20", ""))} />
        {division.name}
        <span className="ml-2 opacity-70">
          ~{division.estimatedTokens >= 1000
            ? `${(division.estimatedTokens / 1000).toFixed(1)}K`
            : division.estimatedTokens} tokens
        </span>
        {isLarge && (
          <AlertTriangle className="inline-block ml-1 h-3 w-3 text-amber-400" />
        )}
      </div>
    </div>
  );
}

/**
 * Division List Item
 */
function DivisionListItem({
  division,
  isSelected,
  onClick,
}: {
  division: AIDivision;
  isSelected: boolean;
  onClick: () => void;
}) {
  const colors = DIVISION_TYPE_COLORS[division.type] || DIVISION_TYPE_COLORS.section;
  const isLarge = division.estimatedTokens > 2500;

  return (
    <div
      onClick={onClick}
      className={cn(
        "p-3 rounded-lg cursor-pointer transition-all border",
        "bg-white dark:bg-neutral-800",
        isSelected
          ? `${colors.border} border-2`
          : "border-neutral-200 dark:border-neutral-700 hover:border-neutral-300 dark:hover:border-neutral-600"
      )}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className={cn("w-3 h-3 rounded-full", colors.bg.replace("/20", ""))} />
          <span className="font-medium text-sm">{division.name}</span>
          <span className={cn("text-xs px-1.5 py-0.5 rounded", colors.bg, colors.text)}>
            {division.type}
          </span>
        </div>
        <div className="flex items-center gap-2 text-xs text-neutral-500 dark:text-neutral-400">
          <span>
            ~{division.estimatedTokens >= 1000
              ? `${(division.estimatedTokens / 1000).toFixed(1)}K`
              : division.estimatedTokens} tokens
          </span>
          {isLarge && (
            <AlertTriangle className="h-3.5 w-3.5 text-amber-500" />
          )}
        </div>
      </div>
      {division.description && (
        <p className="mt-1.5 text-xs text-neutral-600 dark:text-neutral-400">
          {division.description}
        </p>
      )}
      <div className="mt-2 flex items-center gap-3 text-xs text-neutral-500 dark:text-neutral-400">
        <span>
          Position: ({Math.round(division.rect.x)}, {Math.round(division.rect.y)})
        </span>
        <span>
          Size: {Math.round(division.rect.width)}x{Math.round(division.rect.height)}
        </span>
        <span>
          Divs: [{division.divIndices.join(", ")}]
        </span>
      </div>
    </div>
  );
}

/**
 * AI Div Tab Component
 * Shows AI-powered page division analysis
 */
export function AIDivTab({
  screenshot,
  fullPageScreenshot,
  domTree,
  metadata,
  url,
  cachedResult,
  onResultChange,
}: AIDivTabProps) {
  // Use full page screenshot if available, otherwise use viewport screenshot
  const displayScreenshot = fullPageScreenshot || screenshot;

  // Analysis state
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [result, setResult] = useState<AIDivisionResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  // UI state
  const [selectedDivision, setSelectedDivision] = useState<string | null>(null);
  const [scale, setScale] = useState(0.5);

  // Sync with cached result from parent (for backward compatibility)
  useEffect(() => {
    if (cachedResult) {
      setResult(cachedResult);
      if (cachedResult.error) {
        setError(cachedResult.error);
      }
    }
  }, [cachedResult]);

  // Computed values
  const topLevelDivs = useMemo(() => extractTopLevelDivs(domTree), [domTree]);
  const canAnalyze = displayScreenshot && domTree && url;

  /**
   * Handle analyze button click - call AI API
   */
  const handleAnalyze = useCallback(async () => {
    setIsAnalyzing(true);
    setError(null);
    setSelectedDivision(null);

    try {
      if (!displayScreenshot || !domTree || !url) {
        setError("Screenshot and DOM tree required for analysis");
        return;
      }

      const analysisResult = await analyzeWithAI({
        url,
        screenshot: displayScreenshot,
        domTree: domTree!,
        viewportWidth: metadata?.viewport_width || 1920,
        viewportHeight: metadata?.viewport_height || 1080,
        pageHeight: metadata?.page_height || 1080,
        useCache: true,
        useScreenshot: true,
      });

      console.log("[AI Div] Analysis result:", analysisResult);
      setResult(analysisResult);
      onResultChange?.(analysisResult);

      if (!analysisResult.success && analysisResult.error) {
        setError(analysisResult.error);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Analysis failed");
    } finally {
      setIsAnalyzing(false);
    }
  }, [displayScreenshot, domTree, url, metadata, onResultChange]);

  /**
   * Handle zoom controls
   */
  const handleZoomIn = useCallback(() => {
    setScale((s) => Math.min(s * 1.2, 2));
  }, []);

  const handleZoomOut = useCallback(() => {
    setScale((s) => Math.max(s / 1.2, 0.1));
  }, []);

  const handleResetZoom = useCallback(() => {
    setScale(0.5);
  }, []);

  // If no DOM data available, show placeholder
  // Note: screenshot is only required for Visual mode, not Layout Only mode
  if (!domTree) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-neutral-500 dark:text-neutral-400">
        <Brain className="h-12 w-12 mb-4 opacity-50" />
        <p className="text-lg font-medium mb-2">AI Smart Division</p>
        <p className="text-sm">Extract a page first to enable AI division analysis</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Control Bar */}
      <div className="flex items-center justify-between p-4 bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-purple-100 dark:bg-purple-900/30">
            <Brain className="h-5 w-5 text-purple-600 dark:text-purple-400" />
          </div>
          <div>
            <h3 className="font-semibold text-sm">AI Smart Division</h3>
            <p className="text-xs text-neutral-500 dark:text-neutral-400">
              {topLevelDivs.length} top-level elements detected
            </p>
          </div>
          {result?.fromCache && (
            <span className="px-2 py-0.5 text-xs font-medium rounded bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400">
              Cached
            </span>
          )}
        </div>

        <div className="flex items-center gap-3">
          {result && (
            <span className="text-xs text-neutral-500 dark:text-neutral-400 flex items-center gap-1">
              <Clock className="h-3.5 w-3.5" />
              {result.processingTimeMs}ms
            </span>
          )}
          <button
            onClick={handleAnalyze}
            disabled={isAnalyzing || !canAnalyze}
            className={cn(
              "flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors",
              "bg-purple-600 hover:bg-purple-700 text-white",
              "disabled:opacity-50 disabled:cursor-not-allowed"
            )}
          >
            {isAnalyzing ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Analyzing...
              </>
            ) : result ? (
              <>
                <RefreshCw className="h-4 w-4" />
                Re-analyze
              </>
            ) : (
              <>
                <Brain className="h-4 w-4" />
                Analyze with AI
              </>
            )}
          </button>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
          <div className="flex items-center gap-2 text-red-700 dark:text-red-400">
            <AlertCircle className="h-5 w-5" />
            <span className="font-medium">Analysis Failed</span>
          </div>
          <p className="mt-2 text-sm text-red-600 dark:text-red-400">{error}</p>
          {result?.retryCount && result.retryCount > 0 && (
            <p className="mt-1 text-xs text-red-500 dark:text-red-500">
              Attempted {result.retryCount} retries
            </p>
          )}
        </div>
      )}

      {/* Success Result */}
      {result?.success && (
        <>
          {/* Validation Warnings */}
          {result.validation && (!result.validation.isMutuallyExclusive || !result.validation.coversFullPage) && (
            <div className="p-4 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg">
              <div className="flex items-center gap-2 text-amber-700 dark:text-amber-400">
                <AlertTriangle className="h-5 w-5" />
                <span className="font-medium">Validation Warnings</span>
              </div>
              <ul className="mt-2 text-sm text-amber-600 dark:text-amber-400 list-disc list-inside">
                {!result.validation.isMutuallyExclusive && (
                  <li>Some divisions overlap (indices: {result.validation.overlappingIndices.join(", ")})</li>
                )}
                {!result.validation.coversFullPage && (
                  <li>Some elements not covered (indices: {result.validation.missingIndices.join(", ")})</li>
                )}
              </ul>
            </div>
          )}

          {/* Stats Bar */}
          <div className="flex items-center gap-4 px-4 py-2 bg-neutral-50 dark:bg-neutral-900 rounded-lg">
            <div className="flex items-center gap-2">
              <Layers className="h-4 w-4 text-neutral-500" />
              <span className="text-sm font-medium">{result.divisions.length} Divisions</span>
            </div>
            <div className="flex items-center gap-2">
              <CheckCircle className="h-4 w-4 text-green-500" />
              <span className="text-sm text-neutral-600 dark:text-neutral-400">
                {result.validation?.isMutuallyExclusive ? "No overlaps" : "Has overlaps"}
              </span>
            </div>
            {result.validation?.largeDivisions && result.validation.largeDivisions.length > 0 && (
              <div className="flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 text-amber-500" />
                <span className="text-sm text-amber-600 dark:text-amber-400">
                  {result.validation.largeDivisions.length} large section(s)
                </span>
              </div>
            )}
          </div>

          {/* Main Content: Preview (70%) + List (30%) */}
          <div className="grid grid-cols-1 lg:grid-cols-[7fr_3fr] gap-4">
            {/* Screenshot Visualization */}
            <div className="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 overflow-hidden">
              {/* Zoom Controls */}
              <div className="flex items-center justify-between px-3 py-2 border-b border-neutral-200 dark:border-neutral-700">
                <span className="text-xs font-medium text-neutral-500">
                  Visual Preview
                </span>
                <div className="flex items-center gap-1">
                  <button
                    onClick={handleZoomOut}
                    className="p-1.5 rounded hover:bg-neutral-100 dark:hover:bg-neutral-700 transition-colors"
                    title="Zoom out"
                  >
                    <ZoomOut className="h-4 w-4" />
                  </button>
                  <span className="text-xs text-neutral-500 w-12 text-center">
                    {Math.round(scale * 100)}%
                  </span>
                  <button
                    onClick={handleZoomIn}
                    className="p-1.5 rounded hover:bg-neutral-100 dark:hover:bg-neutral-700 transition-colors"
                    title="Zoom in"
                  >
                    <ZoomIn className="h-4 w-4" />
                  </button>
                  <button
                    onClick={handleResetZoom}
                    className="p-1.5 rounded hover:bg-neutral-100 dark:hover:bg-neutral-700 transition-colors"
                    title="Reset zoom"
                  >
                    <Maximize2 className="h-4 w-4" />
                  </button>
                </div>
              </div>

              {/* Screenshot with Overlays (Visual mode) or Layout Boxes (Layout Only mode) */}
              <div className="relative overflow-auto max-h-[600px] bg-neutral-100 dark:bg-neutral-900">
                <div
                  className="relative"
                  style={{
                    width: (metadata?.page_width || 1920) * scale + 40,
                    height: (metadata?.page_height || 1080) * scale + 40,
                  }}
                >
                  {/* Page Background */}
                  <div
                    className="absolute bg-white dark:bg-neutral-900 shadow-lg"
                    style={{
                      left: 20,
                      top: 20,
                      width: (metadata?.page_width || 1920) * scale,
                      height: (metadata?.page_height || 1080) * scale,
                    }}
                  />

                  {/* Screenshot */}
                  {displayScreenshot && (
                    <img
                      src={`data:image/png;base64,${displayScreenshot}`}
                      alt="Page screenshot"
                      className="absolute"
                      style={{
                        left: 20,
                        top: 20,
                        width: (metadata?.page_width || 1920) * scale,
                        height: "auto",
                      }}
                      draggable={false}
                    />
                  )}

                  {/* Division Overlays */}
                  <div className="absolute inset-0 pointer-events-none">
                    {result.divisions.map((division) => (
                      <DivisionOverlay
                        key={division.id}
                        division={division}
                        scale={scale}
                        offset={{ x: 20, y: 20 }}
                        isSelected={selectedDivision === division.id}
                        onClick={() => setSelectedDivision(
                          selectedDivision === division.id ? null : division.id
                        )}
                      />
                    ))}
                  </div>
                </div>
              </div>
            </div>

            {/* Division List */}
            <div className="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 overflow-hidden">
              <div className="px-3 py-2 border-b border-neutral-200 dark:border-neutral-700">
                <span className="text-xs font-medium text-neutral-500">
                  Division List ({result.divisions.length})
                </span>
              </div>
              <div className="p-3 space-y-2 max-h-[600px] overflow-auto">
                {result.divisions
                  .sort((a, b) => a.priority - b.priority)
                  .map((division) => (
                    <DivisionListItem
                      key={division.id}
                      division={division}
                      isSelected={selectedDivision === division.id}
                      onClick={() => setSelectedDivision(
                        selectedDivision === division.id ? null : division.id
                      )}
                    />
                  ))}
              </div>
            </div>
          </div>
        </>
      )}

      {/* Initial State - No Analysis Yet */}
      {!result && !error && !isAnalyzing && (
        <div className="flex flex-col items-center justify-center py-12 text-neutral-500 dark:text-neutral-400">
          <div className="p-4 rounded-full bg-purple-100 dark:bg-purple-900/30 mb-4">
            <Brain className="h-8 w-8 text-purple-600 dark:text-purple-400" />
          </div>
          <p className="text-lg font-medium mb-2">Ready to Analyze</p>
          <p className="text-sm text-center max-w-md mb-4">
            Click &quot;Analyze with AI&quot; to automatically divide the page into semantic sections.
          </p>
          <div className="text-xs text-neutral-400 dark:text-neutral-500 space-y-1 text-center">
            <p>{topLevelDivs.length} top-level elements will be analyzed</p>
            <p>AI will analyze the screenshot and layout data to identify semantic sections</p>
          </div>
        </div>
      )}
    </div>
  );
}
