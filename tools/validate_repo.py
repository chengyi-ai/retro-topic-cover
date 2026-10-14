#!/usr/bin/env python3
"""仓库不变量检查：Skill 说明、文档里引用的路径、随包字体与许可证、示例素材与来源记录、
脚本语法、“不用 AI 生图、不联网”的红线和标签配置。

只读、只用标准库，不渲染。渲染与抠图的冒烟测试在 tests/ 里。
"""

import json
import py_compile
import re
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_NAME = "retro-topic-cover"
# SKILL.md / README.md 等文档里用反引号或 Markdown 链接引用的仓库内路径，必须真实存在。
PATH_PREFIXES = ("scripts/", "examples/", "assets/", "tools/", "docs/", "tests/")
PATH_PATTERN = re.compile(r"(?:`|\]\()((?:%s)[^`)\s]*)" % "|".join(re.escape(p) for p in PATH_PREFIXES))
DOCS = ("SKILL.md", "README.md", "CLAUDE.md", "docs/agent-workflow.md")
REQUIRED_FILES = (
    *DOCS,
    "LICENSE",
    "requirements.txt",
    "requirements-cutout.txt",
    "assets/NotoSerifSC-Black.ttf",
    "assets/OFL.txt",
    "scripts/render_cover.py",
    "scripts/extract_cutout.py",
    "scripts/render_examples.py",
)
# recipe.json 的键会被 render_examples.py 原样转成 render_cover.py 的 --参数。
RECIPE_KEYS = {"line1", "line2", "accent", "title_y", "focus_x", "focus_y", "width", "height"}
HEX_COLOR = re.compile(r"#[0-9a-fA-F]{6}")
URL = re.compile(r"https?://[^\s)>\]]+")
# 红线：不用生成式图像模型 / AI 抠图服务，Skill 脚本不联网、不需要 API Key。
GENERATIVE_PACKAGES = {
    "anthropic", "diffusers", "google-genai", "google-generativeai", "onnxruntime", "openai",
    "replicate", "rembg", "stability-sdk", "torch", "transformers",
}
FORBIDDEN_IMPORTS = {
    "anthropic", "diffusers", "google.genai", "google.generativeai", "httpx", "onnxruntime", "openai",
    "replicate", "rembg", "requests", "stability_sdk", "torch", "transformers", "urllib.request",
}


def check_skill(errors):
    text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not match:
        errors.append("SKILL.md 缺少 YAML frontmatter")
        return
    meta = dict(line.split(":", 1) for line in match.group(1).splitlines() if ":" in line)
    if meta.get("name", "").strip() != SKILL_NAME:
        errors.append(f"SKILL.md 的 name 必须是 {SKILL_NAME}")
    if len(meta.get("description", "").strip()) < 20:
        errors.append("SKILL.md 的 description 过短或缺失")


def check_referenced_paths(errors):
    for doc in DOCS:
        for raw in PATH_PATTERN.findall((ROOT / doc).read_text(encoding="utf-8")):
            path = raw.split("#", 1)[0].rstrip("/.,，。")
            if any(ch in path for ch in "*{<"):
                continue
            if not (ROOT / path).exists():
                errors.append(f"{doc} 引用的路径不存在：{path}")


def check_fonts(errors):
    assets = ROOT / "assets"
    fonts = sorted(p for p in assets.iterdir() if p.suffix.lower() in {".ttf", ".otf", ".ttc"})
    if not fonts:
        errors.append("assets/ 下没有随包字体")
    for path in fonts:
        if path.read_bytes()[:4] not in {b"\x00\x01\x00\x00", b"OTTO", b"ttcf", b"true"}:
            errors.append(f"不是有效的字体文件：{path.relative_to(ROOT)}")
    if "SIL OPEN FONT LICENSE" not in (assets / "OFL.txt").read_text(encoding="utf-8").upper():
        errors.append("assets/OFL.txt 不是 SIL OFL 许可证全文")


def png_has_alpha(path):
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n" or len(data) < 26:
        return False
    color_type = data[25]
    return color_type in (4, 6) or (color_type in (0, 2, 3) and b"tRNS" in data)


def is_jpeg(path):
    return path.read_bytes()[:3] == b"\xff\xd8\xff"


def ratio(value, low, high):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and low <= value <= high


def check_recipe(folder, errors):
    name = folder.relative_to(ROOT)
    recipe = json.loads((folder / "recipe.json").read_text(encoding="utf-8"))
    unknown = set(recipe) - RECIPE_KEYS
    if unknown:
        errors.append(f"{name}/recipe.json 有 render_cover.py 不认识的键：{', '.join(sorted(unknown))}")
    for key in ("line1", "line2"):
        if not str(recipe.get(key, "")).strip():
            errors.append(f"{name}/recipe.json 缺少 {key}")
    if "accent" in recipe and not HEX_COLOR.fullmatch(str(recipe["accent"])):
        errors.append(f"{name}/recipe.json 的 accent 必须是 #RRGGBB")
    if "title_y" in recipe and not ratio(recipe["title_y"], 0, 0.75):
        errors.append(f"{name}/recipe.json 的 title_y 必须在 0–0.75")


