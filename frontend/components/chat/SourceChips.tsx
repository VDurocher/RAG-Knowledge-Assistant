"use client";

import { motion, AnimatePresence } from "framer-motion";
import { useState } from "react";
import { ChevronRight, FileText } from "lucide-react";
import type { Citation } from "@/lib/types";

const CONFIDENCE_COLORS: Record<string, string> = {
  high:   "text-emerald-400",
  medium: "text-amber-400",
  low:    "text-red-400",
};

interface SourceChipsProps {
  citations: Citation[];
}

export function SourceChips({ citations }: SourceChipsProps) {
  const [expanded, setExpanded] = useState(false);

  if (citations.length === 0) return null;

  return (
    <div className="mt-3 space-y-2">
      {/* Label */}
      <p className="text-[10px] tracking-widest text-[#52525b] uppercase">Sources</p>

      {/* Chips en stagger */}
      <motion.div
        className="flex flex-wrap gap-2"
        initial="hidden"
        animate="visible"
        variants={{ visible: { transition: { staggerChildren: 0.06 } } }}
      >
        {citations.map((c, i) => (
          <motion.span
            key={i}
            variants={{
              hidden: { opacity: 0, y: 8, scale: 0.95 },
              visible: { opacity: 1, y: 0, scale: 1, transition: { type: "spring", stiffness: 300, damping: 24 } },
            }}
            className="inline-flex items-center gap-1.5 bg-[#0f0d17] border border-[#2d1f5e] rounded-full px-3 py-1 text-xs text-[#7eb3e8] whitespace-nowrap cursor-default hover:border-[#7c3aed] hover:bg-[#16112a] transition-colors duration-150"
          >
            <FileText size={10} className="text-[#52525b] flex-shrink-0" />
            <span>{c.source}</span>
            {c.page !== null && (
              <span className="text-[#4a6a8a]">· p.{c.page}</span>
            )}
            {c.confidence_label && (
              <motion.span
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ delay: 0.1 + i * 0.06, type: "spring", stiffness: 400 }}
                className={`${CONFIDENCE_COLORS[c.confidence_label] ?? "text-[#52525b]"} text-[9px]`}
                title={c.confidence !== null ? `Confidence: ${Math.round(c.confidence * 100)}%` : undefined}
              >
                ●
              </motion.span>
            )}
          </motion.span>
        ))}
      </motion.div>

      {/* Excerpts accordion */}
      <button
        onClick={() => setExpanded(v => !v)}
        className="flex items-center gap-1 text-xs text-[#52525b] hover:text-[#a1a1aa] transition-colors mt-1"
      >
        <motion.span animate={{ rotate: expanded ? 90 : 0 }} transition={{ duration: 0.15 }}>
          <ChevronRight size={12} />
        </motion.span>
        View excerpts
      </button>

      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="space-y-2 pt-1">
              {citations.map((c, i) => (
                <div key={i} className="bg-[#0f0d17] border border-[#1a1530] rounded-lg p-3">
                  <p className="text-xs font-medium text-[#a78bfa] mb-1">
                    {c.source}{c.page !== null ? ` — page ${c.page}` : ""}
                    {c.confidence !== null && (
                      <span className="text-[#52525b] ml-2 font-normal">
                        {Math.round(c.confidence * 100)}% confidence
                      </span>
                    )}
                  </p>
                  <p className="text-xs text-[#71717a] leading-relaxed">{c.excerpt}</p>
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
