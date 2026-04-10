import re
import base64
import gzip
import zlib
import sys
from pathlib import Path
import pyperclip


def extract_k4(xml: str) -> str:
    m = re.search(r"<k>\s*k4\s*</k>\s*<s>(.*?)</s>", xml, re.DOTALL)
    if not m:
        raise ValueError("k4 not found")
    return m.group(1).strip()


def decode_k4(k4: str) -> str:
    k4 += "=" * ((4 - len(k4) % 4) % 4)
    raw = base64.urlsafe_b64decode(k4.encode("ascii"))
    return gzip.decompress(raw).decode("utf-8")


def encode_for_demo(raw: str) -> str:
    # zlib deflate (matches qi.deflate)
    compressed = zlib.compress(raw.encode("utf-8"))

    b64 = base64.b64encode(compressed).decode("ascii")
    return b64.replace("+", "-").replace("/", "_").rstrip("=")


def js_escape(s: str) -> str:
    return (
        s.replace("\\", "\\\\")
         .replace("`", "\\`")
         .replace("${", "\\${")
    )


# ---------------- EXPANDED MODE ----------------
def build_expanded(raw: str, filename: str) -> str:
    raw_js = js_escape(raw)

    return f"""Zi = (orig => function(data) {{
    console.log("[INJECT] expanded mode");

    function encodeLevel(text) {{
        const bytes = new TextEncoder().encode(text);
        const compressed = qi.deflate(bytes);

        let bin = "";
        for (let i = 0; i < compressed.length; i++) {{
            bin += String.fromCharCode(compressed[i]);
        }}

        let b64 = btoa(bin);
        return b64.replace(/\\+/g, '-').replace(/\\//g, '_').replace(/=+$/, '');
    }}

    const raw = `{raw_js}`;
    const encoded = encodeLevel(raw);

    return orig(encoded);
}})(Zi);
const origAddBitmapText = Phaser.GameObjects.GameObjectFactory.prototype.bitmapText;

Phaser.GameObjects.GameObjectFactory.prototype.bitmapText = function(x, y, font, text, size, align) {{
  if (typeof text === "string") {{
    if (text === "Stereo Madness") {{
      text = "{filename}";
    }}
  }}
  return origAddBitmapText.call(this, x, y, font, text, size, align);
}};
"""


# ---------------- CONDENSED MODE ----------------
def build_condensed(raw: str, filename: str) -> str:
    encoded = encode_for_demo(raw)

    return f"""Zi = (orig => function(data) {{
    console.log("[INJECT] condensed mode");
    return orig("{encoded}");
}})(Zi);
const origAddBitmapText = Phaser.GameObjects.GameObjectFactory.prototype.bitmapText;

Phaser.GameObjects.GameObjectFactory.prototype.bitmapText = function(x, y, font, text, size, align) {{
  if (typeof text === "string") {{
    if (text === "Stereo Madness") {{
      text = "{filename}";
    }}
  }}
  return origAddBitmapText.call(this, x, y, font, text, size, align);
}};
"""


# ---------------- MAIN ----------------
def main():
    if len(sys.argv) < 2:
        print("usage: python convert.py file.gmd [expanded|condensed]")
        return

    path = Path(sys.argv[1])
    mode = sys.argv[2] if len(sys.argv) > 2 else "expanded"

    xml = path.read_text(encoding="utf-8", errors="ignore")

    k4 = extract_k4(xml)
    raw = decode_k4(k4)

    if mode == "condensed":
        print(build_condensed(raw, path.stem))
        pyperclip.copy(build_condensed(raw, path.stem))
    else:
        print(build_expanded(raw, path.stem))
        pyperclip.copy(build_expanded(raw, path.stem))


if __name__ == "__main__":
    main()