def check_layout(folder, errors):
    """拼贴规则：1–3 个透明人物，各自来自不同素材，不复用背景；返回人物数量。"""
    name = folder.relative_to(ROOT)
    layout = json.loads((folder / "layout.json").read_text(encoding="utf-8"))
    cutouts = layout.get("cutouts") or []
    if not 1 <= len(cutouts) <= 3:
        errors.append(f"{name}/layout.json 的 cutouts 必须是 1–3 个")
    if "shadow_color" in layout and not HEX_COLOR.fullmatch(str(layout["shadow_color"])):
        errors.append(f"{name}/layout.json 的 shadow_color 必须是 #RRGGBB")
    paths = [str(item.get("path", "")) for item in cutouts]
    if len(set(paths)) != len(paths):
        errors.append(f"{name}/layout.json 重复使用了同一张人物素材")
    for item, rel in zip(cutouts, paths):
        path = folder / rel
        if Path(rel).stem == "background":
            errors.append(f"{name}/layout.json 不能把背景图当前景人物：{rel}")
        if not path.is_file():
            errors.append(f"{name}/layout.json 引用的人物不存在：{rel}")
        elif not png_has_alpha(path):
            errors.append(f"人物必须是带透明通道的 PNG：{name}/{rel}")
        if not ratio(item.get("width"), 0.01, 1.5):
            errors.append(f"{name}/layout.json 的 {rel} width 必须是 0.01–1.5 的画布比例")
        for key in ("x", "y"):
            if not ratio(item.get(key), -1, 1.5):
                errors.append(f"{name}/layout.json 的 {rel} {key} 必须是画布比例")
    return len(cutouts)


def check_examples(errors):
    examples = sorted(p for p in (ROOT / "examples").iterdir() if p.is_dir())
    if not examples:
        errors.append("examples/ 下没有示例")
    for folder in examples:
        name = folder.relative_to(ROOT)
        missing = [f for f in ("recipe.json", "background.jpg", "cover.jpg", "SOURCES.md") if not (folder / f).is_file()]
        if missing:
            errors.append(f"示例缺文件：{name}/{', '.join(missing)}")
            continue
        for image in ("background.jpg", "cover.jpg"):
            if not is_jpeg(folder / image):
                errors.append(f"不是 JPEG 文件：{name}/{image}")
        try:
            check_recipe(folder, errors)
            people = check_layout(folder, errors) if (folder / "layout.json").is_file() else 0
        except (json.JSONDecodeError, AttributeError, TypeError) as exc:
            errors.append(f"{name} 的 JSON 无法解析：{exc}")
            continue
        # 背景和每个前景人物都是独立素材，各自要有一条来源链接。
        sources = set(URL.findall((folder / "SOURCES.md").read_text(encoding="utf-8")))
        if len(sources) < 1 + people:
            errors.append(f"{name}/SOURCES.md 只有 {len(sources)} 条来源链接，背景加人物共 {1 + people} 张素材")


def requirement_names(path, seen=None):
    seen = seen or set()
    if path in seen or not path.is_file():
        return set()
    seen.add(path)
    names = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if line.startswith("-r "):
            names |= requirement_names(path.parent / line[3:].strip(), seen)
        elif line:
            names.add(re.split(r"[<>=!~;\[ ]", line, maxsplit=1)[0].strip().lower().replace("_", "-"))
    return names


def check_no_generative(errors):
    for req in sorted(ROOT.glob("requirements*.txt")):
        for name in sorted(requirement_names(req) & GENERATIVE_PACKAGES):
            errors.append(f"{req.name} 引入了生成式 / AI 抠图依赖：{name}")
    import_pattern = re.compile(r"^\s*(?:import|from)\s+([\w.]+)", re.M)
    for path in sorted(ROOT.glob("scripts/*.py")):
        for module in import_pattern.findall(path.read_text(encoding="utf-8")):
            if any(module == bad or module.startswith(bad + ".") for bad in FORBIDDEN_IMPORTS):
                errors.append(f"{path.relative_to(ROOT)} 导入了 {module}：Skill 脚本不联网、不调用生成式模型")


def check_python(errors):
    files = sorted(ROOT.glob("scripts/*.py")) + sorted(ROOT.glob("tools/*.py"))
    files += sorted(ROOT.glob("tests/*.py")) + sorted(ROOT.glob(".github/scripts/*.py"))
    with tempfile.TemporaryDirectory() as tmp:
        for i, path in enumerate(files):
            try:
                py_compile.compile(str(path), cfile=str(Path(tmp) / f"{i}.pyc"), doraise=True)
            except py_compile.PyCompileError as exc:
                errors.append(f"语法错误：{path.relative_to(ROOT)}：{exc.msg.strip()}")


def check_labels(errors):
    labels = json.loads((ROOT / ".github/labels.json").read_text(encoding="utf-8"))
    names = [label["name"] for label in labels]
    if len(names) != len(set(names)):
        errors.append(".github/labels.json 有重名标签")
    for label in labels:
        if not re.fullmatch(r"[0-9a-f]{6}", label.get("color", "")):
            errors.append(f"标签颜色不是 6 位十六进制：{label['name']}")


def validate():
    errors = [f"缺少文件：{name}" for name in REQUIRED_FILES if not (ROOT / name).is_file()]
    if errors:
        return errors
    for check in (
        check_skill,
        check_referenced_paths,
        check_fonts,
        check_examples,
        check_no_generative,
        check_python,
        check_labels,
    ):
        check(errors)
    return errors


def main():
    errors = validate()
    for error in errors:
        print(f"✗ {error}", file=sys.stderr)
    if errors:
        return 1
    print("✓ 仓库检查通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
