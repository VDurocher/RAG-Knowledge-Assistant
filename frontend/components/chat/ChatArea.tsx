"use client";

import { useEffect, useRef } from "react";
import { AnimatePresence } from "framer-motion";
import { MessageBubble } from "./MessageBubble";
import { ThinkingIndicator } from "./ThinkingIndicator";
import { ChatInput } from "./ChatInput";
import type { Message } from "@/lib/types";
import { Sparkles } from "lucide-react";

interface ChatAreaProps {
  messages: Message[];
  isStreaming: boolean;
  sendMessage: (text: string) => void;
  docCount: number;
  llmLabel: string;
}

export function ChatArea({ messages, isStreaming, sendMessage, docCount, llmLabel }: ChatAreaProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll vers le bas à chaque nouveau message ou token
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const isEmpty = messages.length === 0;

  return (
    <div className="flex flex-col h-full">
      {/* En-tête */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-[#1a1530]">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-[#16112a] border border-[#2d1f5e] flex items-center justify-center">
            <span className="text-[#7c3aed] text-base" aria-hidden>⬡</span>
          </div>
          <div>
            <h1 className="text-sm font-semibold text-[#fafafa]">Knowledge Assistant</h1>
            <p className="text-[11px] text-[#52525b]">
              {docCount} document{docCount !== 1 ? "s" : ""} indexed
            </p>
          </div>
        </div>

        {/* Badge modèle */}
        <span className="text-[11px] text-[#52525b] bg-[#0f0d17] border border-[#1a1530] rounded-full px-3 py-1">
          {llmLabel}
        </span>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-6 space-y-6">
        {isEmpty ? (
          <EmptyState />
        ) : (
          <>
            <AnimatePresence initial={false}>
              {messages.map((msg: Message) => (
                <MessageBubble key={msg.id} message={msg} />
              ))}
            </AnimatePresence>

            {/* Indicateur de génération */}
            <AnimatePresence>
              {isStreaming && messages[messages.length - 1]?.role === "assistant" &&
               messages[messages.length - 1]?.content === "" && (
                <ThinkingIndicator />
              )}
            </AnimatePresence>
          </>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <ChatInput onSend={sendMessage} disabled={isStreaming} />
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center py-16 select-none">
      <div
        className="w-16 h-16 rounded-2xl bg-[#16112a] border border-[#2d1f5e] flex items-center justify-center mb-6"
        style={{ boxShadow: "0 0 40px rgba(124, 58, 237, 0.15)" }}
      >
        <Sparkles size={28} className="text-[#7c3aed]" />
      </div>
      <h2 className="text-lg font-semibold text-[#fafafa] mb-2">
        Ask anything about your documents
      </h2>
      <p className="text-sm text-[#52525b] max-w-xs leading-relaxed">
        Answers are grounded in your knowledge base and include source citations.
      </p>
    </div>
  );
}
