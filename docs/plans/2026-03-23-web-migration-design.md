# Web Migration Design — RAG Knowledge Assistant
*2026-03-23*

## Décision
Migration de Streamlit vers Next.js 15 + FastAPI dans un monorepo. Le `core/` Python RAG pipeline reste inchangé.

## Design System
- **Palette** : noir `#09090b` + violet `#7c3aed`, glassmorphism subtil, glow effects
- **Typo** : Geist Sans (portfolio-grade, moderne)
- **Animations** : Framer Motion — messages slide-up, source chips staggered, streaming cursor, thinking dots

## Architecture
```
monorepo/
├── core/        RAG pipeline Python (inchangé)
├── backend/     FastAPI — SSE streaming, upload, delete, rebuild
└── frontend/    Next.js 15 App Router — UI complète
```

## API
- `POST /api/chat` → SSE stream (token / sources / done / error)
- `GET /api/documents` → liste fichiers
- `POST /api/documents/upload` → upload
- `DELETE /api/documents/{name}` → suppression
- `POST /api/rebuild` → force rebuild index
- `GET /api/status` → état pipeline

## Composants clés
- `Sidebar` : documents, upload dropzone, settings, actions
- `ChatArea` : messages scrollables, streaming cursor, source chips animés
- `MessageBubble` : user (droite) / assistant (gauche + avatar)
- `SourceChips` : stagger animation post-réponse, confidence badge coloré
- `ChatInput` : textarea auto-resize, border gradient focus
- `ThinkingIndicator` : 3 dots bounce staggeré

## Stack
| Couche | Tech |
|--------|------|
| Frontend | Next.js 15, TypeScript strict, Tailwind v3 |
| Animations | Framer Motion 11 |
| Composants | shadcn/ui |
| Backend | FastAPI 0.115, sse-starlette |
| Streaming | SSE via thread + asyncio.Queue |
