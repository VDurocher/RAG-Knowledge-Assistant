"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { RefreshCw, Trash2, Download, Settings } from "lucide-react";
import { FileDropzone } from "./FileDropzone";
import { DocumentList } from "./DocumentList";
import { SettingsPanel } from "./SettingsPanel";
import type { ChatSettings, DocumentInfo } from "@/lib/types";

interface SidebarProps {
  documents: DocumentInfo[];
  isLoading: boolean;
  isUploading: boolean;
  isRebuilding: boolean;
  onUpload: (files: File[]) => void;
  onRemove: (name: string) => void;
  onRebuild: () => void;
  settings: ChatSettings;
  onSettingsChange: (settings: ChatSettings) => void;
  onClearHistory: () => void;
  onExportChat: () => void;
}

export function Sidebar({
  documents,
  isLoading,
  isUploading,
  isRebuilding,
  onUpload,
  onRemove,
  onRebuild,
  settings,
  onSettingsChange,
  onClearHistory,
  onExportChat,
}: SidebarProps) {
  const [settingsOpen, setSettingsOpen] = useState(false);

  return (
    <div className="w-[280px] flex-shrink-0 h-full flex flex-col bg-[#09090b] border-r border-[#1a1530]">
      {/* En-tête */}
      <div className="px-4 py-5 border-b border-[#1a1530]">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-[#16112a] border border-[#2d1f5e] flex items-center justify-center">
            <span className="text-[#7c3aed] text-sm" aria-hidden>⬡</span>
          </div>
          <div>
            <p className="text-[13px] font-semibold text-[#fafafa]">RAG Assistant</p>
            <p className="text-[10px] text-[#52525b]">Knowledge base</p>
          </div>
        </div>
      </div>

      {/* Contenu scrollable */}
      <div className="flex-1 overflow-y-auto p-4 space-y-5">
        {/* Zone d'upload */}
        <section>
          <p className="text-[10px] tracking-widest text-[#52525b] uppercase mb-2">Upload</p>
          <FileDropzone onUpload={onUpload} isUploading={isUploading} />
        </section>

        {/* Liste des documents */}
        <section>
          <div className="flex items-center justify-between mb-2">
            <p className="text-[10px] tracking-widest text-[#52525b] uppercase">Documents</p>
            <span className="text-[10px] text-[#52525b] bg-[#0f0d17] border border-[#1a1530] rounded-full px-2 py-0.5">
              {documents.length}
            </span>
          </div>
          <DocumentList documents={documents} isLoading={isLoading} onRemove={onRemove} />
        </section>

        {/* Paramètres (accordéon) */}
        <section>
          <button
            onClick={() => setSettingsOpen(v => !v)}
            className="flex items-center justify-between w-full mb-2 group"
          >
            <p className="text-[10px] tracking-widest text-[#52525b] uppercase group-hover:text-[#a1a1aa] transition-colors">
              Settings
            </p>
            <Settings
              size={11}
              className={`transition-colors ${settingsOpen ? "text-[#7c3aed]" : "text-[#52525b]"}`}
            />
          </button>

          {settingsOpen && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              transition={{ duration: 0.2 }}
              className="overflow-hidden"
            >
              <SettingsPanel settings={settings} onChange={onSettingsChange} />
            </motion.div>
          )}
        </section>
      </div>

      {/* Actions en bas */}
      <div className="p-4 border-t border-[#1a1530] space-y-2">
        <motion.button
          onClick={onRebuild}
          disabled={isRebuilding}
          whileHover={{ scale: 1.01 }}
          whileTap={{ scale: 0.98 }}
          className="w-full flex items-center justify-center gap-2 py-2.5 rounded-lg bg-[#7c3aed] hover:bg-[#6d28d9] text-white text-xs font-medium disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          style={{ boxShadow: "0 0 20px rgba(124, 58, 237, 0.25)" }}
        >
          <RefreshCw size={13} className={isRebuilding ? "animate-spin" : ""} />
          {isRebuilding ? "Rebuilding…" : "Rebuild index"}
        </motion.button>

        <div className="flex gap-2">
          <button
            onClick={onClearHistory}
            className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg bg-[#0f0d17] border border-[#1a1530] hover:border-[#2d1f5e] text-[#52525b] hover:text-[#a1a1aa] text-xs transition-colors"
          >
            <Trash2 size={11} />
            Clear
          </button>
          <button
            onClick={onExportChat}
            className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg bg-[#0f0d17] border border-[#1a1530] hover:border-[#2d1f5e] text-[#52525b] hover:text-[#a1a1aa] text-xs transition-colors"
          >
            <Download size={11} />
            Export
          </button>
        </div>
      </div>
    </div>
  );
}
