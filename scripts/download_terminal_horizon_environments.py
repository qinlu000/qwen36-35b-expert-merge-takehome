#!/usr/bin/env python3
"""Download the fixed environment collection with bounded concurrency and LFS checks."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from pathlib import Path

import requests

from audit_terminal_horizon import SOURCES, fetch


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", type=Path)
    ap.add_argument("--proxy", default="http://127.0.0.1:38080")
    args = ap.parse_args()
    base = args.root / "artifacts/data/candidates/new_terminal_horizon_20261016"
    api = json.load(open(base / "environments_api.json"))
    repo, rev = SOURCES["environments"]
    archives = [x for x in api["siblings"] if x["rfilename"].endswith(".tar.gz")]
    out = base / "environments"
    receipts = out / "download_receipts"
    receipts.mkdir(parents=True, exist_ok=True)
    def download(info):
        session = requests.Session()
        session.proxies = {"http": args.proxy, "https": args.proxy}
        dest = out / Path(info["rfilename"]).name
        result = fetch(session, f"https://huggingface.co/datasets/{repo}/resolve/{rev}/{info['rfilename']}",
                       dest, info["size"], info["lfs"]["sha256"])
        (receipts / (dest.name + ".json")).write_text(json.dumps(result, indent=2) + "\n")
        return result
    completed = []
    with ThreadPoolExecutor(max_workers=2) as pool:
        for future in as_completed([pool.submit(download, info) for info in archives]):
            completed.append(future.result())
            summary = {"repo": repo, "revision": rev, "expected_archives": len(archives),
                       "verified_archives": len(completed), "receipts": completed,
                       "all_verified": len(completed) == len(archives)}
            (out / "downloads_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
            print(json.dumps({"verified_archives": len(completed), "expected_archives": len(archives)}), flush=True)


if __name__ == "__main__": main()
