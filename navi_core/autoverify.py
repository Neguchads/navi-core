"""Opt-in public non-commercial VirusTotal hash lookup; never upload binaries."""
import argparse
import hashlib
import json
import os
import re
import stat
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE = "https://www.virustotal.com/api/v3/files/"
CATEGORIES = ("malicious", "suspicious", "undetected", "harmless",
              "timeout", "confirmed-timeout", "failure", "type-unsupported")
MAX_RESPONSE = 4 * 1024 * 1024
MAX_AGE = 30 * 86400
MAX_FILE = 8 * 1024**3


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def fingerprint(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError("Expected an explicit regular artifact")
    if path.suffix.lower() not in (".exe", ".dll", ".zip", ".7z", ".tar", ".gz", ".elf"):
        raise ValueError("Unsupported release artifact extension")
    with path.open("rb") as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or not 0 < before.st_size <= MAX_FILE:
            raise ValueError("Invalid artifact size or type")
        digest = hashlib.sha256()
        total = 0
        while chunk := stream.read(1024 * 1024):
            total += len(chunk)
            if total > before.st_size:
                raise ValueError("Artifact changed during hashing")
            digest.update(chunk)
        after = os.fstat(stream.fileno())
    if total != before.st_size or (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise ValueError("Artifact changed during hashing")
    return {"sha256": digest.hexdigest(), "size_bytes": total}


def classify(payload, sha, now):
    try:
        obj = payload["data"]
        attrs = obj["attributes"]
        stats = attrs["last_analysis_stats"]
        date = attrs["last_analysis_date"]
        if obj["id"] != sha or obj["type"] != "file" or attrs.get("sha256", sha) != sha:
            return {"status": "integrity-mismatch"}
        if not isinstance(stats, dict) or not {"malicious", "suspicious", "undetected", "harmless"} <= stats.keys():
            raise ValueError
        if any(type(v) is not int or not 0 <= v <= 10000 for v in stats.values()):
            raise ValueError
        if type(date) is not int or not 0 < date <= now + 300:
            raise ValueError
        counts = {k: stats.get(k, 0) for k in CATEGORIES}
        result = {"analysis_epoch": date, "stats": counts,
                  "engines_evaluated": sum(counts[k] for k in CATEGORIES[:4])}
        if counts["malicious"] or counts["suspicious"]:
            result["status"] = "review-required"
        elif now - date > MAX_AGE:
            result["status"] = "stale"
        elif not result["engines_evaluated"] or set(stats) - set(CATEGORIES) or any(counts[k] for k in ("timeout", "confirmed-timeout", "failure")):
            result["status"] = "inconclusive"
        else:
            result["status"] = "no-detections-reported"
        return result
    except (KeyError, TypeError, AttributeError, ValueError):
        return {"status": "invalid-response"}


def lookup(sha, key, opener=None, now=None):
    if not re.fullmatch("[a-f0-9]{64}", sha):
        raise ValueError("Invalid SHA-256")
    if not key or not re.fullmatch(r"[A-Za-z0-9_-]{1,256}", key):
        return {"status": "missing-or-invalid-key"}
    # No redirects or inherited proxy settings; never print a server body or key.
    opener = opener or urllib.request.build_opener(
        urllib.request.ProxyHandler({}), NoRedirect())
    request = urllib.request.Request(BASE + sha, headers={"x-apikey": key,
                                     "Accept": "application/json"}, method="GET")
    try:
        with opener.open(request, timeout=30) as response:
            if response.status != 200:
                return {"status": "http-error"}
            body = response.read(MAX_RESPONSE + 1)
            if len(body) > MAX_RESPONSE:
                return {"status": "invalid-response"}
            return classify(json.loads(body), sha, int(time.time()) if now is None else now)
    except urllib.error.HTTPError as error:
        status = {404: "unknown-hash", 429: "quota-exceeded",
                  401: "auth-error", 403: "auth-error"}.get(error.code, "http-error")
        error.close()
        return {"status": status}
    except (urllib.error.URLError, TimeoutError, OSError):
        return {"status": "network-error"}
    except (ValueError, UnicodeError):
        return {"status": "invalid-response"}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact", type=Path)
    parser.add_argument("--expected-sha256")
    parser.add_argument("--lookup-public-noncommercial", action="store_true",
                        help="Confirm hash is public/non-sensitive and use is non-commercial")
    args = parser.parse_args(argv)
    try:
        result = fingerprint(args.artifact)
    except (OSError, ValueError):
        print(json.dumps({"status": "invalid-artifact"}))
        return 2
    result.update({"schema_version": 1, "checked_epoch": int(time.time()),
                   "source": "virustotal-public-v3", "upload": False,
                   "scope": "Hash report only; not malware-free or provenance certification"})
    if args.expected_sha256 and args.expected_sha256.lower() != result["sha256"]:
        result["status"] = "integrity-mismatch"
    elif not args.lookup_public_noncommercial:
        result["status"] = "local-hash-only"
    else:
        result.update(lookup(result["sha256"], os.environ.get("VT_API_KEY", "")))
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "no-detections-reported" else 2


if __name__ == "__main__":
    sys.exit(main())
