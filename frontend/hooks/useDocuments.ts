"use client";

import { useCallback, useEffect, useState } from "react";
import { deleteDocument, fetchDocuments, rebuildIndex, uploadDocuments } from "@/lib/api";
import type { DocumentInfo } from "@/lib/types";

export function useDocuments() {
  const [documents, setDocuments] = useState<DocumentInfo[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [isRebuilding, setIsRebuilding] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setError(null);
      const docs = await fetchDocuments();
      setDocuments(docs);
    } catch {
      setError("Failed to load documents");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const upload = useCallback(async (files: File[]) => {
    setIsUploading(true);
    setError(null);
    try {
      await uploadDocuments(files);
      await load();
    } catch {
      setError("Upload failed");
    } finally {
      setIsUploading(false);
    }
  }, [load]);

  const remove = useCallback(async (name: string) => {
    setError(null);
    try {
      await deleteDocument(name);
      setDocuments(prev => prev.filter(d => d.name !== name));
    } catch {
      setError("Delete failed");
    }
  }, []);

  const rebuild = useCallback(async () => {
    setIsRebuilding(true);
    setError(null);
    try {
      await rebuildIndex();
      await load();
    } catch {
      setError("Rebuild failed");
    } finally {
      setIsRebuilding(false);
    }
  }, [load]);

  return { documents, isLoading, isUploading, isRebuilding, error, upload, remove, rebuild };
}
