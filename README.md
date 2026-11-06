# videcoding

本仓库包含两个基于 Streamlit 的示例应用：一个用于本地知识库问答，另一个用于模型聊天。

## AI对话
入口：`ai_friend\ai_friend.py`
运行：

streamlit run app.py

## 知识库问答

入口：`ai_textsearch/app.py`

上传 PDF、DOCX、TXT 或 Markdown 文档，构建向量知识库并针对文档内容提问。文档向量存储在本地 `chroma_db/` 目录。

运行：

```bash
streamlit run app.py
