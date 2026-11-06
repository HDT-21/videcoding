# videcoding

# AI 智能应用

本仓库包含两个使用 Streamlit 构建的 AI 应用：

- `ai_textsearch/ai_textsearch.py`：知识库问答。上传文档后，在本地构建向量知识库，并通过配置的聊天模型回答问题。
- `ai_friend/ai_friend.py`：AI 聊天伴侣。支持多会话聊天，并将会话记录保存在本地。

## 项目内容

```text
.
├── ai_textsearch/                 # 知识库问答应用
    └── ai_textsearch.py 
└── ai_friend/
    └── ai_friend.py               # 多会话 AI 聊天应用
```

运行应用后，还可能在本地生成配置、上传文件、聊天记录或向量数据库等数据文件。这些文件不属于源码，不应提交到公开仓库。

## 运行环境

- Python：建议使用 Python 3.11 或 3.12，并确保所选依赖版本支持该 Python 版本。
- `pip`：用于安装 Python 依赖。
- Ollama：两个应用都使用本机 Ollama；知识库应用需要文本嵌入模型，聊天伴侣默认需要聊天模型。
- 聊天 API：知识库应用需要一个 OpenAI 兼容的聊天 API。可以使用云端服务，也可以配置为可访问的本地服务。

## 安装

### 1. 创建虚拟环境

在仓库根目录打开终端。

Windows PowerShell：

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

macOS / Linux：

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. 安装 Python 依赖

```bash
python -m pip install --upgrade pip
python -m pip install streamlit openai langchain-ollama langchain-community langchain-text-splitters langchain-openai langchain-chroma langchain-core pypdf docx2txt
```

本仓库当前没有锁定依赖版本的 `requirements.txt`。正式部署前，建议验证兼容性后生成并维护依赖清单。

### 3. 安装并准备 Ollama 模型（可选）

安装并启动 Ollama，然后获取两个应用使用的模型：

```bash
ollama pull nomic-embed-text:v1.5
ollama pull deepseek-r1:8b
```

确认 Ollama 服务可用，并且模型已经下载：

```bash
ollama list
```

`app.py` 默认连接 `http://localhost:11434` 获取文档嵌入。`ai_friend/02_.py` 默认连接 `http://localhost:11434/v1` 进行聊天。

## 配置聊天服务

### 知识库问答：`ai_textsearch.py`

启动应用后，在侧边栏配置：

- API Key
- Base URL
- 对话模型名称

聊天服务需要兼容 OpenAI API。配置的 Base URL 应指向当前聊天服务的 API 地址；使用云端 API 时，需要有效的服务商密钥。

也可以通过环境变量提供默认值：

Windows PowerShell：

```powershell
$env:OPENAI_API_KEY = "你的 API Key"
$env:OPENAI_BASE_URL = "服务商提供的 API Base URL"
```

macOS / Linux：

```bash
export OPENAI_API_KEY="你的 API Key"
export OPENAI_BASE_URL="服务商提供的 API Base URL"
```

应用会将侧边栏配置写入仓库根目录下的 `.app_config.json`。该文件以明文保存配置，请勿提交真实 API Key。

### AI 聊天伴侣：`ai_friend/ai_friend.py`

聊天伴侣默认使用本机 Ollama 的 `deepseek-r1:8b`。若需更改模型或服务地址，请修改 `ai_friend/02_.py` 中的模型名称和 `base_url` 配置。

## 运行

在仓库根目录启动知识库问答：

```bash
python -m streamlit run ai_textsearch/ai_textsearch.py
```

在仓库根目录启动 AI 聊天伴侣：

```bash
python -m streamlit run ai_friend/ai_friend.py
```

启动后，Streamlit 会在终端显示本地访问地址。按 `Ctrl+C` 可停止应用。

## 数据与隐私

应用会在本地保存运行数据：

- `.app_config.json`：知识库应用保存的 API Key、Base URL 和模型名称。
- `uploaded_docs/`：知识库应用保存的上传文档。
- `chroma_db/`：知识库应用保存的向量数据库。
- `ai_friend/sessions.json`：聊天伴侣保存的会话和聊天内容。

请勿将上述文件或目录提交到公开仓库。建议在仓库根目录的 `.gitignore` 中排除它们，以及 `.venv/` 和 `__pycache__/`。

知识库问答会将检索到的文档片段发送给配置的聊天模型服务以生成回答。上传敏感文档前，请确认该服务的隐私政策和数据处理方式符合要求。聊天伴侣默认连接本机 Ollama；如将服务地址改为远程服务，聊天内容会发送到该服务。

## 部署说明

本机 Ollama 地址只在运行应用的机器上有效。部署到其他电脑或云平台时，部署环境必须能够访问 Ollama 服务；`localhost` 指向部署应用所在的机器，而不是访问者的电脑。

部署时还需要在部署环境中安装 Python 依赖、配置聊天服务，并为本地数据目录做好持久化和访问控制。

## 安全注意事项

- 不要把 API Key、`.app_config.json`、聊天记录、个人资料、上传文档或向量数据库提交到 GitHub。
- 如果 API Key 曾被提交到公开仓库，请立即在服务商处撤销并重新生成。
- 上传文档前确认聊天模型服务是否会接收或保存文档片段。
- 不要在不可信网络上公开运行 Streamlit 应用，除非已配置适当的身份验证和网络访问控制。
