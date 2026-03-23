// Types partagés entre hooks et composants

export interface Citation {
  source: string;
  page: number | null;
  excerpt: string;
  confidence: number | null;
  confidence_label: "high" | "medium" | "low" | null;
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations: Citation[];
  isStreaming: boolean;
  isFallback: boolean;
}

export interface DocumentInfo {
  name: string;
  extension: string;
}

export interface PipelineStatus {
  doc_count: number;
  llm_label: string;
  embedder_label: string;
}

export interface ChatSettings {
  score_threshold: number;
  fallback_enabled: boolean;
  k: number;
}
