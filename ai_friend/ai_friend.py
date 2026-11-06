from datetime import datetime

import streamlit as st
import os
import json
import uuid
from openai import OpenAI

SESSIONS_FILE = os.path.join(os.path.dirname(__file__), "sessions.json")

def load_sessions():
    if os.path.exists(SESSIONS_FILE):
        with open(SESSIONS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_sessions(sessions):
    with open(SESSIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(sessions, f, ensure_ascii=False, indent=2)

# 页面配置
st.set_page_config(
    page_title="AI智能伴侣",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="auto",
    menu_items={}
)

# 创建与AI大模型交互的客户端
# client = OpenAI(api_key=os.environ.get("DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com")
client = OpenAI(api_key="ollama", base_url="http://localhost:11434/v1")
time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
# ========== 初始化会话数据 ==========
if "sessions" not in st.session_state:
    st.session_state.sessions = load_sessions()

if "current_session_id" not in st.session_state:
    if st.session_state.sessions:
        st.session_state.current_session_id = st.session_state.sessions[0]["id"]
    else:
        new_id = str(uuid.uuid4())

        st.session_state.sessions = [{"id": new_id, "name": f"{time}", "system_prompt": "", "messages": []}]
        st.session_state.current_session_id = new_id
        save_sessions(st.session_state.sessions)

def get_current_session():
    for s in st.session_state.sessions:
        if s["id"] == st.session_state.current_session_id:
            return s
    return None

def sync_to_storage():
    save_sessions(st.session_state.sessions)

# ========== 侧边栏 ==========
with st.sidebar:
    st.title("AI智能伴侣")

    if st.button("➕ 新建会话", use_container_width=True):
        new_id = str(uuid.uuid4())
        new_session = {"id": new_id, "name": f"{time}", "system_prompt": "", "messages": []}
        st.session_state.sessions.append(new_session)
        st.session_state.current_session_id = new_id
        sync_to_storage()
        st.rerun()

    st.divider()
    st.markdown("##### 会话列表")

    if "renaming_session_id" not in st.session_state:
        st.session_state.renaming_session_id = None

    for s in st.session_state.sessions:
        if st.session_state.renaming_session_id == s["id"]:
            cols = st.columns([0.7, 0.15, 0.15])
            with cols[0]:
                new_name = st.text_input("会话名称", value=s["name"], key=f"rename_input_{s['id']}",
                                         label_visibility="collapsed")
            with cols[1]:
                if st.button("✅", key=f"confirm_{s['id']}"):
                    if new_name.strip():
                        s["name"] = new_name.strip()
                        sync_to_storage()
                    st.session_state.renaming_session_id = None
                    st.rerun()
            with cols[2]:
                if st.button("❌", key=f"cancel_{s['id']}"):
                    st.session_state.renaming_session_id = None
                    st.rerun()
        else:
            cols = st.columns([0.7, 0.15, 0.15])
            with cols[0]:
                if st.button(s["name"], key=f"switch_{s['id']}", use_container_width=True,
                             type="primary" if s["id"] == st.session_state.current_session_id else "secondary"):
                    st.session_state.current_session_id = s["id"]
                    st.rerun()
            with cols[1]:
                if st.button("✏️", key=f"rename_{s['id']}"):
                    st.session_state.renaming_session_id = s["id"]
                    st.rerun()
            with cols[2]:
                if st.button("🗑️", key=f"del_{s['id']}"):
                    if len(st.session_state.sessions) > 1:
                        st.session_state.sessions = [x for x in st.session_state.sessions if x["id"] != s["id"]]
                        if st.session_state.current_session_id == s["id"]:
                            st.session_state.current_session_id = st.session_state.sessions[0]["id"]
                        sync_to_storage()
                        st.rerun()
# ========== 主区域 ==========
current = get_current_session()

st.title("AI智能伴侣")
st.caption(f"当前会话：{current['name']}")

with st.sidebar:
    st.divider()
    st.markdown("##### ⚙️ 系统提示词")
    st.markdown("""
            <style>
            textarea[data-testid="stTextArea"][aria-label="请输入系统提示词"] {
                min-height: 150px;
                resize: vertical !important;
            }
            </style>
        """, unsafe_allow_html=True)
    new_prompt = st.text_area("请输入系统提示词", value=current["system_prompt"], key=f"prompt_{current['id']}")
    if new_prompt != current["system_prompt"]:
        current["system_prompt"] = new_prompt
        sync_to_storage()

# 显示聊天消息
for message in current["messages"]:
    st.chat_message(message["role"]).write(message["content"])

# 对话
prompt = st.chat_input("请输入你的问题")
if prompt:
    st.chat_message("user").write(prompt)
    current["messages"].append({"role": "user", "content": prompt})

    response = client.chat.completions.create(
        # model="deepseek-chat",
        model="deepseek-r1:8b",
        messages=[
            {"role": "system", "content": current["system_prompt"]},
            *current["messages"]
        ],
        stream=True,
    )

    placeholder = st.empty()
    ai_response = ""
    for chunk in response:
        if chunk.choices[0].delta.content is not None:
            ai_response += chunk.choices[0].delta.content
            placeholder.write(ai_response)

    current["messages"].append({"role": "assistant", "content": ai_response})
    sync_to_storage()