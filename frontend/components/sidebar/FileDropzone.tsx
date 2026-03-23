"use client";

import { useCallback, useRef, useState } from "react";
import { Upload } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

const ACCEPTED = ".pdf,.txt,.csv,.docx,.json";

interface FileDropzoneProps {
  onUpload: (files: File[]) => void;
  isUploading: boolean;
}

export function FileDropzone({ onUpload, isUploading }: FileDropzoneProps) {
  const [isDragging, setIsDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFiles = useCallback((files: FileList | null) => {
    if (!files || isUploading) return;
    const valid = Array.from(files).filter(f =>
      ACCEPTED.split(",").some(ext => f.name.toLowerCase().endsWith(ext))
    );
    if (valid.length > 0) onUpload(valid);
  }, [isUploading, onUpload]);

  const onDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const onDragLeave = useCallback((e: React.DragEvent) => {
    // Ignorer les événements sur les enfants
    if (!e.currentTarget.contains(e.relatedTarget as Node)) {
      setIsDragging(false);
    }
  }, []);

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    handleFiles(e.dataTransfer.files);
  }, [handleFiles]);

  const onClick = useCallback(() => {
    if (!isUploading) inputRef.current?.click();
  }, [isUploading]);

  return (
    <motion.div
      onClick={onClick}
      onDragOver={onDragOver}
      onDragLeave={onDragLeave}
      onDrop={onDrop}
      animate={{
        borderColor: isDragging ? "#7c3aed" : "#2d1f5e",
        backgroundColor: isDragging ? "rgba(124, 58, 237, 0.06)" : "rgba(15, 13, 23, 0)",
      }}
      transition={{ duration: 0.15 }}
      className="border border-dashed rounded-xl px-4 py-5 text-center cursor-pointer hover:border-[#7c3aed] hover:bg-[#16112a]/30 transition-colors"
    >
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED}
        multiple
        className="hidden"
        onChange={e => handleFiles(e.target.files)}
        disabled={isUploading}
      />

      <AnimatePresence mode="wait">
        {isUploading ? (
          <motion.div
            key="uploading"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="flex flex-col items-center gap-2"
          >
            <div className="w-5 h-5 border-2 border-[#7c3aed] border-t-transparent rounded-full animate-spin" />
            <p className="text-xs text-[#52525b]">Uploading…</p>
          </motion.div>
        ) : (
          <motion.div
            key="idle"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="flex flex-col items-center gap-2"
          >
            <Upload size={18} className={isDragging ? "text-[#7c3aed]" : "text-[#52525b]"} />
            <p className="text-xs text-[#52525b]">
              Drop files or{" "}
              <span className="text-[#a78bfa]">browse</span>
            </p>
            <p className="text-[10px] text-[#3f3f46]">PDF · TXT · CSV · DOCX · JSON</p>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
