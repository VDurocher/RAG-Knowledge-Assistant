"use client";

import { motion } from "framer-motion";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { SourceChips } from "./SourceChips";
import type { Message } from "@/lib/types";

interface MessageBubbleProps {
  message: Message;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  if (message.role === "user") {
    return (
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ type: "spring", stiffness: 300, damping: 28 }}
        className="flex justify-end"
      >
        <div className="max-w-[75%] bg-[#16112a] border border-[#2d1f5e] rounded-2xl rounded-tr-sm px-4 py-3">
          <p className="text-sm text-[#fafafa] leading-relaxed whitespace-pre-wrap">
            {message.content}
          </p>
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ type: "spring", stiffness: 300, damping: 28 }}
      className="flex gap-3"
    >
      {/* Avatar */}
      <div className="w-8 h-8 rounded-full bg-[#16112a] border border-[#2d1f5e] flex items-center justify-center flex-shrink-0 mt-0.5">
        <span className="text-[#7c3aed] text-sm leading-none">⬡</span>
      </div>

      {/* Contenu */}
      <div className="flex-1 min-w-0">
        {message.isFallback && (
          <div className="flex items-center gap-2 bg-[#1c1505] border border-[#854d0e] rounded-lg px-3 py-2 mb-2 text-xs text-[#fbbf24]">
            <span>⚠️</span>
            <span>Not in your documents — answer from general knowledge</span>
          </div>
        )}

        <div className="bg-[#0f0d17] border border-[#1a1530] rounded-2xl rounded-tl-sm px-4 py-3">
          {message.content ? (
            <div className="prose-chat">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {message.content}
              </ReactMarkdown>
              {message.isStreaming && (
                <span className="streaming-cursor" aria-hidden />
              )}
            </div>
          ) : (
            message.isStreaming && (
              <span className="streaming-cursor" aria-hidden />
            )
          )}
        </div>

        {/* Citations animées — apparaissent après la fin du stream */}
        {!message.isStreaming && message.citations.length > 0 && (
          <SourceChips citations={message.citations} />
        )}
      </div>
    </motion.div>
  );
}
