"""Validate release metadata before downloading one explicitly approved asset."""
import argparse
import json
import re
import sys
from pathlib import Path

MAX_BYTES = 1024**3
REPOS = {"Neguchads/cdos-nintendods-recomp", "Neguchads/csotn-saturn-recomp", "Neguchads/ccod-xbox-recomp"}


def select_asset(release, tag, filename, expected, repo):
    if repo not in REPOS:
        raise ValueError("Repository not allowlisted")
    if not re.fullmatch(r"v[0-9]+(?:\.[0-9]+){2}", tag):
        raise ValueError("Invalid release tag")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", filename):
        raise ValueError("Expected asset basename")
    if Path(filename).suffix.lower() not in (".exe", ".dll", ".zip", ".7z"):
        raise ValueError("Unsupported artifact extension")
    if not re.fullmatch(r"[a-f0-9]{64}", expected):
        raise ValueError("Expected lowercase SHA-256")
    if release.get("tag_name") != tag or release.get("draft") is not False or release.get("prerelease") is not False:
        raise ValueError("Expected published release")
    matches = [a for a in release["assets"] if a.get("name") == filename]
    if len(matches) != 1:
        raise ValueError("Asset missing or ambiguous")
    asset = matches[0]
    if type(asset.get("size")) is not int or not 0 < asset["size"] <= MAX_BYTES:
        raise ValueError("Artifact exceeds pilot size limit")
    if asset.get("state") != "uploaded":
        raise ValueError("Asset not available")
    # Do not silently fall back if the release service has no recorded digest.
    if asset.get("digest") != "sha256:" + expected:
        raise ValueError("Release metadata digest absent or mismatched")
    if type(asset.get("id")) is not int or asset["id"] <= 0:
        raise ValueError("Invalid asset ID")
    return {"asset_id": asset["id"], "tag": tag, "filename": filename,
            "sha256": expected, "size_bytes": asset["size"], "repository": repo}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("repo", choices=sorted(REPOS))
    p.add_argument("metadata", type=Path)
    p.add_argument("tag")
    p.add_argument("filename")
    p.add_argument("expected_sha256")
    args = p.parse_args()
    try:
        if args.metadata.stat().st_size > 4 * 1024**2:
            raise ValueError("Metadata too large")
        result = select_asset(json.loads(args.metadata.read_text(encoding="utf-8")),
                              args.tag, args.filename, args.expected_sha256, args.repo)
    except (ValueError, OSError, TypeError, KeyError, AttributeError):
        print("Release metadata rejected", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
