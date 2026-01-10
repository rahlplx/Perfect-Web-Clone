"use client";

import React, { useState, useRef, useEffect } from "react";
import { cn } from "@/lib/utils";
import { Bot, Database, Settings } from "lucide-react";

/**
 * Project Header Props
 */
interface ProjectHeaderProps {
  projectName: string;
  onProjectNameChange: (name: string) => void;
  showChatPanel: boolean;
  onToggleChatPanel: () => void;
  showSourcePanel: boolean;
  onToggleSourcePanel: () => void;
  status?: "idle" | "ready" | "booting" | "error";
}

/**
 * Project Header Component
 * 顶部栏，包含项目名称和控制按钮
 */
export function ProjectHeader({
  projectName,
  onProjectNameChange,
  showChatPanel,
  onToggleChatPanel,
  showSourcePanel,
  onToggleSourcePanel,
  status = "idle",
}: ProjectHeaderProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [editValue, setEditValue] = useState(projectName);
  const inputRef = useRef<HTMLInputElement>(null);

  // Focus input when editing starts
  useEffect(() => {
    if (isEditing && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [isEditing]);

  const handleSave = () => {
    if (editValue.trim()) {
      onProjectNameChange(editValue.trim());
    } else {
      setEditValue(projectName);
    }
    setIsEditing(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      handleSave();
    } else if (e.key === "Escape") {
      setEditValue(projectName);
      setIsEditing(false);
    }
  };

  // Status indicator colors
  const statusColors: Record<string, string> = {
    booting: "bg-yellow-500",
    ready: "bg-green-500",
    error: "bg-red-500",
    idle: "bg-neutral-400",
  };

  const statusLabels: Record<string, string> = {
    booting: "Starting...",
    ready: "Ready",
    error: "Error",
    idle: "Idle",
  };

  return (
    <div
      className={cn(
        "flex items-center justify-between px-4 py-1.5 flex-shrink-0",
        "border-b border-neutral-200 dark:border-neutral-700",
        "bg-white dark:bg-neutral-900"
      )}
    >
      {/* Left: Project Name + Status */}
      <div className="flex items-center gap-3">
        {/* Project Name */}
        {isEditing ? (
          <input
            ref={inputRef}
            type="text"
            value={editValue}
            onChange={(e) => setEditValue(e.target.value)}
            onBlur={handleSave}
            onKeyDown={handleKeyDown}
            className={cn(
              "px-2 py-1 text-sm font-medium rounded border",
              "bg-white dark:bg-neutral-800",
              "border-neutral-300 dark:border-neutral-600",
              "text-neutral-900 dark:text-white",
              "focus:outline-none focus:ring-2 focus:ring-violet-500"
            )}
          />
        ) : (
          <button
            onClick={() => setIsEditing(true)}
            className={cn(
              "px-2 py-1 text-sm font-medium rounded",
              "text-neutral-900 dark:text-white",
              "hover:bg-neutral-100 dark:hover:bg-neutral-800",
              "transition-colors"
            )}
          >
            {projectName}
          </button>
        )}

        {/* Status Indicator */}
        <div className="flex items-center gap-1.5 text-xs text-neutral-500 dark:text-neutral-400">
          <span className={cn("w-2 h-2 rounded-full", statusColors[status])} />
          <span>{statusLabels[status]}</span>
        </div>
      </div>

      {/* Right: Actions */}
      <div className="flex items-center gap-2">
        {/* Toggle Source Panel */}
        <button
          onClick={onToggleSourcePanel}
          className={cn(
            "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors",
            showSourcePanel
              ? "bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-400"
              : "text-neutral-600 dark:text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-800"
          )}
        >
          <Database className="h-4 w-4" />
          Sources
        </button>

        {/* Toggle Chat Panel */}
        <button
          onClick={onToggleChatPanel}
          className={cn(
            "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors",
            showChatPanel
              ? "bg-neutral-200 dark:bg-neutral-700 text-neutral-800 dark:text-neutral-200"
              : "text-neutral-600 dark:text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-800"
          )}
        >
          <Bot className="h-4 w-4" />
          AI Assistant
        </button>

        {/* Settings */}
        <button
          className={cn(
            "p-2 rounded-lg transition-colors",
            "text-neutral-500 dark:text-neutral-400",
            "hover:bg-neutral-100 dark:hover:bg-neutral-800"
          )}
        >
          <Settings className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
