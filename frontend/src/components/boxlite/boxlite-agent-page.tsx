"use client";

import React, { useState, useCallback, useEffect, useRef } from "react";
import { RefreshCw } from "lucide-react";
import { cn } from "@/lib/utils";
import { useBoxLite } from "@/hooks/use-boxlite";
import { BoxLiteIDE } from "./boxlite-ide";
import { ProjectHeader } from "./project-header";
import { SourcePanel, type SavedSource } from "./source-panel";
import { AppSidebar } from "@/components/app-sidebar";
import { NextingAgentChatPanel } from "@/components/agent/chat-panel";
import type { ChatMessage } from "@/types/agent";
import type { BoxLiteSandboxState } from "@/types/boxlite";

// ============================================
// Types
// ============================================

interface SelectedSource {
  id: string;
  title: string;
  url: string;
  theme: "light" | "dark";
}

// ============================================
// Main BoxLite Agent Page
// ============================================

export function BoxLiteAgentPage() {
  // Sandbox hook (BoxLite infra)
  const {
    state,
    isConnected,
    isInitialized,
    error,
    readFile,
    writeFile,
    runCommand,
    startDevServer,
    stopDevServer,
    getTerminalOutput,
    sendTerminalInput,
    executeTool,
    agentLogs,
    addAgentLog,
    fileDiffs,
    clearFileDiff,
    updateState,  // For syncing Agent WebSocket state_update
  } = useBoxLite({
    autoInit: true,
    onFileWritten: (path) => {
      console.log("[Sandbox] File written:", path);
    },
  });

  // UI State
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [fileContent, setFileContent] = useState("");
  const [chatPanelWidth, setChatPanelWidth] = useState(380);
  const [showChatPanel, setShowChatPanel] = useState(true);
  const [showSourcePanel, setShowSourcePanel] = useState(false);
  const [projectName, setProjectName] = useState("Untitled Project");
  const [selectedSource, setSelectedSource] = useState<SelectedSource | null>(null);
  const [isAgentLoading, setIsAgentLoading] = useState(false);

  // Resizer state
  const [isResizing, setIsResizing] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // Handle file selection
  const handleFileSelect = useCallback(
    async (path: string) => {
      setSelectedFile(path);
      const content = await readFile(path);
      setFileContent(content || "");
    },
    [readFile]
  );

  // Handle file save
  const handleSaveFile = useCallback(async () => {
    if (selectedFile && fileContent) {
      await writeFile(selectedFile, fileContent);
      addAgentLog({
        type: "file",
        content: `Saved: ${selectedFile}`,
        timestamp: Date.now(),
      });
    }
  }, [selectedFile, fileContent, writeFile, addAgentLog]);

  // Handle file creation
  const handleFileCreate = useCallback(
    async (path: string, content: string) => {
      await writeFile(path, content);
    },
    [writeFile]
  );

  // Handle file deletion
  const handleFileDelete = useCallback(
    async (path: string) => {
      await executeTool("delete_file", { path });
    },
    [executeTool]
  );

  // Handle terminal input
  const handleTerminalInput = useCallback(
    async (input: string) => {
      const terminalId = state?.active_terminal_id;
      if (terminalId) {
        await sendTerminalInput(terminalId, input);
      } else {
        await runCommand(input.trim());
      }
    },
    [state, sendTerminalInput, runCommand]
  );

  // Handle BoxLite state update from Agent WebSocket
  // This syncs the Agent's state_update events with the useBoxLite hook's state
  const handleBoxLiteStateUpdate = useCallback((newState: BoxLiteSandboxState) => {
    console.log("[BoxLiteAgentPage] Received state_update, syncing with hook");
    updateState(newState);
  }, [updateState]);

  // Handle clearing file diffs
  const handleClearFileDiffs = useCallback(() => {
    Object.keys(fileDiffs.diffs).forEach((path) => clearFileDiff(path));
  }, [fileDiffs.diffs, clearFileDiff]);

  // Handle source selection
  const handleSelectSource = useCallback((source: SavedSource) => {
    setSelectedSource({
      id: source.id,
      title: source.page_title || "Untitled",
      url: source.source_url,
      theme: source.metadata?.theme || "light",
    });
  }, []);

  // Handle resizing
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    setIsResizing(true);
  }, []);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isResizing || !containerRef.current) return;
      const containerRect = containerRef.current.getBoundingClientRect();
      // Calculate width relative to main content area (after sidebar)
      const sidebarWidth = 56; // collapsed sidebar width
      const newWidth = e.clientX - containerRect.left;
      setChatPanelWidth(Math.max(280, Math.min(600, newWidth)));
    };

    const handleMouseUp = () => {
      setIsResizing(false);
    };

    if (isResizing) {
      document.addEventListener("mousemove", handleMouseMove);
      document.addEventListener("mouseup", handleMouseUp);
      document.body.style.userSelect = "none";
      document.body.style.cursor = "col-resize";
    }

    return () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
      document.body.style.userSelect = "";
      document.body.style.cursor = "";
    };
  }, [isResizing]);

  // Show loading state
  if (!isInitialized) {
    return (
      <div className="flex h-screen bg-white dark:bg-neutral-900">
        <AppSidebar currentPage="agent" />
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center text-neutral-900 dark:text-white">
            <RefreshCw className="h-12 w-12 animate-spin mx-auto mb-4 text-violet-500" />
            <p className="text-lg font-medium">Initializing Nexting Agent...</p>
            {error && <p className="text-red-500 mt-2">{error}</p>}
          </div>
        </div>
      </div>
    );
  }

  // Map BoxLite status to ProjectHeader status
  const getStatus = () => {
    if (!isConnected) return "idle";
    if (state?.status === "ready") return "ready";
    if (state?.status === "error") return "error";
    return "booting";
  };

  return (
    <div className="flex h-screen bg-white dark:bg-neutral-900">
      {/* Navigation Sidebar */}
      <AppSidebar currentPage="agent" />

      {/* Main Content */}
      <main className="flex-1 overflow-hidden flex flex-col min-w-0">
        {/* Project Header */}
        <ProjectHeader
          projectName={projectName}
          onProjectNameChange={setProjectName}
          showChatPanel={showChatPanel}
          onToggleChatPanel={() => setShowChatPanel(!showChatPanel)}
          showSourcePanel={showSourcePanel}
          onToggleSourcePanel={() => setShowSourcePanel(!showSourcePanel)}
          status={getStatus()}
        />

        {/* Content Area */}
        <div ref={containerRef} className="flex-1 flex overflow-hidden min-h-0">
          {/* AI Chat Panel (Left) */}
          <div
            className="flex-shrink-0 overflow-hidden"
            style={{
              width: `${chatPanelWidth}px`,
              display: showChatPanel ? "block" : "none",
            }}
          >
            {state?.sandbox_id ? (
              <NextingAgentChatPanel
                mode="boxlite"
                sandboxId={state.sandbox_id}
                boxliteState={state}
                onBoxLiteStateUpdate={handleBoxLiteStateUpdate}
                messages={messages}
                onMessagesChange={setMessages}
                onClearFileDiffs={handleClearFileDiffs}
                selectedSource={selectedSource}
                onClearSource={() => setSelectedSource(null)}
                onLoadingChange={setIsAgentLoading}
                onProjectNameGenerated={setProjectName}
              />
            ) : (
              <div className="h-full flex items-center justify-center bg-neutral-50 dark:bg-neutral-900 text-neutral-500">
                <div className="text-center">
                  <RefreshCw className="h-8 w-8 animate-spin mx-auto mb-2" />
                  <p>Connecting to sandbox...</p>
                </div>
              </div>
            )}
          </div>

          {/* Resizable Divider */}
          <div
            className={cn(
              "flex-shrink-0 cursor-col-resize relative group",
              "transition-all duration-150",
              "w-px bg-neutral-200 dark:bg-neutral-700",
              "hover:w-1 hover:bg-violet-500 dark:hover:bg-violet-500",
              isResizing && "w-1 bg-violet-500 dark:bg-violet-500"
            )}
            style={{ display: showChatPanel ? "block" : "none" }}
            onMouseDown={handleMouseDown}
          >
            <div
              className={cn(
                "absolute inset-y-0 -left-1 -right-1",
                "group-hover:bg-violet-500/10",
                isResizing && "bg-violet-500/10"
              )}
            />
          </div>

          {/* IDE Panel (Center) */}
          <div className="flex-1 overflow-hidden min-w-0">
            <BoxLiteIDE
              state={state}
              isConnected={isConnected}
              agentLogs={agentLogs}
              fileDiffs={fileDiffs}
              onFileSelect={handleFileSelect}
              onFileCreate={handleFileCreate}
              onFileDelete={handleFileDelete}
              onDiffClear={clearFileDiff}
              onWriteFile={writeFile}
              onTerminalInput={handleTerminalInput}
              getTerminalOutput={getTerminalOutput}
              selectedFile={selectedFile}
              fileContent={fileContent}
              onContentChange={setFileContent}
              onSaveFile={handleSaveFile}
              isResizing={isResizing}
              selectedSource={selectedSource}
            />
          </div>

          {/* Source Panel (Right) */}
          {showSourcePanel && (
            <>
              {/* Divider */}
              <div
                className={cn(
                  "flex-shrink-0 w-px",
                  "bg-neutral-200 dark:bg-neutral-700"
                )}
              />
              <div className="flex-shrink-0 w-72 overflow-hidden">
                <SourcePanel
                  selectedSourceId={selectedSource?.id}
                  disabled={isAgentLoading}
                  onSelectSource={handleSelectSource}
                />
              </div>
            </>
          )}
        </div>
      </main>
    </div>
  );
}

export default BoxLiteAgentPage;
