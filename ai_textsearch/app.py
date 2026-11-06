# app.py
import hashlib
import os
import json
from functools import partial
from pathlib import Path
from this import d
from langchain_ollama import OllamaEmbeddings
import streamlit as st
from langchain_community.document_loaders import (
    PyPDFLoader, Docx2txtLoader, TextLoader, UnstructuredMarkdownLoader,
)
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.output_parsers import StrOutputParser

CONFIG_PATH = Path("./.app_config.json")
UPLOAD_DIR = Path("./uploaded_docs")
UPLOAD_DIR.mkdir(exist_ok=True)

LOADERS = {
    ".pdf": PyPDFLoader,
    ".docx": Docx2txtLoader,
    ".txt": partial(TextLoader, encoding="utf-8"),
    ".md": partial(TextLoader, encoding="utf-8"),
}
def load_config() -> dict:
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Excetion:
            return{}
    return {}
def save_config(cfg:dict) -> None:
    CONFIG_PATH.write_text(
        json.dumps(cfg,ensure_ascii=False,indent=2),
        encoding="utf-8",
    )
#启动时读取一次 （很轻量，每次rerun都读也没问题）
_saved_cfg = load_config()

st.set_page_config(page_title="知识库问答", page_icon="📚", layout="wide")


# ---------------- 工具函数 ----------------

def get_signature(files):
    """根据文件名 + 内容 md5 生成缓存签名"""
    parts = [f"{f.name}:{hashlib.md5(f.getvalue()).hexdigest()[:8]}" for f in files]
    return "|".join(sorted(parts))


def save_files(files):
    """清空并写入上传文件到磁盘（Loader 需要路径）"""
    for p in UPLOAD_DIR.glob("*"):
        p.unlink()
    for f in files:
        (UPLOAD_DIR / f.name).write_bytes(f.getvalue())


# ---------------- 构建知识库（缓存） ----------------

@st.cache_resource(show_spinner=False)
def build_pipeline(signature, chunk_size, chunk_overlap, k, api_tage):
    """签名或参数变化时自动重建；返回值被缓存在内存中"""
    docs = []
    for path in UPLOAD_DIR.rglob("*"):
        loader_cls = LOADERS.get(path.suffix.lower())
        if not loader_cls:
            continue
        try:
            docs.extend(loader_cls(str(path)).load())
        except Exception as e:
            st.warning(f"加载 {path.name} 失败：{e}")

    if not docs:
        return None

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""],
    )
    chunks = splitter.split_documents(docs)

    embedding = OllamaEmbeddings(model="nomic-embed-text:v1.5",base_url="http://localhost:11434")

    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embedding,
        collection_name="knowledge_base",
        persist_directory="./chroma_db",
    )
    retriever = vectorstore.as_retriever(
        search_type="mmr",
        search_kwargs={"k": k, "fetch_k": max(k * 3, 12)},
    )
    return {"num_chunks": len(chunks), "retriever": retriever}


# ---------------- 问答 ----------------

def answer_stream(question, history, retriever, model, base_url):
    """返回 (docs, 生成器)，由调用方用 st.write_stream 渲染"""
    docs = retriever.invoke(question)
    context = "\n\n---\n\n".join(d.page_content for d in docs)

    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "你是一个严谨的知识库问答助手。请仅依据提供的上下文回答。"
         "上下文不足时明确说明“根据已有资料无法回答”，不要编造。\n\n"
         "上下文：\n{context}"),
        MessagesPlaceholder("chat_history"),
        ("human", "{question}"),
    ])

    llm = ChatOpenAI(
        model=model,
        temperature=0,
        base_url=base_url or None,
        streaming=True,          # 关键：开启流式
    )
    chain = prompt | llm | StrOutputParser()

    stream = chain.stream({
        "context": context,
        "chat_history": history,
        "question": question,
    })
    return docs, stream


# ---------------- 主界面 ----------------

