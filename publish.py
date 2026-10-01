"""Build, sign and optionally publish an immutable HuangGuo hot-update release."""
import argparse
import base64
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess
import zipfile
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

ROOT = Path(__file__).resolve().parent
REPOSITORY = "MrSsg/HuangguoAPP-HotUpdates"
EXCLUDED = {"site-default.json", "hot-update-public.pem", "hot-runtime.js", "runtime.js"}
EXTENSIONS = {".html", ".css", ".js", ".svg", ".png", ".jpg", ".jpeg", ".webp", ".gif", ".json", ".woff", ".woff2", ".txt"}

def json_file(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))

def key_path():
    folder = os.environ.get("LOCALAPPDATA")
    return Path(folder) / "HuangGuoSigning" / "hot-update-private.pem" if folder else None

def signed(payload, key):
    data = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return {"payload": base64.b64encode(data).decode(),
            "signature": base64.b64encode(key.sign(data, ec.ECDSA(hashes.SHA256()))).decode()}

def build(args):
    release, site, theme = (json_file(ROOT / name) for name in ("release.json", "site.json", "theme.json"))
    if args.revision is not None:
        release["revision"] = args.revision
    revision = release["revision"]
    if not isinstance(revision, int) or revision < 1 or release["bridgeVersion"] != 1:
        raise ValueError("revision 必须为递增正整数，当前 bridgeVersion 为 1")
    for name in ("startsAt", "endsAt"):
        if theme.get(name):
            date = dt.datetime.fromisoformat(theme[name].replace("Z", "+00:00"))
            if date.tzinfo is None:
                raise ValueError("主题时间必须包含时区")
    if not str(site.get("origin", "")).startswith("https://"):
        raise ValueError("站点必须使用 HTTPS")
    if args.key is None or not args.key.is_file():
        raise FileNotFoundError("缺少本机热更新签名私钥；请通过 --key 指定，勿提交私钥")
    key = serialization.load_pem_private_key(args.key.read_bytes(), password=None)
    public = key.public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
    expected = serialization.load_pem_public_key((ROOT / "public-key.pem").read_bytes()).public_bytes(
        serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
    if public != expected:
        raise ValueError("私钥与应用信任的公钥不匹配")
    tag = "resources-r" + str(revision)
    dist = ROOT / "dist" / tag
    dist.mkdir(parents=True, exist_ok=True)
    archive = dist / (tag + ".zip")
    files = [(ROOT / "site.json", "site.json"), (ROOT / "theme.json", "theme.json")]
    if (ROOT / "theme").is_dir():
        files += [(path, path.relative_to(ROOT).as_posix()) for path in sorted((ROOT / "theme").rglob("*")) if path.is_file()]
    if args.web:
        if not (args.assets / "app.html").is_file():
            raise FileNotFoundError("--assets 必须指向 Android 应用的 assets 目录")
        files += [(path, "ui/" + path.relative_to(args.assets).as_posix())
                  for path in sorted(args.assets.rglob("*")) if path.is_file() and path.name not in EXCLUDED]
    if len(files) > 512 or sum(path.stat().st_size for path, _ in files) > 25 * 1024 * 1024:
        raise ValueError("资源包超出客户端支持的大小或文件数量")
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as output:
        for path, name in files:
            if path.suffix.lower() not in EXTENSIONS:
                raise ValueError("不支持的资源类型：" + name)
            output.writestr(zipfile.ZipInfo(name, (2026, 1, 1, 0, 0, 0)), path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED)
    data = archive.read_bytes()
    if len(data) > 12 * 1024 * 1024:
        raise ValueError("压缩后的资源包不得超过 12 MiB")
    payload = dict(release, schema=1, size=len(data), sha256=hashlib.sha256(data).hexdigest(),
                   url="https://github.com/" + REPOSITORY + "/releases/download/" + tag + "/" + archive.name)
    manifest = dist / "hot-update.json"
    manifest.write_text(json.dumps(signed(payload, key), ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    notes = dist / "notes.md"
    notes.write_text(release.get("notes", "更新站点规则与界面资源") + "\n", encoding="utf-8")
    if args.publish:
        exists = subprocess.run(["gh", "release", "view", tag, "--repo", REPOSITORY], capture_output=True)
        if exists.returncode == 0:
            raise ValueError("该 revision 已发布，请递增版本；已有资源包不可覆盖")
        subprocess.run(["gh", "release", "create", tag, str(archive), str(manifest), "--repo", REPOSITORY,
                        "--title", release["version"], "--notes-file", str(notes), "--latest"], check=True)
    print("资源包：", archive)
    print("签名清单：", manifest)
    return archive, manifest

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--key", type=Path, default=key_path())
    parser.add_argument("--assets", type=Path, default=ROOT.parent / "Android Version" / "app/src/main/assets")
    parser.add_argument("--revision", type=int)
    parser.add_argument("--web", action="store_true", help="包含完整 HTML/CSS/JS 界面包")
    parser.add_argument("--publish", action="store_true", help="发布到 GitHub，签名私钥仅在本机使用")
    build(parser.parse_args())
