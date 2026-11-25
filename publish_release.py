"""Keep a release private until every offline volume is uploaded and verified."""
import ast
import json
import os
from pathlib import Path
import subprocess
from build_offline import sha256


def gh(*args):
    return subprocess.check_output(["gh", *args], encoding="utf-8").strip()


def main():
    repo, commit = os.environ["GITHUB_REPOSITORY"], os.environ["GITHUB_SHA"]
    if os.environ.get("GITHUB_REF") != "refs/heads/main":
        raise SystemExit("Only main may publish a release")
    head = json.loads(gh("api", "repos/"+repo+"/git/ref/heads/main"))["object"]["sha"]
    if head != commit:
        print("Newer main exists; skip this older build")
        return
    module = ast.parse(Path("app.py").read_text(encoding="utf-8"))
    version = next(ast.literal_eval(n.value) for n in module.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "VERSION" for t in n.targets))
    tag = "v"+version
    existing = subprocess.run(["gh", "release", "view", tag, "--repo", repo, "--json", "isDraft,targetCommitish"], capture_output=True, encoding="utf-8")
    if existing.returncode == 0:
        data = json.loads(existing.stdout)
        if not data["isDraft"] or data["targetCommitish"] != commit:
            raise SystemExit("Version already exists. Bump VERSION; never replace a published package.")
    else:
        gh("release", "create", tag, "--repo", repo, "--target", commit, "--draft", "--prerelease",
           "--title", tag+" · 内置 Qwen3.5 2B + 4B 离线包", "--notes-file", "Release Notes.txt")
    files = sorted(path for path in Path("release").iterdir() if path.is_file())
    gh("release", "upload", tag, *[str(p) for p in files], "--repo", repo, "--clobber")
    release = json.loads(gh("api", "repos/"+repo+"/releases/tags/"+tag))
    assets = {asset["name"]: asset for asset in release["assets"]}
    for path in files:
        asset = assets[path.name]
        if asset["size"] != path.stat().st_size or asset.get("digest") != "sha256:"+sha256(path):
            raise RuntimeError("Published asset digest mismatch: "+path.name)
    gh("release", "edit", tag, "--repo", repo, "--draft=false", "--prerelease")
    print("Verified and published", release["html_url"])


if __name__ == "__main__":
    main()
