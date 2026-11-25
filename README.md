# 视频号直播答疑助手

Windows 视频号直播伴侣开播时，在本机识别评论问题，并在悬浮提词窗口显示答案。支持 **本地 Ollama 模型**、**本地固定问答**，以及手动选择的 **DeepSeek 云端**。本地模式不会自动回退到云端。

当前版本：**v0.2.0-rc1**。这是试播版，生成质量和速度需要在你的实际直播电脑上测试。旧版 v0.1.0-rc1 不支持本地生成。

## Windows 下载

1. 打开 [Releases](https://github.com/HarveyWho/video-channels-ai-assistant/releases)，选择 **v0.2.0-rc1**。
2. 在 Assets 中下载 **Live.Answer.Assistant.Windows.zip**。构建完成后才会出现这个文件。
3. 右键“全部解压”，运行文件夹里的 **Live Answer Assistant.exe**，保留旁边的 `_internal` 文件夹。无需安装 Python。
4. 程序标题应显示 **v0.2.0-rc1**。程序未签名；请核对来源、保留安全软件保护，必要时使用下面的源码方式。

ZIP 只包含助手、OCR 及其运行环境，**不包含 Ollama 或大语言模型权重**。

## Surface Laptop 3 / 16GB 的本地设置

此配置可以尝试小模型，但 CPU 推理、直播编码与 OCR 会竞争资源。无法保证本地比云端更快，也不能把小模型当成完全准确的答案来源。

1. 从 [Ollama 官方 Windows 下载页](https://ollama.com/download/windows)安装最新版 Ollama，并让它保持运行。
2. 重新打开 PowerShell，执行下面的命令下载模型。模型约数 GB，请预留磁盘空间：

```powershell
ollama pull qwen3.5:2b
```

3. 打开助手的 **模型与资料设置 → 模型连接**，选择 **本地 Ollama**，模型填 `qwen3.5:2b`。本地模式不需要 DeepSeek 密钥。
4. 点击 **测试连接 / 预热本地模型**，首次加载可能较慢。成功后会显示首字和完整回答耗时，再点 **应用设置**。
5. 先手动输入直播中常见的问题测试，再边试播边测。若速度和答案质量可以接受，再考虑 `qwen3.5:4b`；4B 需要单独执行 `ollama pull qwen3.5:4b`，通常需要更多资源。

程序通过 `http://127.0.0.1:11434/api/chat` 连接本机 Ollama，设置 `think: false`、模型保留时间 `10m`、短回答和有限上下文。只使用已下载的本地模型，不使用带 cloud 的模型标签。请求在本地服务内的具体处理由你安装的 Ollama 决定。

本地生成参考资料最多 3000 字，问题最多 600 字；过长资料会明确提示精简，不会悄悄截掉。先以 2B 小模型和简短资料实测，避免一边直播一边首次加载大模型。

[Ollama 官方接口说明](https://docs.ollama.com/api/chat) · [Qwen3.5 2B 模型](https://ollama.com/library/qwen3.5:2b)

## 固定问题直接显示确认过的答案

对于报名、课表、费用等问题，最快且可控的方式是使用你自己确认过的原文。到 **直播资料** 页按以下格式填写：

```text
问：请问怎么报名？
答：在这里填写你确认过的报名流程。

问：一周几次课？
答：在这里填写真实课表。
```

问题严格匹配后，直接显示对应答案，不调用本地或云端模型。只统一标点、空格和常见昵称前缀，不做模糊语义猜测，因此不同年级、数字和价格不会混在一起。问法不同就增加另一组“问 / 答”。若同一个问题配置了冲突答案，不会直接采用其中一个。示例文字请换成真实资料。

## 使用 DeepSeek 云端（可选）

到模型设置中主动选择 **DeepSeek 云端**，填写自己在 [DeepSeek 开放平台](https://platform.deepseek.com/api_keys)创建的 API Key，测试后应用。密钥只在本次运行内存中，不写进配置文件；云端按 API 用量收费。

模型仍为 `deepseek-flash`，关闭思考输出、逐字显示短答案。本地连接失败时不会自动调用 DeepSeek。云端也不保证固定响应时间。

## 开播和第三次没响应时的检查

1. 打开直播伴侣，框选可见的评论区域。不要遮住评论列表。
2. 点击 **开始监听**。新版默认处理当前可见问题；可在资料设置里关闭这个选项。
3. 状态栏会显示识别、过滤、去重和本帧入队数量。没有入队时，会提示是没读到文字、没有疑问句、重复问题，还是跳过了启动画面。
4. 重复使用同一问题测试时，点击 **重读当前弹幕**。它会清除识别去重记录，重新读取可见问题；队列中已经等待或生成的同题不会重复加入。
5. 下方会显示所用模型、首字等待时间和生成状态。首字长时间不出现或整体超时会停止等待，显示原因，可以选中问题重试。
6. 当前答案会保留，后续答案不会自动顶走它。读完点 **下一条**，提词窗口有焦点时可按 **Ctrl + 右方向键**。手动输入或选中的待生成问题会优先处理。
7. 没读到问题时，可先手动输入带问号的问题测试。只处理疑问句是规则筛选，可在设置里关闭。

点击 **暂停** 会请求取消模型读取，并停止监听。网络建立阶段可能仍需等连接超时。已经发出的云端请求可能仍计费，不会自动反复重试。

开始正式直播前检查采集源，确保密钥、参考资料和不准备公开的提词窗口没有被直播画面采集。

## 限制与隐私

- 通过可见屏幕 OCR 读取评论，没有使用视频号官方弹幕 API。高速滚屏、遮挡和复杂排版可能漏读。
- 最多 8 条待生成或生成中的问题，超过上限会跳过并提示；需要时手动补充或重读。
- AI 的事实与语言质量需要主播确认，尤其是价格、时间和政策。本程序没有联网检索功能。
- 模型选择、资料、字号等设置保存在 `%LOCALAPPDATA%/Live Answer Assistant/settings.json`。同目录 `diagnostics.log` 记录后端、请求编号、耗时和错误类型，不主动记录问题、回答、主题、资料或密钥。
- 屏幕图像不保存、不上传。本地模式连接本机；云端模式会将问题、主题和资料发送给 DeepSeek。详细说明见 [PRIVACY.md](PRIVACY.md)。

## 源码方式

仓库首页选择 **Code → Download ZIP**。安装官方 [Windows x64 Python 3.11–3.13](https://www.python.org/downloads/windows/)，保留 Tcl/Tk 组件并勾选 Add python.exe to PATH，解压后双击 `Start.bat`。

```powershell
py -3.13 -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
.venv/Scripts/python.exe -m unittest -v tests
.venv/Scripts/python.exe app.py
```

固定演示：`python app.py --demo`，不连接模型、不采集屏幕。Windows 独立包由 GitHub Actions 打包；本地开发打包需安装 `requirements build.txt` 并运行 `python package.py`。

每次发布会检查源码和打包后的 OCR、界面构造；这些检查不代表你电脑上的模型速度或真实视频号直播已通过。[查看 Actions](https://github.com/HarveyWho/video-channels-ai-assistant/actions)。

项目自行编写的代码采用 [MIT License](LICENSE)。第三方组件保留各自许可证，见 [THIRD PARTY NOTICES.md](THIRD%20PARTY%20NOTICES.md)。与微信、腾讯、视频号、DeepSeek 或 Ollama 均无官方隶属关系。
