"""Point d'entrée Streamlit — interface chat entreprise avec citations."""

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config import settings
from core.indexer import load_or_build_index
from core.loader import list_source_files, load_documents
from core.rag import ask_stream, build_llm, build_retriever

# ─── Configuration Streamlit ─────────────────────────────────────────────────

st.set_page_config(
    page_title="RAG Knowledge Assistant",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── CSS ─────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
/* Import police */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');

/* Logo entreprise */
.logo-wrap {
    background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 100%);
    border-radius: 10px;
    padding: 18px 20px;
    text-align: center;
    margin-bottom: 16px;
    border: 1px solid #1e40af33;
}
.logo-name  { color: #60a5fa; font-size: 20px; font-weight: 700; letter-spacing: 3px; margin: 0; }
.logo-sub   { color: #64748b; font-size: 10px; letter-spacing: 2px; margin-top: 3px; }

/* Badges statut */
.badge      { display: inline-block; padding: 3px 10px; border-radius: 20px; font-size: 12px; font-weight: 600; }
.badge-ok   { background: #052e16; color: #4ade80; border: 1px solid #166534; }
.badge-err  { background: #450a0a; color: #f87171; border: 1px solid #991b1b; }

/* Chips de source — compactes, inline */
.sources-row { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 10px; }
.source-chip {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    background: #0f1e35;
    border: 1px solid #1e3a5f;
    border-radius: 20px;
    padding: 3px 10px 3px 8px;
    font-size: 12px;
    color: #7eb3e8;
    white-space: nowrap;
}
.source-chip .page { color: #4a6a8a; margin-left: 2px; }

/* Ligne séparatrice légère sous les chips */
.sources-label { font-size: 11px; color: #4a6a8a; margin-bottom: 4px; letter-spacing: 0.5px; }

/* Bannière fallback */
.fallback-banner {
    background: #1c1505;
    border: 1px solid #854d0e;
    border-radius: 8px;
    padding: 8px 14px;
    font-size: 13px;
    color: #fbbf24;
    margin-bottom: 8px;
}
</style>
""", unsafe_allow_html=True)


# ─── Cache pipeline ───────────────────────────────────────────────────────────

@st.cache_resource(show_spinner="Loading knowledge base…")
def initialize_rag_pipeline(force_rebuild: bool = False):
    documents = load_documents(settings.knowledge_base_path)
    vector_store = load_or_build_index(documents, settings, force_rebuild=force_rebuild)
    retriever = build_retriever(vector_store, k=settings.retrieval_k)
    llm = build_llm(settings)
    return retriever, llm


# ─── Sidebar ─────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("""
    <div class="logo-wrap">
        <p class="logo-name">⬡ ACME CORP</p>
        <p class="logo-sub">KNOWLEDGE ASSISTANT</p>
    </div>
    """, unsafe_allow_html=True)

    source_files = list_source_files(settings.knowledge_base_path)

    if source_files:
        st.markdown(
            f'<span class="badge badge-ok">● {len(source_files)} documents indexed</span>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<span class="badge badge-err">● No documents found</span>',
            unsafe_allow_html=True,
        )

    st.divider()
    st.subheader("⚙️ Settings")

    retrieval_k = st.slider("Results per query", 1, 10, settings.retrieval_k)

    fallback_enabled = st.toggle(
        "LLM fallback",
        value=True,
        help="When no relevant documents are found, the AI answers from general knowledge.",
    )

    if settings.llm_type == "ollama":
        llm_label = f"Ollama / {settings.ollama_model}"
    else:
        llm_label = f"OpenAI / {settings.openai_chat_model}"

    embed_label = "OpenAI" if settings.embedder_type == "openai" else "Local (HuggingFace)"
    st.caption(f"**LLM:** {llm_label}")
    st.caption(f"**Embedder:** {embed_label}")

    st.divider()
    st.subheader("📚 Knowledge Base")

    for filename in source_files:
        icon = "📄" if filename.endswith(".pdf") else "📝"
        st.caption(f"{icon} {filename}")

    if not source_files:
        st.info("Add PDF or TXT files to `knowledge_base/`.")

    st.divider()

    st.divider()
    st.subheader("📤 Add Documents")

    uploaded_files = st.file_uploader(
        "PDF, TXT, MD or CSV",
        type=["pdf", "txt", "md", "csv"],
        accept_multiple_files=True,
        label_visibility="collapsed",
    )

    if uploaded_files:
        saved = []
        for uploaded_file in uploaded_files:
            dest = settings.knowledge_base_path / uploaded_file.name
            dest.write_bytes(uploaded_file.read())
            saved.append(uploaded_file.name)
        st.success(f"Added: {', '.join(saved)}")
        st.cache_resource.clear()
        st.rerun()

    st.divider()

    if st.button("🔄 Rebuild Index", use_container_width=True, type="secondary"):
        st.cache_resource.clear()
        st.rerun()

    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()


# ─── Main ─────────────────────────────────────────────────────────────────────

st.title("🧠 Knowledge Assistant")
st.caption("Ask questions about your company documents. Answers are grounded in your knowledge base.")

# Validation config
try:
    settings.validate()
except ValueError as error:
    st.error(f"**Configuration error:** {error}")
    st.code("cp .env.example .env  # then fill OPENAI_API_KEY", language="bash")
    st.stop()

if not source_files:
    st.warning("**No documents found.** Add PDF or TXT files to `knowledge_base/`, then rebuild.")
    st.stop()

try:
    retriever, llm = initialize_rag_pipeline()
except Exception as error:
    st.error(f"**Pipeline error:** {error}")
    st.stop()

# ─── Demo questions ───────────────────────────────────────────────────────────

DEMO_QUESTIONS: list[tuple[str, str]] = [
    ("💰", "Which supplier has the best price for the Jabra Evolve2 85 headset?"),
    ("📊", "What was Metro Digital Agency's total spend in Q1 2026, and how many orders did they place?"),
    ("📈", "What is our selling price for the Dell XPS 15 i7 and what margin does it generate?"),
    ("🏆", "Compare buying price vs selling price for the Logitech MX Master 3S — what is our profit per unit?"),
    ("👥", "Who works on Saturdays and what are their roles?"),
    ("🔍", "Which client had the highest average order value in Q1 2026?"),
]

# ─── Historique ───────────────────────────────────────────────────────────────

if "messages" not in st.session_state:
    st.session_state.messages = []
if "preset_question" not in st.session_state:
    st.session_state.preset_question = None


def render_sources(citations: list[dict]) -> None:
    """Affiche les sources sous forme de chips compactes + excerpts optionnels."""
    if not citations:
        return

    chips_html = '<div class="sources-label">SOURCES</div><div class="sources-row">'
    for c in citations:
        page_part = f'<span class="page">· p.{c["page"]}</span>' if c.get("page") else ""
        chips_html += f'<span class="source-chip">📄 {c["source"]}{page_part}</span>'
    chips_html += "</div>"
    st.markdown(chips_html, unsafe_allow_html=True)

    with st.expander("View excerpts", expanded=False):
        for c in citations:
            label = f"**{c['source']}**" + (f" — page {c['page']}" if c.get("page") else "")
            st.markdown(label)
            st.caption(c["excerpt"])


# Suggestions de démo — affichées uniquement quand le chat est vide
if not st.session_state.messages:
    st.markdown("#### Try these questions")
    cols = st.columns(2)
    for i, (icon, question) in enumerate(DEMO_QUESTIONS):
        with cols[i % 2]:
            label = f"{icon} {question[:60]}{'…' if len(question) > 60 else ''}"
            if st.button(label, key=f"demo_{i}", use_container_width=True):
                st.session_state.preset_question = question
                st.rerun()
    st.divider()

# Rendu de l'historique
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg.get("is_fallback"):
            st.markdown(
                '<div class="fallback-banner">⚠️ Not in your documents — answer from general knowledge</div>',
                unsafe_allow_html=True,
            )
        st.markdown(msg["content"])
        if msg["role"] == "assistant" and not msg.get("is_fallback"):
            render_sources(msg.get("citations", []))

# ─── Input ────────────────────────────────────────────────────────────────────

# Récupérer la question preset (clic sur un bouton de démo) ou la saisie manuelle
preset = st.session_state.pop("preset_question", None) if st.session_state.get("preset_question") else None

if prompt := (preset or st.chat_input("Ask a question about your documents…")):
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        is_fallback = False
        source_docs = []

        try:
            stream, source_docs, is_fallback = ask_stream(
                prompt, retriever, llm, fallback_to_llm=fallback_enabled
            )

            if is_fallback:
                st.markdown(
                    '<div class="fallback-banner">⚠️ Not in your documents — answer from general knowledge</div>',
                    unsafe_allow_html=True,
                )

            full_response = st.write_stream(stream)

        except Exception as error:
            full_response = f"An error occurred: {error}"
            st.error(full_response)

        # Citations — uniquement si l'IA a trouvé des docs (pas en fallback)
        citations: list[dict] = []
        if source_docs:
            seen: set[str] = set()
            for doc in source_docs:
                excerpt = doc.page_content[:180].strip().replace("\n", " ")
                if excerpt in seen:
                    continue
                seen.add(excerpt)
                page = doc.metadata.get("page")
                citations.append({
                    "source": doc.metadata.get("source", "Unknown"),
                    "page": page + 1 if page is not None else None,
                    "excerpt": excerpt + ("…" if len(doc.page_content) > 180 else ""),
                })
            render_sources(citations)

    st.session_state.messages.append({
        "role": "assistant",
        "content": full_response,
        "citations": citations,
        "is_fallback": is_fallback,
    })
