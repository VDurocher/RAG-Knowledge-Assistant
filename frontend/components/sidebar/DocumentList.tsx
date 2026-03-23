"use client";

import { motion, AnimatePresence } from "framer-motion";
import { FileText, Trash2 } from "lucide-react";
import type { DocumentInfo } from "@/lib/types";

const EXT_ICONS: Record<string, string> = {
  pdf:  "📄",
  csv:  "📊",
  docx: "📝",
  json: "📋",
  txt:  "📃",
};

interface DocumentListProps {
  documents: DocumentInfo[];
  isLoading: boolean;
  onRemove: (name: string) => void;
}

export function DocumentList({ documents, isLoading, onRemove }: DocumentListProps) {
  if (isLoading) {
    return (
      <div className="space-y-2">
        {[1, 2, 3].map(i => (
          <div
            key={i}
            className="h-9 bg-[#0f0d17] border border-[#1a1530] rounded-lg animate-pulse"
          />
        ))}
      </div>
    );
  }

  if (documents.length === 0) {
    return (
      <div className="flex flex-col items-center py-8 text-center">
        <FileText size={28} className="text-[#2d1f5e] mb-2" />
        <p className="text-xs text-[#52525b]">No documents indexed</p>
        <p className="text-[10px] text-[#3f3f46] mt-0.5">Upload files to get started</p>
      </div>
    );
  }

  return (
    <motion.ul className="space-y-1.5" layout>
      <AnimatePresence initial={false}>
        {documents.map(doc => (
          <motion.li
            key={doc.name}
            layout
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.15 }}
            className="group flex items-center gap-2.5 bg-[#0f0d17] border border-[#1a1530] rounded-lg px-3 py-2 hover:border-[#2d1f5e] transition-colors"
          >
            <span className="text-sm flex-shrink-0" aria-hidden>
              {EXT_ICONS[doc.extension] ?? "📄"}
            </span>
            <span
              className="flex-1 text-xs text-[#a1a1aa] truncate"
              title={doc.name}
            >
              {doc.name}
            </span>
            <button
              onClick={() => onRemove(doc.name)}
              className="opacity-0 group-hover:opacity-100 text-[#52525b] hover:text-[#ef4444] transition-all duration-150 flex-shrink-0 p-0.5"
              title={`Delete ${doc.name}`}
            >
              <Trash2 size={12} />
            </button>
          </motion.li>
        ))}
      </AnimatePresence>
    </motion.ul>
  );
}
