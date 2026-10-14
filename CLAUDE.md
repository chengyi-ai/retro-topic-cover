# CLAUDE.md

本仓库是 Agent Skill「retro-topic-cover」：用真实照片、历史绘画和人物抠图制作中文复古主题封面（默认 1440×1920 JPG），两行横排标题 + 完整背景 + 1–3 张独立素材的透明人物拼贴。仓库根目录就是 Skill 本体，用户直接 clone 到 Skills 目录使用。

## 目录

- `SKILL.md`：Agent 使用说明（构图判断、操作步骤）；`README.md`：安装、命令行用法、示例与许可。
- `scripts/`：Skill 脚本。
  - `render_cover.py`：渲染封面（Pillow）；`--collage` 读取拼贴 JSON。
  - `extract_cutout.py`：按人工给的多边形用传统 GrabCut 抠图（可选，依赖 `requirements-cutout.txt` 的 numpy / OpenCV）。
  - `render_examples.py`：按 `examples/*/recipe.json`、`layout.json` 重新渲染示例成图（会覆盖 `examples/*/cover.jpg`）。
- `assets/`：随包字体 Noto Serif SC Black 及其 SIL OFL 许可证 `assets/OFL.txt`。
- `examples/`：五个示例，各含背景、透明人物、`recipe.json`、`layout.json`、成图和 `SOURCES.md`（素材来源与许可）。
- `tools/`：维护用脚本（`validate_repo.py` 仓库检查、`submit_feedback.py` 登记反馈），不属于 Skill 流程。
- `tests/`：`unittest` 测试（反馈工作流逻辑、仓库检查、脚本冒烟）。
- `.github/`：CI 与 Agent 工作流，见 `docs/agent-workflow.md`。

## 不可违背的原则

- 不使用 AI 生图、生成式填充或 AI 抠图服务；只用 Pillow 排版和传统图像处理（GrabCut）。Skill 脚本不联网、不需要 API Key。
- 只用公有领域或兼容授权的真实素材，每张素材（背景和每个前景人物）都在 `SOURCES.md` 记录来源链接与许可。
- 背景保留完整；前景人物另取 1–3 张不同素材，不从背景复制，也不重复同一张图。
- 人物与投影裁切在外框内侧，外框最后绘制；渲染器不判断脸部和文字遮挡，成图必须目视检查。

`tools/validate_repo.py` 检查其中能自动检查的部分（示例素材与来源条数、透明 PNG、不引入生成式依赖），代码改动不能放宽这些检查。

## 开发约定

- Python 3.10+，依赖见 `requirements.txt`（Pillow）；抠图和完整测试需要 `requirements-cutout.txt`。
- 提交前必须通过：

  ```bash
  python tools/validate_repo.py
  python -m unittest discover -s tests
  ```

- 行为改动配测试；测试只用仓库自带字体和示例素材，输出写到临时目录，小尺寸渲染，不联网。
- 改默认渲染效果（标题字号与位置、配色、色调遮罩、投影、外框、颗粒、图层顺序）要附改动前后的样张，并用 `python scripts/render_examples.py` 更新示例成图。
- 新增或替换素材、字体必须是公有领域或开放许可，并记录来源与许可证。
- 用户可见变化同步 `SKILL.md`、`README.md`。
- 提交信息使用 `fix:` / `feat:` / `docs:` / `test:` / `ci:` 前缀，简体中文描述。
