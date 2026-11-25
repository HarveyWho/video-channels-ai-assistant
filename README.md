# 视频号直播答疑助手

Windows 视频号直播伴侣开播时，在本机识别评论问题，并在悬浮提词窗口显示答案。支持 **本地 Ollama 模型**、**本地固定问答**，以及手动选择的 **DeepSeek 云端**。本地模式不会自动回退到云端。

当前版本：**v0.3.0-rc1 · 2B + 4B 完整离线包**。已内置 Qwen3.5 两个模型及 Ollama Windows x64 CPU 运行组件，不用另装 Ollama、不用输入模型下载命令、不需要 API Key。首次加载和切换模型仍需等待。

## Windows 完整离线包下载（推荐）

**[打开 v0.3.0-rc1 下载页](https://github.com/HarveyWho/video-channels-ai-assistant/releases/tag/v0.3.0-rc1)**。只有所有文件上传、校验完成后才会公开该版本。

GitHub 单个文件上限为 2 GiB，因此完整包按 1800 MiB 分卷。模型只放在 Releases 下载资产中，不放入 Git 源码历史。**需要下载安装工具 ZIP 和全部离线分卷**，不能只下载第一卷。

完整包总下载约 **6.4GB**，请下载下面 **全部 5 个文件**：

| 文件 | 大小 | 下载 |
|---|---:|---|
| 安装与解压工具 | 约 1.1MB | [Windows.Offline.Setup.zip](https://github.com/HarveyWho/video-channels-ai-assistant/releases/download/v0.3.0-rc1/Windows.Offline.Setup.zip) |
| 第 1 卷 | 约 1.89GB | [Offline.7z.001](https://github.com/HarveyWho/video-channels-ai-assistant/releases/download/v0.3.0-rc1/Live.Answer.Assistant.Offline.7z.001) |
| 第 2 卷 | 约 1.89GB | [Offline.7z.002](https://github.com/HarveyWho/video-channels-ai-assistant/releases/download/v0.3.0-rc1/Live.Answer.Assistant.Offline.7z.002) |
| 第 3 卷 | 约 1.89GB | [Offline.7z.003](https://github.com/HarveyWho/video-channels-ai-assistant/releases/download/v0.3.0-rc1/Live.Answer.Assistant.Offline.7z.003) |
| 第 4 卷 | 约 734MB | [Offline.7z.004](https://github.com/HarveyWho/video-channels-ai-assistant/releases/download/v0.3.0-rc1/Live.Answer.Assistant.Offline.7z.004) |

1. 在一个空文件夹中保存 `Windows.Offline.Setup.zip` 和全部 `Live.Answer.Assistant.Offline.7z.001`、`.002`、`.003`……文件。以下载页实际列出的最后一卷为准；不要改文件名。
2. 右键 `Windows.Offline.Setup.zip` → **全部解压**。工具解压到当前文件夹或它的一个子文件夹都可以；不要在 ZIP 预览窗口中直接运行。
3. 双击解压出来的 **Install Offline.cmd**。脚本先检查每卷的大小与 SHA256，再解压完整软件。工具已自带 7-Zip，无需另外安装解压软件、Python 或 Ollama，也不需要管理员权限。
4. 解压完成后自动打开 **Live Answer Assistant.exe**。以后直接运行它。保留旁边的 `_internal`、`Local Runtime`、`Models` 和许可证文件夹；不要单独移动 EXE。
5. 到 **模型与直播资料 → 模型连接 → 本地 Ollama**，选择 `qwen3.5:2b` 或 `qwen3.5:4b`，点击 **测试连接 / 预热本地模型**，然后 **应用设置**。

建议准备 **至少 20GB 可用磁盘空间**用于保留下载分卷和解压文件。运行要求 Windows 10 22H2 / Windows 11 x64；Surface Laptop 3 / 16GB 可尝试，实际速度与直播编码负载有关。完整包采用 CPU 运行组件，不包含 NVIDIA CUDA / AMD ROCm GPU 加速库。软件与安装脚本尚未签名，请核对来源。

首次加载模型可能较慢。测试结果显示首字和完整回答耗时；用同一组常见直播问题比较 2B、4B，再选择能接受的质量与等待时间。4B 的参数量更大，不能据此保证每个问题都更准确。

内置服务按需自动启动，仅绑定本机回环地址的独立端口；使用包内 `Models` 文件夹，不替换电脑中已有的 Ollama 或模型。退出助手时关闭自己启动的服务；切换模型时只保留一个模型在内存中。本地模式关闭 Ollama 云功能，不自动回退到 DeepSeek。

本地生成参考资料最多 3000 字，问题最多 600 字。固定问答可直接显示你确认过的答案。生成模型没有联网检索，资料不足时仍需主播确认。

[Ollama Windows 运行组件说明](https://docs.ollama.com/windows) · [Qwen3.5 2B](https://ollama.com/library/qwen3.5:2b) · [Qwen3.5 4B](https://ollama.com/library/qwen3.5:4b)

## 已有 Ollama 的轻量包（可选）

`Live.Answer.Assistant.Windows.zip` 只包含助手和 OCR，**不含生成模型与 Ollama**。已经自行安装 Ollama、下载好模型的用户才需要这个 ZIP。解压后运行 EXE，连接本机 `127.0.0.1:11434`。首次使用请选择上面的完整离线包。

源码页的 **Code → Download ZIP** 也不包含模型。

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

固定演示：`python app.py --demo`，不连接模型、不采集屏幕。Windows 独立包由 GitHub Actions 打包；本地开发打包需安装 `requirements build.txt` 并运行 `python package.py`；完整离线分卷再运行 `python build_offline.py`，会下载并校验 `bundled_models.json` 固定的模型与运行组件。

离线发布会检查源码和打包后的 OCR、界面构造，实际运行两个内置模型生成回答，并测试分卷安装与校验；这些检查不代表你电脑上的模型速度或真实视频号直播已通过。[查看 Actions](https://github.com/HarveyWho/video-channels-ai-assistant/actions)。

项目自行编写的代码采用 [MIT License](LICENSE)。第三方组件保留各自许可证，见 [THIRD PARTY NOTICES.md](THIRD%20PARTY%20NOTICES.md)。与微信、腾讯、视频号、DeepSeek 或 Ollama 均无官方隶属关系。
