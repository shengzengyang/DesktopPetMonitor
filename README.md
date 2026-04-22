# 🐾 DesktopPetMonitor · doro 桌宠

> *A Live2D desktop pet (doro) that chats with GPT/Claude, runs around your screen, monitors system stats, and keeps you company while you code.*

[English](#english) · [简体中文](#简体中文)

---

## 📣 项目缘起 / Project Origin

**中文**:做这个项目的初衷,是因为用 Claude 的时候总担心自己 IP 不小心变了没察觉,以及开机之后忘记打开代理 —— 所以就做了这样一个 doro 桌宠,让它帮我盯着 IP 和系统状态。

本项目可能存在 bug,如果你遇到问题或者想到了新功能,**欢迎提 Issue**,我们会在空余时间修复和跟进。如果你也有想法、想合作、或者**想定制自己的专属角色模型**,也欢迎联系我们 —— **最好是你自己能提供 Live2D 文件**(`.moc3` + `.model3.json` + 纹理等),因为我们对 Live2D 本身的建模/绑定并不熟悉,主要擅长的是把它接进来。

📬 **联系方式 · Telegram**:[@gogogoyang](https://t.me/gogogoyang)

---

**English**: This project was created because I kept worrying about accidentally changing my IP while using Claude, and I often forgot to turn the proxy on after boot — so I built this doro pet to watch the IP and system status for me.

There may be bugs. If you run into anything or have feature ideas, **please open an issue** — we'll fix and improve in our spare time. If you have suggestions, want to collaborate, or **want a custom character model tailored to you**, contact us too. **Ideally you provide the Live2D files yourself** (`.moc3` + `.model3.json` + textures), because we're not very experienced with Live2D modeling/rigging itself — our strength is in wiring it up.

📬 **Contact · Telegram**: [@gogogoyang](https://t.me/gogogoyang)

---

<!-- ============================================================ -->
## 演示视频 / Demo Video

<!-- TODO: 把演示视频放到这个区域,B 站/YouTube 嵌入或上传到 docs/assets/demo.mp4 -->

<div align="center">

<!-- 
在这里替换成你的 B 站 iframe 或 GitHub 上传的 MP4/GIF。例如:

<video src="docs/assets/demo.mp4" controls width="720"></video>

或 B 站:

<iframe src="//player.bilibili.com/player.html?bvid=BVxxxxx&page=1" width="720" height="405" allowfullscreen></iframe>
-->

**[ 📺 演示视频占位 — 待添加 / Demo video placeholder — TBD ]**

</div>

---

<!-- ============================================================ -->

## 简体中文

### 这个项目是什么

**DesktopPetMonitor** 是一个基于 Live2D 的 Windows 桌面宠物,主角是 **doro** —— 来自手游《胜利女神:NIKKE》的粉色 Q 版小精灵。桌宠会在你屏幕上闲逛、跑步、做表情、陪你聊天,并在侧边悬浮面板里实时显示 CPU/内存/GPU/网络监控、番茄钟、IP 告警等。

这个项目使用了开源社区的 Live2D 模型(作者 `0x4682B4`),通过 `live2d-py` 渲染;AI 对话支持直连官方 API(OpenAI / Anthropic / Google 等)或任意 OpenAI 兼容中转站。

### 功能速览

- 🎭 **Live2D 桌宠**:11 种表情(墨镜 / 星星眼 / 问号 / 吐舌 ...)+ 7 种自定义动作(点头 / 摇头 / 跳舞 / 惊讶 / 跑步 / 伸懒腰 / 挣扎)
- 🏃 **全屏闲逛**:真·四足跨步 + 速度线特效,doro 会在整个桌面上跑来跑去
- 💬 **AI 对话**:Ctrl+Space 呼出输入框,接入 GPT / Claude / Gemini 等,流式响应
- 📊 **系统监视**:CPU / 内存 / GPU / 显存 / 网速 / IP 都在悬浮面板里,IP 改变时可触发 doro 告警
- 🍅 **番茄钟 + 久坐提醒**:自动进入"专注"动作状态
- 🖱 **交互**:拖拽会挣扎、右键菜单、鼠标滚轮缩放、边缘吸附
- 🌏 **多语言**:中文 / English,可在设置里切换
- 📝 **日志**:轮转文件日志,排查问题方便

### 快速开始

**环境要求**
- Windows 10/11(OpenGL 3.0+)
- Python 3.10+

**安装 & 运行**

```bash
# 1. 克隆仓库
git clone https://github.com/<you>/DesktopPetMonitor.git
cd DesktopPetMonitor

# 2. 建虚拟环境并装依赖
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# 3. 启动桌宠
python main.py
```

桌宠启动后:
- **左键单击**:打开/关闭信息面板
- **左键拖拽**:移动位置,doro 会挣扎
- **左键双击**:表白反应
- **右键**:完整菜单(对话 / 表情 / 动作 / 大小 / 切换模型 / 设置 / 退出)
- **滚轮**:快速缩放
- **Ctrl + Space**:唤出聊天框

### AI 对话配置

右键 doro → **⚙ 设置** → **对话 (GPT)** 标签页。两种接入方式:

#### 1. 官方 API 接入

填写对应厂商的 Base URL 和 API Key:

| 提供商 | Base URL | 示例 Model |
|---|---|---|
| **OpenAI** | `https://api.openai.com/v1` | `gpt-4o-mini`, `gpt-5`, `o1` |
| **Anthropic Claude** | `https://api.anthropic.com/v1` | `claude-sonnet-4-5-20250929`, `claude-3-5-haiku` |
| **Google Gemini** | `https://generativelanguage.googleapis.com/v1beta/openai` | `gemini-2.0-flash` |
| **DeepSeek** | `https://api.deepseek.com/v1` | `deepseek-chat`, `deepseek-reasoner` |
| **Moonshot / Kimi** | `https://api.moonshot.cn/v1` | `moonshot-v1-8k` |
| **通义千问** | `https://dashscope.aliyuncs.com/compatible-mode/v1` | `qwen-plus`, `qwen-max` |
| **智谱 GLM** | `https://open.bigmodel.cn/api/paas/v4` | `glm-4`, `glm-4-flash` |
| **硅基流动** | `https://api.siliconflow.cn/v1` | `deepseek-ai/DeepSeek-V3` |

> **模型路由**:代码会根据模型名自动选择端点 —— `gpt-5*` / `o1*` / `o3*` / `o4*` 走 `/v1/responses`(reasoning 模型专用);其他走 `/v1/chat/completions`。

#### 2. 中转站接入

任意 OpenAI 兼容的中转站都可以,Base URL 填中转站给你的地址(例如 `https://xxx.example.com/v1`),Key 填中转站 Key,模型名按中转站文档填。**推荐用支持流式响应的中转**,代码目前强制走流式。

已验证可以跑通的中转站特征:
- Path 是 `/v1/chat/completions` 或 `/v1/responses`
- 响应 `Content-Type` 带 `text/event-stream`(流式)
- 按 OpenAI 的 SSE 格式发 `data: {...}` 块

### 切换 / 新增 doro 模型

模型文件放在 `assets/<kind>/<name>/` 下,包含:
- `*.moc3`(必须)· Live2D 编译后的模型
- `*.model3.json`(必须)· 引用表
- `*.physics3.json`、`*.cdi3.json`、纹理、表情、动作 …

要加一只新角色,最快的办法:在 `pets.py` 的 `PETS` 字典里复制 `'dororong'` 条目,改名字、路径、参数映射即可。详细步骤看 [`CLAUDE.md`](./CLAUDE.md)。

**我们欢迎你贡献新的 Live2D 角色!** 如果你有合法授权的 `.moc3` + 源工程(`.cmo3`),或者想让 doro 有"全身绑定版"、别的人物等,欢迎 Issue / PR 联系我们,提交时请附上:
- Live2D 模型的**来源授权**说明(二次分发许可很重要)
- `.moc3` + `.model3.json` + 纹理图集 + 物理 + 表情
- 最好有原 `.cmo3` 工程,这样大家可以继续调绑定
- 建议的角色名、idle / 问候语等

### 贡献 / 开发

**强烈推荐用 [Claude Code](https://claude.com/claude-code) 或类似 AI 工具开发** —— 本项目 95% 的代码是我和 Claude 协作写的,项目里专门准备了一份 [`CLAUDE.md`](./CLAUDE.md) 给 AI 看,包含:
- 完整模块架构图
- Live2D 参数字典
- Qt.Tool + Frameless 的已知坑
- 怎么加新动作 / 表情 / 模型
- 怎么改 i18n

你只要 clone 下来,在 IDE 里让 Claude 打开 CLAUDE.md,剩下的让 AI 读完你再让它改就行。

### 项目说明 / 致谢

- **doro 角色** · © SHIFT UP / TENCENT 《胜利女神:NIKKE》
- **Live2D 模型** · by [0x4682B4](https://booth.pm/) (Booth 平台购买的社区作品,感谢作者)
- **Live2D Cubism SDK** · © Live2D Inc.
- **live2d-py** · Python 绑定,桌宠核心渲染
- **PyQt5** · UI 框架

### License

MIT — 见 [LICENSE](./LICENSE)。

**注意**:本仓库仅包含**代码**的 MIT 授权。`assets/dororong/Doro/` 下的 `.moc3` 和纹理图集属于原作者,请尊重其授权条款(通常禁止商用 / 再分发)。如要开源分发,建议:
- 不 commit 模型文件,只 commit 下载脚本
- 或联系原作者拿到明确的二次分发许可

---

<!-- ============================================================ -->
## English

### What is this

**DesktopPetMonitor** is a Windows desktop pet powered by Live2D. The star is **doro**, a pink chibi sprite from the mobile game *Goddess of Victory: NIKKE*. She wanders your screen, runs around with speed lines, reacts to drags, chats with GPT / Claude, and shows CPU / memory / GPU / network stats in a floating panel.

### Features

- 🎭 **Live2D pet** with 11 expressions (sunglasses / star eyes / question mark / etc.) and 7 motions (nod / shake / dance / surprised / run / stretch / struggle)
- 🏃 **Full-screen wandering** with stepping gait animation + speed lines
- 💬 **LLM chat** via Ctrl+Space — OpenAI / Claude / Gemini / any OpenAI-compatible proxy, streaming responses
- 📊 **System monitor** — CPU, memory, GPU, network, IP. IP mismatch alert built-in.
- 🍅 **Pomodoro + sit-reminder**
- 🖱 **Interactions** — drag to struggle, right-click menu, wheel to resize, edge snapping
- 🌏 **i18n** — 中文 / English toggle in settings

### Quick Start

```bash
git clone https://github.com/<you>/DesktopPetMonitor.git
cd DesktopPetMonitor
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

### Configuring the LLM

Right-click doro → **⚙ Settings** → **Chat (GPT)**. Two modes:

**Official APIs** — see the table in the Chinese section above. Model name auto-routes to `/v1/responses` (for `gpt-5*`, `o1*`, `o3*`, `o4*`) or `/v1/chat/completions` (everything else).

**Proxy / relay services** — any OpenAI-compatible proxy with streaming SSE works. Fill in Base URL + Key + Model name.

### Contributing

Prepared for AI-assisted development. See [`CLAUDE.md`](./CLAUDE.md) for an architectural tour aimed at Claude Code / AI agents. We welcome Live2D model contributions — please include source license.

### License

MIT for code. Live2D assets belong to their original authors — check `assets/` authorship before redistributing.
