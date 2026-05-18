"""Streamlit frontend for the Agentic Research Assistant."""
from __future__ import annotations

import os
import uuid

import requests
import streamlit as st

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")
API_KEY = os.getenv("API_KEY", "dev-secret")
HEADERS = {"X-API-Key": API_KEY}
SUPPORTED_TYPES = ["pdf", "txt", "md", "html", "htm"]


def api(method: str, path: str, **kwargs) -> requests.Response:
    return requests.request(method, f"{API_BASE}{path}", headers=HEADERS, timeout=120, **kwargs)


def fetch_collections() -> list[dict]:
    try:
        r = api("GET", "/collections")
        r.raise_for_status()
        return r.json().get("collections", [])
    except Exception:
        return []


def create_collection(name: str, description: str) -> dict | None:
    try:
        r = api("POST", "/collections", json={"name": name, "description": description})
        r.raise_for_status()
        return r.json()
    except requests.HTTPError as e:
        st.error(f"Could not create collection: {e.response.json().get('detail', str(e))}")
        return None


def delete_collection(name: str) -> bool:
    try:
        r = api("DELETE", f"/collections/{name}")
        return r.status_code == 204
    except Exception:
        return False


def upload_document(collection: str, file) -> dict | None:
    try:
        r = requests.post(
            f"{API_BASE}/documents/upload",
            headers=HEADERS,
            params={"collection": collection},
            files={"file": (file.name, file.getvalue(), "application/octet-stream")},
            timeout=120,
        )
        r.raise_for_status()
        return r.json()
    except requests.HTTPError as e:
        st.error(f"Upload failed: {e.response.json().get('detail', str(e))}")
        return None


def delete_document(collection: str, doc_id: str) -> bool:
    try:
        r = api("DELETE", f"/documents/{doc_id}", params={"collection": collection})
        return r.status_code == 200
    except Exception:
        return False


def send_chat(session_id: str, collection: str, message: str) -> dict | None:
    try:
        r = api("POST", "/chat", json={"session_id": session_id, "collection": collection, "message": message})
        r.raise_for_status()
        return r.json()
    except requests.HTTPError as e:
        st.error(f"Chat error: {e.response.json().get('detail', str(e))}")
        return None


def clear_session(session_id: str) -> None:
    try:
        api("DELETE", f"/chat/sessions/{session_id}")
    except Exception:
        pass


def init_state():
    defaults = {
        "session_id": str(uuid.uuid4()),
        "messages": [],
        "active_collection": None,
        "collections": [],
        "refresh_collections": True,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def render_sidebar():
    st.sidebar.title("Research Assistant")
    st.sidebar.caption("Agentic RAG over technical literature")
    st.sidebar.divider()

    if st.session_state.refresh_collections:
        st.session_state.collections = fetch_collections()
        st.session_state.refresh_collections = False

    st.sidebar.subheader("Knowledge Base")
    col_names = [c["name"] for c in st.session_state.collections]

    if col_names:
        current_idx = col_names.index(st.session_state.active_collection) if st.session_state.active_collection in col_names else 0
        selected = st.sidebar.selectbox("Active collection", col_names, index=current_idx)
        if selected != st.session_state.active_collection:
            st.session_state.active_collection = selected
            st.session_state.messages = []
            clear_session(st.session_state.session_id)
            st.session_state.session_id = str(uuid.uuid4())
    else:
        st.sidebar.info("No collections yet. Create one below.")
        st.session_state.active_collection = None

    st.sidebar.divider()

    with st.sidebar.expander("New collection", expanded=not bool(col_names)):
        new_name = st.text_input("Name (letters, numbers, - _)", key="new_col_name")
        new_desc = st.text_input("Description (optional)", key="new_col_desc")
        if st.button("Create", key="btn_create_col"):
            if not new_name:
                st.warning("Please enter a collection name.")
            else:
                result = create_collection(new_name.strip(), new_desc.strip())
                if result:
                    st.success(f"Created '{new_name}'")
                    st.session_state.active_collection = new_name
                    st.session_state.refresh_collections = True
                    st.rerun()

    if st.session_state.active_collection:
        st.sidebar.divider()
        st.sidebar.subheader(f"Documents — {st.session_state.active_collection}")
        uploaded = st.sidebar.file_uploader("Upload document", type=SUPPORTED_TYPES, key=f"uploader_{st.session_state.active_collection}")
        if uploaded and st.sidebar.button("Index document", key="btn_upload"):
            with st.spinner("Processing and indexing…"):
                result = upload_document(st.session_state.active_collection, uploaded)
            if result:
                st.sidebar.success(f"Indexed {result['num_chunks']} chunks from '{result['filename']}'")
                st.session_state.refresh_collections = True
                st.rerun()

        active_info = next((c for c in st.session_state.collections if c["name"] == st.session_state.active_collection), None)
        if active_info and active_info["documents"]:
            for doc in active_info["documents"]:
                col1, col2 = st.sidebar.columns([4, 1])
                col1.caption(f"\U0001f4c4 {doc['filename']} ({doc['num_chunks']} chunks)")
                if col2.button("✕", key=f"del_{doc['doc_id']}", help="Remove document"):
                    if delete_document(st.session_state.active_collection, doc["doc_id"]):
                        st.sidebar.success(f"Removed '{doc['filename']}'")
                        st.session_state.refresh_collections = True
                        st.rerun()
        elif active_info:
            st.sidebar.caption("No documents yet. Upload one above.")

        st.sidebar.divider()
        with st.sidebar.expander("Danger zone"):
            if st.button(f"Delete collection '{st.session_state.active_collection}'", type="primary"):
                if delete_collection(st.session_state.active_collection):
                    st.success(f"Deleted collection '{st.session_state.active_collection}'")
                    st.session_state.active_collection = None
                    st.session_state.refresh_collections = True
                    st.rerun()

    st.sidebar.divider()
    if st.sidebar.button("Clear conversation"):
        clear_session(st.session_state.session_id)
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.rerun()
    st.sidebar.caption(f"Session: `{st.session_state.session_id[:8]}…`")


def render_chat():
    if not st.session_state.active_collection:
        st.title("Agentic Research Assistant")
        st.info("Create or select a knowledge base collection in the sidebar to get started.")
        return

    st.title(f"Research Assistant — {st.session_state.active_collection}")

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("sources"):
                with st.expander(f"Sources ({len(msg['sources'])})"):
                    for src in msg["sources"]:
                        st.markdown(f"**{src['filename']}** (score: {src.get('score', '—')})")
                        st.caption(src["page_content"])
            if msg.get("tool_calls"):
                st.caption(f"Tools used: {', '.join(msg['tool_calls'])}")

    if prompt := st.chat_input("Ask a question about your documents…"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thinking…"):
                response = send_chat(st.session_state.session_id, st.session_state.active_collection, prompt)
            if response:
                answer = response["answer"]
                sources = response.get("sources", [])
                tool_calls = response.get("tool_calls_made", [])
                st.markdown(answer)
                if sources:
                    with st.expander(f"Sources ({len(sources)})"):
                        for src in sources:
                            st.markdown(f"**{src['filename']}** (score: {src.get('score', '—')})")
                            st.caption(src["page_content"])
                if tool_calls:
                    st.caption(f"Tools used: {', '.join(tool_calls)}")
                st.session_state.messages.append({"role": "assistant", "content": answer, "sources": sources, "tool_calls": tool_calls})


def main():
    st.set_page_config(
        page_title="Agentic Research Assistant",
        page_icon="\U0001f52c",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    init_state()
    render_sidebar()
    render_chat()


if __name__ == "__main__":
    main()