def main():
    st.session_state.setdefault("messages", [])
    st.session_state.setdefault("signature", "")

    # ---- 侧边栏 ----
    with st.sidebar:
        st.title("📚 知识库问答")

        # ---- 初始化 session_state (只在第一次进界面时执行) --- 
        if "api_key" not in st.session_state:
            st.session_state.api_key = (
                _saved_cfg.get("api_key")
                or os.getenv("OPENAI_API_KEY", "")
            )
        if "base_url" not in st.session_state:
            st.session_state.base_url = (
                _saved_cfg.get("base_url")
                or os.getenv("OPENAI_BASE_URL", "")
            )
        if "model_name" not in st.session_state:
            st.session_state.model_name = (
                _saved_cfg.get("model_name")
                or "gpt-6-sol"
            )
        # --- 任一项变更时，整组写回磁盘 ---
        def _persist():
            save_config({
                "api_key": st.session_state.api_key,
                "base_url": st.session_state.base_url,
                "model_name": st.session_state.model_name,
            })

        api_key = st.text_input(
            "OpenAI API Key", type="password",
            key="api_key",on_change=_persist,
        )
        base_url = st.text_input(
            "Base URL（可选）", key="base_url",on_change=_persist,
        )
        model = st.text_input(
            "对话模型", key="model_name",on_change=_persist,
        )

        if api_key:
            os.environ["OPENAI_API_KEY"] = api_key
        if base_url:
            os.environ["OPENAI_BASE_URL"] = base_url
        

        st.divider()

        files = st.file_uploader(
            "上传文档", type=["pdf", "docx", "txt", "md"],
            accept_multiple_files=True,
        )

        with st.expander("⚙️ 参数设置", expanded=False):
            chunk_size = st.slider("Chunk Size", 300, 2000, 800, 100)
            chunk_overlap = st.slider("Chunk Overlap", 0, 400, 120, 20)
            k = st.slider("召回条数 k", 1, 10, 4)

        c1, c2 = st.columns(2)
        with c1:
            if st.button("🗑️ 清空对话", use_container_width=True):
                st.session_state.messages = []
                st.rerun()
        with c2:
            if st.button("🔄 重建库", use_container_width=True):
                st.cache_resource.clear()
                st.session_state.signature = ""
                st.rerun()
        
        # 清除记忆
        def _clear_config():
            if CONFIG_PATH.exists():
                CONFIG_PATH.unlink()
            st.session_state.api_key = ""
            st.session_state.base_url = ""
            st.session_state.model_name = "gpt-4o-mini"

        st.button(
            "🧹 清除配置记忆",
            use_container_width=True,
            on_click=_clear_config,
        )

    

    # ---- 主区标题 ----
    st.title("💬 知识库问答")
    st.caption("上传文档后即可基于文档内容提问，回答会附带引用来源。")

    # ---- 构建/复用知识库 ----
    pipeline = None
    if files:
        sig = get_signature(files)
        if sig != st.session_state.signature:
            save_files(files)
            st.session_state.signature = sig

        api_tag = hashlib.md5(f"{api_key}|{base_url}".encode()).hexdigest()[:8]
        with st.spinner("正在构建知识库（首次构建可能较慢）..."):
            pipeline = build_pipeline(sig, chunk_size, chunk_overlap, k, api_tag)

        if pipeline:
            st.success(f"✅ 知识库已就绪：共 {pipeline['num_chunks']} 个文本片段")
    else:
        st.info("👈 请在左侧上传文档（支持 PDF / DOCX / TXT / MD）")

    st.divider()

    # ---- 渲染历史消息 ----
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("sources"):
                with st.expander(f"📎 引用 {len(msg['sources'])} 个片段"):
                    for i, s in enumerate(msg["sources"], 1):
                        st.markdown(f"**{i}. {s['source']}**")
                        st.caption(s["content"][:400] + "…")

    # ---- 输入区 ----
    if prompt := st.chat_input("请输入问题，例如：这份文档的主要结论是什么？"):
        if not api_key:
            st.error("请先在左侧填写 OpenAI API Key")
            st.stop()
        if not pipeline:
            st.error("请先上传文档")
            st.stop()

        # 渲染用户消息
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # 把历史消息转成 LangChain Message 对象（不含最后一条用户消息）
        history = []
        for m in st.session_state.messages[:-1]:
            if m["role"] == "user":
                history.append(HumanMessage(content=m["content"]))
            else:
                history.append(AIMessage(content=m["content"]))

        with st.chat_message("assistant"):
            try:
                docs, stream = answer_stream(
                    prompt, history,
                    pipeline["retriever"], model, base_url,
                )
            except Exception as e:
                st.error(f"❌ 检索或初始化失败：{e}")
                st.stop()

            # 流式渲染，返回拼接后的完整文本
            text = st.write_stream(stream)
            # 引用片段在流结束后再展示
            sources = [
                {
                    "source": Path(d.metadata.get("source", "unknown")).name,
                    "content": d.page_content,
                }
                for d in docs
            ]
            if sources:
                with st.expander(f"📎 引用 {len(sources)} 个片段"):
                    for i, s in enumerate(sources, 1):
                        st.markdown(f"**{i}. {s['source']}**")
                        st.caption(s["content"][:400] + "…")
main()