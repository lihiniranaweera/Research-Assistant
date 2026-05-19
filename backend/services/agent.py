"""LangGraph ReAct agent wired with RAG + Tavily web search."""
from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from tavily import TavilyClient

from backend.config import get_settings
from backend.services import vector_store as vs

SYSTEM_PROMPT = """You are a precise research assistant that answers questions strictly from uploaded documents.

STRICT GROUNDING RULES — follow these without exception:
1. ALWAYS call `search_documents` first, for every question. No exceptions.
2. Base your answer ONLY on text returned by `search_documents`. Do not use your own knowledge to fill gaps.
3. If the retrieved text does not contain enough information to answer the question, say exactly:
   "I could not find that information in the uploaded documents."
   Do NOT guess, infer, or extrapolate beyond what is explicitly stated in the retrieved text.
4. When you state a fact, quote or closely paraphrase the source text and name the file it came from.
5. Only call `web_search` when the user explicitly asks about external or general information unrelated to the uploaded documents. Never use it to supplement missing document content.
6. Never combine document content with your own prior knowledge. If the document is silent on a detail, the answer is "not found in the documents."

FORMATTING:
- For factual questions, give a direct answer then cite the source text.
- For summaries, cover what the document explicitly states: do not add interpretation.
- Keep answers concise unless the user asks for detail."""


def _build_tools(collection_name: str):
    settings = get_settings()

    @tool
    def search_documents(query: str) -> str:
        """Search the uploaded research documents for information relevant to the query.
        Use this tool first for any question that may be covered by the uploaded papers.
        Input should be a natural-language search query."""
        try:
            results = vs.similarity_search_with_score(collection_name, query, k=settings.max_retrieval_docs)
            if not results:
                return "No relevant documents found in the collection for this query."
            parts = []
            for doc, score in results:
                meta = doc.metadata
                parts.append(
                    f"[Source: {meta.get('filename', 'unknown')} | score: {score:.3f}]\n{doc.page_content}"
                )
            return "\n\n---\n\n".join(parts)
        except Exception as e:
            return f"Document search error: {e}"

    @tool
    def web_search(query: str) -> str:
        """Search the web for current information to supplement document knowledge.
        Use ONLY when the user explicitly asks about external or general information
        unrelated to the uploaded documents. Do not use to fill gaps in document content.
        Input should be a concise search query."""
        try:
            client = TavilyClient(api_key=settings.tavily_api_key)
            response = client.search(query=query, max_results=5, search_depth="advanced")
            results = response.get("results", [])
            if not results:
                return "No web results found."
            parts = []
            for r in results:
                parts.append(f"[{r.get('title', '')}]({r.get('url', '')})\n{r.get('content', '')}")
            return "\n\n---\n\n".join(parts)
        except Exception as e:
            return f"Web search error: {e}"

    @tool
    def extract_citations(query: str) -> str:
        """Extract references, citations, and bibliographic entries from the uploaded documents.
        Use when the user asks about sources, references, or wants to find citations for a topic.
        Input should be the topic or keyword to find citations for."""
        try:
            results = vs.similarity_search_with_score(
                collection_name,
                query + " references bibliography citations doi arxiv",
                k=8,
            )
            if not results:
                return "No citation-related content found."
            citation_chunks = []
            for doc, _ in results:
                text = doc.page_content
                if any(
                    kw in text.lower()
                    for kw in ["doi", "arxiv", "journal", "et al", "references", "bibliography", "proceedings", "isbn"]
                ):
                    citation_chunks.append(f"From {doc.metadata.get('filename', 'unknown')}:\n{text}")
            return (
                "\n\n".join(citation_chunks)
                if citation_chunks
                else "No clear citation content found for this query."
            )
        except Exception as e:
            return f"Citation extraction error: {e}"

    return [search_documents, web_search, extract_citations]


def run_agent(collection_name: str, user_message: str, chat_history: list[BaseMessage]) -> dict[str, Any]:
    """Run the LangGraph ReAct agent and return {answer, tool_calls_made}."""
    settings = get_settings()

    llm = ChatOpenAI(
        model=settings.llm_model,
        temperature=0,
        openai_api_key=settings.openai_api_key,
    )

    tools = _build_tools(collection_name)
    agent = create_react_agent(model=llm, tools=tools, prompt=SYSTEM_PROMPT)

    messages: list[BaseMessage] = list(chat_history) + [HumanMessage(content=user_message)]
    result = agent.invoke(
        {"messages": messages},
        config={"recursion_limit": settings.agent_max_iterations * 2},
    )

    output_messages = result.get("messages", [])
    answer = ""
    for msg in reversed(output_messages):
        if isinstance(msg, AIMessage) and msg.content:
            answer = msg.content if isinstance(msg.content, str) else str(msg.content)
            break

    tool_calls_made: list[str] = []
    for msg in output_messages:
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                name = tc.get("name") if isinstance(tc, dict) else getattr(tc, "name", "")
                if name and name not in tool_calls_made:
                    tool_calls_made.append(name)

    return {"answer": answer, "tool_calls_made": tool_calls_made}
