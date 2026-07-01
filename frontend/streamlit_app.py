"""
streamlit_app.py  ·  DocMind Premium UI (API client edition)
Production-quality ChatGPT/Claude-style Streamlit chatbot.

Talks to the DocMind FastAPI backend exclusively over HTTP via
`api_client.py` — no direct imports from the backend package, so the
frontend can be deployed independently and pointed at any backend URL
via the DOCMIND_API_URL environment variable.
"""

# ── stdlib ──────────────────────────────────────────────────────────────────
import datetime
import uuid

# ── third-party ─────────────────────────────────────────────────────────────
from pathlib import Path
import streamlit as st
# ── project ──────────────────────────────────────────────────────────────────
import api_client
def load_css():
    css_file = Path(__file__).parent / "style.css"

    with open(css_file, "r", encoding="utf-8") as f:
        st.markdown(
            f"<style>{f.read()}</style>",
            unsafe_allow_html=True,
        )

load_css()
# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG  ← must be the absolute first Streamlit call
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="DocMind AI",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# LOAD CSS
# ─────────────────────────────────────────────────────────────────────────────
# froms pathlib import Path

# css_path = Path(__file__).parent / "style.css"
# st.write(css_path)
# st.write(css_path.exists())

# ─────────────────────────────────────────────────────────────────────────────
# UTILITIES
# ─────────────────────────────────────────────────────────────────────────────
def generate_thread_id() -> str:
    return str(uuid.uuid4())


def reset_chat() -> None:
    tid = generate_thread_id()
    st.session_state["thread_id"] = tid
    st.session_state["message_history"] = []
    st.session_state["thread_meta"][tid] = {"has_document": False, "document_metadata": {}}


def short_id(tid: str) -> str:
    return str(tid)[-8:]


def greeting() -> str:
    h = datetime.datetime.now().hour
    if h < 12:
        return "Good morning"
    if h < 17:
        return "Good afternoon"
    return "Good evening"


def refresh_thread_list() -> None:
    """Pull the latest thread list + per-thread document metadata from the API."""
    try:
        threads = api_client.list_threads()
    except api_client.ApiError as exc:
        st.session_state["api_error"] = str(exc)
        return

    meta = {}
    for t in threads:
        meta[t["thread_id"]] = {
            "has_document": t["has_document"],
            "document_metadata": t.get("document_metadata", {}),
        }
    st.session_state["thread_meta"] = {**meta, **st.session_state.get("thread_meta", {})}

    # Keep ordering: threads we already knew about first, new ones appended.
    known = st.session_state.get("thread_order", [])
    for t in threads:
        if t["thread_id"] not in known:
            known.append(t["thread_id"])
    st.session_state["thread_order"] = known


# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────────────────────────────────────
if "message_history" not in st.session_state:
    st.session_state["message_history"] = []
if "thread_id" not in st.session_state:
    st.session_state["thread_id"] = generate_thread_id()
if "thread_order" not in st.session_state:
    st.session_state["thread_order"] = []
if "thread_meta" not in st.session_state:
    st.session_state["thread_meta"] = {}
if "api_error" not in st.session_state:
    st.session_state["api_error"] = None

refresh_thread_list()

thread_key = st.session_state["thread_id"]
if thread_key not in st.session_state["thread_order"]:
    st.session_state["thread_order"].append(thread_key)
if thread_key not in st.session_state["thread_meta"]:
    st.session_state["thread_meta"][thread_key] = {"has_document": False, "document_metadata": {}}

thread_meta_entry = st.session_state["thread_meta"][thread_key]
thread_doc_meta = thread_meta_entry.get("document_metadata") or {}
all_threads = st.session_state["thread_order"][::-1]  # newest first
selected_thread = None

if not api_client.health_check():
    st.error(
        f"⚠️ Can't reach the DocMind API at `{api_client.API_BASE_URL}`. "
        "Make sure the FastAPI backend is running (`uvicorn app.main:app --reload`).",
        icon="🚨",
    )
    st.stop()

# ─────────────────────────────────────────────────────────────────────────────
# TOOL LABELS
# ─────────────────────────────────────────────────────────────────────────────
TOOL_LABELS: dict[str, tuple[str, str]] = {
    "rag_tool": ("📄", "Searching document"),
    "duckduckgo_search": ("🌐", "Searching the web"),
    "web_search": ("🌐", "Searching the web"),
    "get_stock_price": ("📈", "Fetching stock data"),
    "calculator": ("🧮", "Calculating"),
}


# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:

    # ── Brand ────────────────────────────────────────────────────────────────
    st.markdown(
        """
        <div class="sb-wrap">
        <div class="sb-brand">
          <div class="sb-logo">✦</div>
          <div>
            <div class="sb-app-name">DocMind</div>
            <div class="sb-tagline">AI Document Assistant</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── New Chat button ───────────────────────────────────────────────────────
    st.markdown('<div class="new-chat-btn">', unsafe_allow_html=True)
    if st.button("＋  New Conversation", use_container_width=True, key="btn_new_chat"):
        reset_chat()
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    # ── Search ────────────────────────────────────────────────────────────────
    search_query = st.text_input(
        "search_convs",
        placeholder="🔍  Search conversations…",
        label_visibility="collapsed",
        key="sidebar_search_input",
    )

    # ── Document section ──────────────────────────────────────────────────────
    st.markdown('<div class="sb-section">Document</div>', unsafe_allow_html=True)

    if thread_doc_meta:
        fname = thread_doc_meta.get("filename", "Unknown")
        pages = thread_doc_meta.get("documents", "?")
        chunks = thread_doc_meta.get("chunks", "?")
        st.markdown(
            f"""
            <div class="doc-badge">
              <div class="doc-badge-row">
                <span style="font-size:16px">📎</span>
                <div class="doc-badge-name">{fname}</div>
              </div>
              <div class="doc-badge-stats">
                <span class="doc-stat">📄 {pages} pages</span>
                <span class="doc-stat">🧩 {chunks} chunks</span>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="no-doc-badge">📂 No document loaded yet</div>',
            unsafe_allow_html=True,
        )

    uploaded_pdf = st.file_uploader(
        "pdf_upload",
        type=["pdf"],
        label_visibility="collapsed",
        help="Upload a PDF — it will be indexed for Q&A in this session.",
    )

    if uploaded_pdf:
        already_indexed = thread_doc_meta.get("filename") == uploaded_pdf.name
        if already_indexed:
            st.info(f"**{uploaded_pdf.name}** is already indexed.", icon="ℹ️")
        else:
            with st.status("⚙️ Indexing document…", expanded=True) as s:
                try:
                    summary = api_client.upload_document(
                        uploaded_pdf.getvalue(),
                        filename=uploaded_pdf.name,
                        thread_id=thread_key,
                    )
                    st.session_state["thread_meta"][thread_key] = {
                        "has_document": True,
                        "document_metadata": {
                            "filename": summary["filename"],
                            "documents": summary["documents"],
                            "chunks": summary["chunks"],
                        },
                    }
                    s.update(label="✅ Document ready", state="complete", expanded=False)
                except api_client.ApiError as exc:
                    s.update(label=f"❌ Failed: {exc}", state="error", expanded=True)
                    st.stop()
            st.rerun()

    # ── Conversation history ───────────────────────────────────────────────────
    st.markdown('<div class="sb-section">Conversations</div>', unsafe_allow_html=True)

    # Filter by search
    filtered = [
        t for t in all_threads
        if not search_query or search_query.lower() in short_id(t).lower()
    ]

    if not filtered:
        st.markdown(
            "<p style='font-size:12px;color:var(--text-3);padding:4px 2px;'>"
            + ("No results found." if search_query else "No conversations yet.")
            + "</p>",
            unsafe_allow_html=True,
        )
    else:
        # Simple bucketing: first = Today, next 3 = Yesterday, rest = Older
        buckets: dict[str, list] = {"Today": [], "Yesterday": [], "Older": []}
        for i, t in enumerate(filtered):
            if i == 0:
                buckets["Today"].append(t)
            elif i <= 3:
                buckets["Yesterday"].append(t)
            else:
                buckets["Older"].append(t)

        for bucket_name, items in buckets.items():
            if not items:
                continue
            st.markdown(
                f'<div class="thread-group-label">{bucket_name}</div>',
                unsafe_allow_html=True,
            )
            for tid in items:
                is_active = tid == thread_key
                has_doc = st.session_state["thread_meta"].get(tid, {}).get("has_document", False)
                doc_icon = "📎" if has_doc else "💬"
                prefix = "▸ " if is_active else "   "
                label = f"{prefix}{doc_icon}  ···{short_id(tid)}"

                if st.button(label, key=f"thread_{tid}", use_container_width=True,
                             help=f"Thread: {tid}"):
                    selected_thread = tid

    # Close sb-wrap div
    st.markdown("</div>", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN AREA — HEADER
# ─────────────────────────────────────────────────────────────────────────────
if thread_doc_meta:
    doc_html = f"""
    <div class="header-doc-card">
      <div class="doc-label">Active Document</div>
      <div class="doc-filename">📎 {thread_doc_meta.get("filename","Unknown")}</div>
      <div class="doc-chips">
        <span class="doc-chip">📄 {thread_doc_meta.get("documents","?")} pages</span>
        <span class="doc-chip">🧩 {thread_doc_meta.get("chunks","?")} chunks</span>
      </div>
    </div>
    """
else:
    doc_html = 'No document loaded'

st.markdown(
    f"""
    <div class="page-header fade-in">
      <div class="header-left">
        <h1>DocMind</h1>
        <div class="greeting">{greeting()} — ask me anything about your documents or the web.</div>
      </div>
      <div style="display:flex;flex-direction:column;align-items:flex-end;gap:6px;">
        {doc_html}
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────────────────────────────────────
# EMPTY STATE
# ─────────────────────────────────────────────────────────────────────────────
if not st.session_state["message_history"]:
    st.markdown(
        """
        <div class="empty-state fade-in">
          <div class="empty-icon">✦</div>
          <h2>How can I help you today?</h2>
          <p>Upload a PDF from the sidebar and ask questions about it, or use
             the built-in tools to search the web, fetch stock prices, and more.</p>

          <div class="feature-grid">
            <div class="feature-card">
              <div class="feature-icon">📄</div>
              <div class="feature-title">Document Q&amp;A</div>
              <div class="feature-desc">Upload any PDF and get instant answers grounded in your document.</div>
            </div>
            <div class="feature-card">
              <div class="feature-icon">🌐</div>
              <div class="feature-title">Web Search</div>
              <div class="feature-desc">Real-time answers from the web via DuckDuckGo search integration.</div>
            </div>
            <div class="feature-card">
              <div class="feature-icon">📈</div>
              <div class="feature-title">Stock Prices</div>
              <div class="feature-desc">Live stock data for any ticker symbol — just ask.</div>
            </div>
            <div class="feature-card">
              <div class="feature-icon">🧮</div>
              <div class="feature-title">Calculator</div>
              <div class="feature-desc">Complex math and unit conversions handled automatically.</div>
            </div>
          </div>

          <div class="prompt-row">
            <span class="prompt-chip">📄 Summarise this document</span>
            <span class="prompt-chip">🔑 Key takeaways?</span>
            <span class="prompt-chip">📊 What are the main findings?</span>
            <span class="prompt-chip">🌐 Latest AI news</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ─────────────────────────────────────────────────────────────────────────────
# CHAT HISTORY
# ─────────────────────────────────────────────────────────────────────────────
for idx, msg in enumerate(st.session_state["message_history"]):
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

        ts = datetime.datetime.now().strftime("%H:%M")
        if msg["role"] == "assistant":
            st.markdown(
                f"""
                <div class="msg-meta">
                  <span class="msg-time">{ts}</span>
                  <span class="msg-action">📋 Copy</span>
                  <span class="msg-action">👍</span>
                  <span class="msg-action">👎</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

# ─────────────────────────────────────────────────────────────────────────────
# CHAT INPUT  (single request/response — the API is not streaming)
# ─────────────────────────────────────────────────────────────────────────────
user_input = st.chat_input("Ask anything — document Q&A, web, stocks, math…")

if user_input:
    st.session_state["message_history"].append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Thinking…"):
            try:
                result = api_client.send_chat_message(user_input, thread_id=thread_key)
            except api_client.ApiError as exc:
                st.error(f"Request failed: {exc}", icon="🚨")
                st.stop()

        # The backend may report which tools it used for this turn.
        for tc in result.get("tool_calls", []):
            icon, label = TOOL_LABELS.get(tc["name"], ("🔧", f"Using {tc['name']}"))
            st.status(f"{icon}  {label}", state="complete", expanded=False)

        ai_response = result["reply"]
        st.markdown(ai_response)

        ts = datetime.datetime.now().strftime("%H:%M")
        st.markdown(
            f"""
            <div class="msg-meta" style="opacity:1">
              <span class="msg-time">{ts}</span>
              <span class="msg-action">📋 Copy</span>
              <span class="msg-action">👍</span>
              <span class="msg-action">👎</span>
              <span class="msg-action">🔄 Regenerate</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.session_state["message_history"].append({"role": "assistant", "content": ai_response})
    # The backend may auto-create a thread_id on the first message of a new chat.
    if result["thread_id"] != thread_key:
        st.session_state["thread_id"] = result["thread_id"]
        if result["thread_id"] not in st.session_state["thread_order"]:
            st.session_state["thread_order"].append(result["thread_id"])

    if thread_doc_meta:
        st.caption(
            f"📎 {thread_doc_meta.get('filename')}  ·  "
            f"{thread_doc_meta.get('documents')} pages  ·  "
            f"{thread_doc_meta.get('chunks')} chunks"
        )

# ─────────────────────────────────────────────────────────────────────────────
# THREAD SWITCH
# ─────────────────────────────────────────────────────────────────────────────
if selected_thread:
    try:
        data = api_client.get_thread_messages(selected_thread)
    except api_client.ApiError as exc:
        st.error(f"Couldn't load that conversation: {exc}", icon="🚨")
        st.stop()

    st.session_state["thread_id"] = selected_thread
    st.session_state["message_history"] = data["messages"]
    st.session_state["thread_meta"][selected_thread] = {
        "has_document": bool(data.get("document_metadata")),
        "document_metadata": data.get("document_metadata", {}),
    }
    st.rerun()
