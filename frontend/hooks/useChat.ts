"use client";

import { useCallback, useRef, useState } from "react";
import { streamChat } from "@/lib/api";
import type { ChatSettings, Citation, Message } from "@/lib/types";

function buildChatHistory(messages: Message[]): Array<[string, string]> {
  const history: Array<[string, string]> = [];
  for (let i = 0; i < messages.length - 1; i++) {
    const msg = messages[i];
    const next = messages[i + 1];
    if (msg.role === "user" && next?.role === "assistant" && !next.isStreaming) {
      history.push([msg.content, next.content]);
    }
  }
  return history.slice(-3);
}

function exportToMarkdown(messages: Message[]): string {
  const lines = ["# Knowledge Assistant — Conversation Export\n"];
  for (const msg of messages) {
    const role = msg.role === "user" ? "**You**" : "**Assistant**";
    lines.push(`${role}\n\n${msg.content}\n`);
    if (msg.citations.length > 0) {
      const sources = msg.citations.map(c => c.source).join(", ");
      lines.push(`*Sources: ${sources}*\n`);
    }
    lines.push("---\n");
  }
  return lines.join("\n");
}

export function useChat(settings: ChatSettings) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const abortRef = useRef<boolean>(false);

  const sendMessage = useCallback(async (text: string) => {
    if (isStreaming) return;

    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content: text,
      citations: [],
      isStreaming: false,
      isFallback: false,
    };

    const assistantId = crypto.randomUUID();
    const assistantPlaceholder: Message = {
      id: assistantId,
      role: "assistant",
      content: "",
      citations: [],
      isStreaming: true,
      isFallback: false,
    };

    setMessages(prev => {
      const updated = [...prev, userMessage, assistantPlaceholder];
      return updated;
    });
    setIsStreaming(true);
    abortRef.current = false;

    // Historique construit depuis les messages AVANT ajout de la question courante
    const history = buildChatHistory([...messages, userMessage]);

    await streamChat(text, history, settings, {
      onToken: (token) => {
        if (abortRef.current) return;
        setMessages(prev =>
          prev.map(m => m.id === assistantId ? { ...m, content: m.content + token } : m)
        );
      },
      onSources: (citations: Citation[]) => {
        setMessages(prev =>
          prev.map(m => m.id === assistantId ? { ...m, citations } : m)
        );
      },
      onDone: (isFallback: boolean) => {
        setMessages(prev =>
          prev.map(m => m.id === assistantId ? { ...m, isStreaming: false, isFallback } : m)
        );
        setIsStreaming(false);
      },
      onError: (message: string) => {
        setMessages(prev =>
          prev.map(m =>
            m.id === assistantId
              ? { ...m, content: `Error: ${message}`, isStreaming: false }
              : m
          )
        );
        setIsStreaming(false);
      },
    });
  }, [isStreaming, messages, settings]);

  const clearHistory = useCallback(() => {
    setMessages([]);
    setIsStreaming(false);
  }, []);

  const exportChat = useCallback(() => {
    const md = exportToMarkdown(messages);
    const blob = new Blob([md], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "conversation.md";
    a.click();
    URL.revokeObjectURL(url);
  }, [messages]);

  return { messages, isStreaming, sendMessage, clearHistory, exportChat };
}
