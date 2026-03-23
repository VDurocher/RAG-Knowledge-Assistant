"use client";

import { useRef, useState, type KeyboardEvent } from "react";
import { motion } from "framer-motion";
import { ArrowUp } from "lucide-react";

interface ChatInputProps {
  onSend: (text: string) => void;
  disabled?: boolean;
}

export function ChatInput({ onSend, disabled = false }: ChatInputProps) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSend = () => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setValue("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleInput = () => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 140)}px`;
  };

  return (
    <div className="px-4 py-4 border-t border-[#1a1530] bg-[#09090b]/80 backdrop-blur-sm">
      <div className="max-w-3xl mx-auto">
        <div className="input-gradient-border">
          <div className="relative bg-[#0f0d17] border border-[#2d1f5e] rounded-[14px] z-10">
            <textarea
              ref={textareaRef}
              value={value}
              onChange={e => setValue(e.target.value)}
              onKeyDown={handleKeyDown}
              onInput={handleInput}
              disabled={disabled}
              placeholder="Ask a question about your documents…"
              rows={1}
              className="w-full resize-none bg-transparent px-4 py-3 pr-12 text-sm text-[#fafafa] placeholder:text-[#52525b] focus:outline-none disabled:opacity-50 rounded-[14px]"
              style={{ minHeight: "48px", maxHeight: "140px" }}
            />

            {/* Bouton Send */}
            <div className="absolute right-2 bottom-2">
              <motion.button
                onClick={handleSend}
                disabled={!value.trim() || disabled}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                className="w-8 h-8 rounded-full bg-[#7c3aed] flex items-center justify-center disabled:opacity-30 disabled:cursor-not-allowed hover:bg-[#6d28d9] transition-colors"
                style={{
                  boxShadow: value.trim() && !disabled
                    ? "0 0 12px rgba(124, 58, 237, 0.4)"
                    : "none",
                }}
              >
                <ArrowUp size={14} className="text-white" />
              </motion.button>
            </div>
          </div>
        </div>

        <p className="text-center text-[10px] text-[#3f3f46] mt-2">
          Enter to send · Shift+Enter for new line
        </p>
      </div>
    </div>
  );
}
