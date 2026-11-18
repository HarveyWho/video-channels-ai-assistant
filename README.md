# 视频号直播答疑助手

Windows 视频号直播伴侣开播时，框选评论区域，助手在本机识别新问题，交给 DeepSeek 生成答案，并在悬浮大字提词窗口显示。主播读完后切换下一条，后续回答不会自动顶走当前内容。

**当前为试播测试版。正式使用前，请先用你的 Windows 电脑、视频号直播伴侣和 DeepSeek API Key 完成一次内部试播。**

## Windows 下载与启动（推荐）

1. 打开 [Releases 下载页](https://github.com/HarveyWho/video-channels-ai-assistant/releases)。进入最新的测试版本。
2. 在 **Assets** 中下载 **`Live Answer Assistant Windows.zip`**。这是包含运行环境的 Windows x64 程序包。若这个文件尚未出现，表示构建尚未完成，请稍后刷新。
3. 右键压缩包，选择 **全部解压**。不要直接在压缩包里运行，也不要把 EXE 单独从文件夹里拖出来。
4. 进入解压后的 `Live Answer Assistant` 文件夹，双击 **`Live Answer Assistant.exe`**。此方式无需另装 Python。
5. 本程序目前没有代码签名。若 Windows 阻止运行，请核对下载来源和同一 Release 的 `SHA256.txt`，保留安全软件保护。也可以使用下方的源码方式运行。

请完整保留程序旁边的 `_internal` 文件夹，它包含本地 OCR 组件和模型。运行需要连接 DeepSeek 的网络；API 按用量收费。

## 配置 DeepSeek

1. 在 [DeepSeek 开放平台](https://platform.deepseek.com/api_keys)创建自己的 API Key，并确认 API 余额。网页聊天账号不等于已配置 API 调用。
2. 点击助手里的 **设置 DeepSeek**，将密钥粘贴到隐藏输入框。密钥不用发给项目维护者，不要提交到 GitHub 或展示在直播画面中。
3. 填写直播主题和参考资料，例如真实的课程介绍、价格、课表和常见问答。
4. 点击 **测试连接**，确认成功后点击 **应用设置**。连接测试会产生少量 API 用量。

密钥仅在本次运行内存中保留，退出后需要重新输入。程序也支持读取已有的 `DEEPSEEK_API_KEY` 环境变量，不会主动写入系统环境变量。

## 开播前的操作

1. 打开 Windows 视频号直播伴侣，保持评论列表可见，建议调大评论字号。
2. 点击 **选择弹幕区域**。在屏幕快照中拖动鼠标框选评论文字，点 **使用这块区域**。尽量避开标题、礼物、人数和输入框。
3. 把助手和提词窗口移到评论区域之外，再点击 **开始监听**。第一帧已有评论作为基线跳过，请发送一条新问题测试。
4. 点击 **打开提词窗口**，把大字窗口放在靠近摄像头的位置。读完一条后点击 **下一条**；提词窗口有焦点时也支持 **Ctrl + 右方向键**，上一条为 **Ctrl + 左方向键**。
5. 有问题没识别到时，可以在主窗口底部手动补充。点 **暂停**停止监听和后续生成；未完成的问题可以选中后重试。

请检查直播伴侣的预览。如果直播采集整个桌面，提词窗口也可能被观众看到；建议使用摄像头或需要的指定窗口作为直播采集源。

## Windows 第一次测试清单

建议先做内部试播，依次核对：

- **连接**：设置中测试 DeepSeek 成功，手动提问能收到逐字显示的回答。
- **资料**：填写一项虚构测试资料，例如“测试课程每周二上课”，手动询问并检查回答是否依据资料；正式直播前删除测试资料，换成真实信息。
- **弹幕**：开始监听后发送“请问怎么报名？”，确认识别内容、问题队列和回答都出现。
- **去重**：同一个问题保持在屏幕上时，不应连续重复入队；“1.5 小时够吗？”与“15 小时够吗？”应保留为两个问题。
- **提词**：连续发两条不同问题，第一条显示后应保持；点击下一条或使用快捷键切换。
- **暂停与错误**：暂停后不再处理新弹幕；错误密钥应显示提示并停止继续生成。已发出的请求可能仍计费。
- **画面**：直播预览没有采集到密钥、参考资料或不想公开的提词内容。

若发现问题，请在 [Issues](https://github.com/HarveyWho/video-channels-ai-assistant/issues)中提供 Windows 版本、显示缩放、出错步骤和脱敏截图。不要上传 API Key、私人聊天或个人信息。

## 源码下载与启动（备选）

1. 在仓库首页点绿色 **Code → Download ZIP**，或下载 [main 分支源码 ZIP](https://github.com/HarveyWho/video-channels-ai-assistant/archive/refs/heads/main.zip)。Release 里的 **Source code (zip)** 也是源码包，需要 Python。
2. 完整解压到可写入的本地文件夹。
3. 安装官方 [Python 3.13、3.12 或 3.11 的 Windows 64 位版本](https://www.python.org/downloads/windows/)，勾选 **Add python.exe to PATH**，保留 **Tcl/Tk and IDLE**。
4. 双击 **Start.bat**。首次会创建 `.venv` 并下载依赖，可能需要数分钟；默认清华 PyPI 镜像，失败后改用官方 PyPI。
5. 窗口打开后，按上面的流程配置 DeepSeek 和评论区域。

面向 Windows 10/11 x64。本版不承诺支持 Windows ARM64、32 位 Python 或 Python 3.14 及更新版本。如果提示缺少 `VCRUNTIME140` 或原生 DLL，请按[微软官方说明](https://learn.microsoft.com/cpp/windows/latest-supported-vc-redist)安装 x64 Visual C++ Redistributable。

## 工作方式与限制

- 屏幕图像只在本机内存中做 OCR，不保存截图、不上传图像。发送给 DeepSeek 的是提问文字、你填写的主题和参考资料，以及程序提示词。
- 通过可见屏幕读取评论，没有接入视频号官方弹幕 API。评论被遮挡、最小化或滚出屏幕后无法读取；高速弹幕、昵称徽章和复杂换行可能造成漏读、错读或重复。
- 默认每约 1.5 秒识别一次，默认筛选疑问句；可以调整间隔或关闭疑问句筛选。实际响应时间还包含 OCR 和 DeepSeek 生成，不保证固定秒数。
- 最多 8 条待生成或生成中的问题，每次只生成一条。超过上限的评论会跳过并提示，需要时可手动补充。
- 答案以短口语回答为目标。AI 仍可能答错；费用、时间、政策和考试信息请主播核实后表达。程序没有联网检索功能。
- 启动时会跳过已有旧弹幕；相同文字在本次运行内去重，最多保留 3000 条识别缓存。每个问题独立生成，不带入上一题聊天历史。
- 不会向直播间自动发评论，也不会自动语音播报。

更多操作和故障处理见[使用说明](使用说明.md)。数据保存位置见[隐私与数据说明](PRIVACY.md)。

## 开发、自检与打包

```powershell
py -3.13 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m unittest -v tests
.venv\Scripts\python.exe app.py --demo
```

`--demo` 只显示固定示例，不采集屏幕、不调用 DeepSeek。

GitHub Actions 的 **Checks** 在 Windows 上检查 Python 3.11、3.12、3.13。发布 Release 后，**Windows release** 工作流使用 Windows runner 打包，运行本地 OCR 与界面构造自检，再运行打包后 EXE 的相同自检；通过后上传 ZIP 和校验值。自检不调用 DeepSeek，也不读取真实直播弹幕。

手动打包可在 Windows 上安装 `requirements build.txt`，执行 `python package.py`。生成文件位于 `release` 目录。第三方组件和模型保留各自许可证，见 [THIRD PARTY NOTICES.md](THIRD%20PARTY%20NOTICES.md)。

## 验证边界

最初在 Mac 环境通过 14 项核心测试、模拟 HTTP 流式接口测试和深浅背景中文人工样张 OCR 测试。GitHub 上的 Windows 自动构建结果请以 [Actions](https://github.com/HarveyWho/video-channels-ai-assistant/actions)记录为准。自动检查无法代替用户电脑上的显示缩放、多屏、高负载、真实视频号弹幕和真实 DeepSeek 连接测试。

## 开源许可

本项目自行编写的代码采用 [MIT License](LICENSE)，可以使用、修改和分发。项目与微信、视频号、腾讯及 DeepSeek 均无官方隶属关系，也不提供任何官方接口授权。
