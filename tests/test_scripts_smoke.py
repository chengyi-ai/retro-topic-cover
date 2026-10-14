"""脚本冒烟测试：用随包字体和示例素材小尺寸渲染，不联网、不写入 examples/。"""

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HAS_PILLOW = importlib.util.find_spec("PIL") is not None
HAS_OPENCV = HAS_PILLOW and importlib.util.find_spec("cv2") is not None and importlib.util.find_spec("numpy") is not None


def run(*args):
    return subprocess.run([sys.executable, *map(str, args)], cwd=ROOT, text=True, capture_output=True)


@unittest.skipUnless(HAS_PILLOW, "需要 Pillow：pip install -r requirements.txt")
class RenderCoverTests(unittest.TestCase):
    script = ROOT / "scripts/render_cover.py"

    def test_help(self):
        result = run(self.script, "--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--collage", result.stdout)

    def test_renders_collage_at_requested_size(self):
        from PIL import Image

        example = ROOT / "examples/beethoven"
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "cover.jpg"
            result = run(
                self.script,
                "--main", example / "background.jpg",
                "--line1", "贝多芬：",
                "--line2", "失聪后如何作曲",
                "--collage", example / "layout.json",
                "--width", 360,
                "--height", 480,
                "--output", output,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            with Image.open(output) as image:
                self.assertEqual((image.format, image.size), ("JPEG", (360, 480)))

    def test_rejects_opaque_cutout(self):
        from PIL import Image

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            Image.new("RGB", (40, 60), "white").save(tmp / "opaque.png")
            (tmp / "layout.json").write_text(
                json.dumps({"cutouts": [{"path": "opaque.png", "width": 0.3, "x": 0.1, "y": 0.6}]}),
                encoding="utf-8",
            )
            result = run(
                self.script,
                "--main", ROOT / "examples/vangogh/background.jpg",
                "--line1", "梵高：",
                "--line2", "他眼中的世界",
                "--collage", tmp / "layout.json",
                "--width", 320,
                "--height", 400,
                "--output", tmp / "cover.jpg",
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("transparency", result.stderr)
            self.assertFalse((tmp / "cover.jpg").exists())


class RenderExamplesTests(unittest.TestCase):
    def test_help(self):
        result = run(ROOT / "scripts/render_examples.py", "--help")
        self.assertEqual(result.returncode, 0, result.stderr)


@unittest.skipUnless(HAS_OPENCV, "需要 OpenCV：pip install -r requirements-cutout.txt")
class ExtractCutoutTests(unittest.TestCase):
    def test_polygon_cutout_is_transparent_png(self):
        from PIL import Image, ImageDraw

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            source = Image.new("RGB", (160, 200), (40, 90, 160))
            ImageDraw.Draw(source).ellipse((40, 30, 120, 170), fill=(230, 200, 160))
            source.save(tmp / "portrait.jpg")
            (tmp / "polygon.json").write_text(json.dumps([[30, 20], [130, 20], [130, 180], [30, 180]]))
            result = run(
                ROOT / "scripts/extract_cutout.py",
                "--input", tmp / "portrait.jpg",
                "--polygon", tmp / "polygon.json",
                "--band", 12,
                "--output", tmp / "person.png",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            with Image.open(tmp / "person.png") as cutout:
                self.assertEqual(cutout.mode, "RGBA")
                low, high = cutout.getchannel("A").getextrema()
            self.assertEqual((low, high), (0, 255))

    def test_rejects_non_png_output(self):
        result = run(
            ROOT / "scripts/extract_cutout.py",
            "--input", "missing.jpg",
            "--polygon", "missing.json",
            "--output", "person.jpg",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(".png", result.stderr)


if __name__ == "__main__":
    unittest.main()
