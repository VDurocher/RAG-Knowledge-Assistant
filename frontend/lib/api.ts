// Client API — appels vers le backend FastAPI

import type { ChatSettings, Citation, DocumentInfo, PipelineStatus } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ─── Documents ────────────────────────────────────────────────────────────────

export async function fetchDocuments(): Promise<DocumentInfo[]> {
  const res = await fetch(`${API_URL}/api/documents`);
  if (!res.ok) throw new Error("Failed to fetch documents");
  return res.json();
}

export async function uploadDocuments(files: File[]): Promise<DocumentInfo[]> {
  const form = new FormData();
  for (const file of files) form.append("files", file);
  const res = await fetch(`${API_URL}/api/documents/upload`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) throw new Error("Upload failed");
  return res.json();
}

export async function deleteDocument(name: string): Promise<void> {
  const res = await fetch(`${API_URL}/api/documents/${encodeURIComponent(name)}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error("Delete failed");
}

export async function rebuildIndex(): Promise<void> {
  const res = await fetch(`${API_URL}/api/rebuild`, { method: "POST" });
  if (!res.ok) throw new Error("Rebuild failed");
}

export async function fetchStatus(): Promise<PipelineStatus> {
  const res = await fetch(`${API_URL}/api/status`);
  if (!res.ok) throw new Error("Status fetch failed");
  return res.json();
}

// ─── Chat SSE ─────────────────────────────────────────────────────────────────

export interface SSEEvent {
  type: "token" | "sources" | "done" | "error";
  data: unknown;
}

function parseSSEChunk(chunk: string): SSEEvent[] {
  const events: SSEEvent[] = [];
  // Les événements SSE sont séparés par \n\n
  const rawEvents = chunk.split("\n\n").filter(Boolean);

  for (const raw of rawEvents) {
    const lines = raw.split("\n");
    let eventType = "message";
    let dataStr = "";

    for (const line of lines) {
      if (line.startsWith("event: ")) eventType = line.slice(7).trim();
      if (line.startsWith("data: ")) dataStr = line.slice(6).trim();
    }

    if (!dataStr) continue;
    try {
      events.push({ type: eventType as SSEEvent["type"], data: JSON.parse(dataStr) });
    } catch {
      // Chunk incomplet — ignoré
    }
  }

  return events;
}

export interface ChatStreamCallbacks {
  onToken: (token: string) => void;
  onSources: (citations: Citation[]) => void;
  onDone: (isFallback: boolean) => void;
  onError: (message: string) => void;
}

export async function streamChat(
  question: string,
  chatHistory: Array<[string, string]>,
  settings: ChatSettings,
  callbacks: ChatStreamCallbacks,
): Promise<void> {
  const response = await fetch(`${API_URL}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      question,
      chat_history: chatHistory,
      score_threshold: settings.score_threshold,
      fallback_enabled: settings.fallback_enabled,
      k: settings.k,
    }),
  });

  if (!response.ok || !response.body) {
    callbacks.onError("Connection to backend failed");
    return;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    // Traiter tous les événements complets (terminés par \n\n)
    const lastDouble = buffer.lastIndexOf("\n\n");
    if (lastDouble === -1) continue;

    const toProcess = buffer.slice(0, lastDouble + 2);
    buffer = buffer.slice(lastDouble + 2);

    const events = parseSSEChunk(toProcess);

    for (const event of events) {
      if (event.type === "token") {
        callbacks.onToken((event.data as { token: string }).token);
      } else if (event.type === "sources") {
        callbacks.onSources(event.data as Citation[]);
      } else if (event.type === "done") {
        callbacks.onDone((event.data as { is_fallback: boolean }).is_fallback);
        return;
      } else if (event.type === "error") {
        callbacks.onError((event.data as { message: string }).message);
        return;
      }
    }
  }
}
