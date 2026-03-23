"use client";

import { useEffect, useState } from "react";
import { Sidebar } from "@/components/sidebar/Sidebar";
import { ChatArea } from "@/components/chat/ChatArea";
import { useChat } from "@/hooks/useChat";
import { useDocuments } from "@/hooks/useDocuments";
import { fetchStatus } from "@/lib/api";
import type { ChatSettings, PipelineStatus } from "@/lib/types";

const DEFAULT_SETTINGS: ChatSettings = {
  score_threshold: 0.3,
  fallback_enabled: true,
  k: 4,
};

export default function AppShell() {
  const [settings, setSettings] = useState<ChatSettings>(DEFAULT_SETTINGS);
  const [status, setStatus] = useState<PipelineStatus | null>(null);

  const { documents, isLoading, isUploading, isRebuilding, upload, remove, rebuild } =
    useDocuments();
  const { messages, isStreaming, sendMessage, clearHistory, exportChat } =
    useChat(settings);

  // Récupération du statut pipeline au démarrage
  useEffect(() => {
    fetchStatus()
      .then(setStatus)
      .catch(() => {
        // Statut indisponible — le backend n'est pas encore prêt
      });
  }, []);

  const docCount = documents.length;
  const llmLabel = status?.llm_label ?? "LLM";

  return (
    <div className="flex h-full">
      <Sidebar
        documents={documents}
        isLoading={isLoading}
        isUploading={isUploading}
        isRebuilding={isRebuilding}
        onUpload={upload}
        onRemove={remove}
        onRebuild={rebuild}
        settings={settings}
        onSettingsChange={setSettings}
        onClearHistory={clearHistory}
        onExportChat={exportChat}
      />
      <main className="flex-1 min-w-0 h-full">
        <ChatArea
          messages={messages}
          isStreaming={isStreaming}
          sendMessage={sendMessage}
          docCount={docCount}
          llmLabel={llmLabel}
        />
      </main>
    </div>
  );
}
