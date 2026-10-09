"""The release names none of the people, machines or accounts that built it.

Scanned: every tracked file (every file under the root, local state aside, when there is no git checkout, as in a
`git archive` copy) and, inside it, every member of a .gz, .tar.gz or zip archive (the `.eval` logs, whose members are
zstd-compressed), member names included. This file is left out of the pattern scan, since it spells the shapes.
Rejected, by shape, so that no list of names is stored here:

- home directories: any `/Users/<name>`; a `/home/<name>` of a machine account (`ubuntu`, `ec2-user`, ...) or of a
  name the worlds do not use. The worlds give their seats in-fiction home directories named after the cast, so a
  `/home/<name>` passes only when its name, alone, after one initial (the clinic's desk accounts, `kkirkwood`) or after
  `pa-` (the personal assistant's seats), is a word of the authored world sources (`eval/<env>/scenarios`,
  `eval/<env>/environment`, `eval/_harness`);
- private hosts: tailnet names (`*.ts.net`), cloud instance and cluster hostnames (`instance-<n>`, `ip-a-b-c-d`,
  `*.compute.internal`, `*.c.<project>.internal`, `<cluster>-node<n>`);
- repository URLs other than the public upstreams THIRD_PARTY_NOTICES.md names, and ssh remotes;
- 1Password references and API-key shapes (Anthropic, OpenAI, OpenRouter, Google, Hugging Face, GitHub, AWS, Slack,
  Modal, private key blocks);
- provider organization and request ids (an Anthropic `org: <uuid>` in a rate-limit message, an OpenAI `org-...` id,
  `req_...` ids) and personal e-mail addresses (webmail domains);
- an account's provider rate limits (the figure of a provider's rate-limit message: `rate limit of <n> ... tokens per
  minute (org: ...`, `(TPM): Limit <n>`; the API key world's own simulated limit message passes) and per-call dollar
  costs (a pi session's `usage.cost` other than zeros).

A maintainer can also check for words this file must not spell (the authors' user names, say): set
`MAMUBENCH_SCRUB_WORDS` (comma- or space-separated; never committed) and every word must be absent, as a whole word
in any case, from every file, member and name, this file included. Without the variable that test is skipped.
"""

from __future__ import annotations

import functools
import gzip
import io
import os
import re
import subprocess
import sys
import tarfile
import zipfile
from collections.abc import Iterator
from pathlib import Path

import pytest

if sys.version_info < (3, 14):
    # adds zstd, the `.eval` member compression, to zipfile
    import zipfile_zstd  # noqa: F401  # pyright: ignore[reportMissingTypeStubs, reportUnusedImport]

ROOT = Path(__file__).resolve().parents[1]
THIS = Path(__file__).resolve()
WORDS_VARIABLE = "MAMUBENCH_SCRUB_WORDS"
#: local state a copy without git may hold (the .gitignore's entries)
LOCAL_DIRS = {
    ".git",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    "node_modules",
    "modal_downloads",
}
LOCAL_ROOT_DIRS = {"jobs"}
#: output dirs below the root that a copy without git may hold (analysis/stats.py's)
LOCAL_SUBDIRS = {("analysis", "out")}

_UUID = rb"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
#: ANSI colour codes and line breaks a rich-rendered traceback puts between a label and its value
_GAP = rb"(?:\s|\\n|\\u001b\[[0-9;]*m|\x1b\[[0-9;]*m)*"
IDENTIFIERS = {
    "macOS home path": re.compile(rb"/Users/[A-Za-z]"),
    "Windows home path": re.compile(rb"[A-Za-z]:(?:\\\\|\\)Users(?:\\\\|\\)[A-Za-z]"),
    "tailnet host": re.compile(rb"\.ts\.net\b"),
    "cloud instance host": re.compile(
        rb"\binstance-[0-9]|\bip-\d{1,3}-\d{1,3}-\d{1,3}-\d{1,3}\b|\.compute\.internal\b"
        rb"|\.c\.[a-z][a-z0-9\-]*\.internal\b"
    ),
    "cluster node host": re.compile(rb"\b[a-z][a-z0-9]*-node-?[0-9]+\b"),
    "ssh remote": re.compile(rb"\bgit@[A-Za-z0-9.\-]+:"),
    "1Password reference": re.compile(
        rb"op://|\bop (?:read|run|signin|item) |OP_SERVICE_ACCOUNT_TOKEN|1password",
        re.IGNORECASE,
    ),
    "Anthropic API key": re.compile(rb"\bsk-ant-[A-Za-z0-9_\-]{20,}"),
    "OpenAI or OpenRouter API key": re.compile(
        rb"\bsk-(?:proj-|svcacct-|admin-|or-v1-)?[A-Za-z0-9_\-]{32,}"
    ),
    "Google API key": re.compile(rb"\bAIza[0-9A-Za-z_\-]{35}"),
    "Hugging Face token": re.compile(rb"\bhf_[A-Za-z0-9]{30,}"),
    "GitHub token": re.compile(
        rb"\bgh[pousr]_[A-Za-z0-9]{36,}|\bgithub_pat_[A-Za-z0-9_]{22,}"
    ),
    "AWS access key": re.compile(rb"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    "Slack token": re.compile(rb"\bxox[abprs]-[A-Za-z0-9\-]{10,}"),
    "Modal token": re.compile(rb"\b(?:ak|as)-[A-Za-z0-9]{20,}\b"),
    "private key": re.compile(rb"-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----"),
    "Anthropic org id": re.compile(
        rb"org:" + _GAP + rb"(?!00000000-0000-0000-0000-000000000000)" + _UUID
    ),
    "OpenAI org id": re.compile(rb"\borg-(?!X{6})[A-Za-z0-9]{24}\b"),
    "Anthropic request id": re.compile(rb"\breq_011[A-Za-z0-9]{18,}"),
    "OpenAI request id": re.compile(rb"\breq_[0-9a-f]{32}\b"),
    "provider rate-limit figure": re.compile(
        rb"rate limit of "
        + _GAP
        + rb"\d[\d,]*"
        + _GAP
        + rb"(?:input |output )?tokens per minute \(org"
        rb"|\(TPM\):" + _GAP + rb"Limit" + _GAP + rb"\d"
    ),
    "per-call dollar cost": re.compile(
        rb'"cost":\{"input":(?!0,"output":0,"cacheRead":0,"cacheWrite":0,"total":0\})'
    ),
    "personal e-mail address": re.compile(
        rb"[A-Za-z0-9._%+\-]+@(?:gmail|googlemail|outlook|hotmail|live|yahoo|icloud|proton|protonmail)\.[a-z]{2,3}\b"
    ),
}
#: repositories the release may link: the public upstreams of THIRD_PARTY_NOTICES.md and of the vendored fixture repo
PUBLIC_REPOS = {
    "pallets/jinja",
    "pallets/cachelib",
    "earendil-works/pi",
    "meridianlabs-ai/inspect_petri",
    # linked from the blog post (blog/index.html): this repository and a public CLI it cites
    "safety-research/MAMUBench",
    "doordash-oss/doordash-cli",
}
_REPO_URL = re.compile(
    rb"\b(?:github\.com|gitlab\.com|bitbucket\.org)[/:]([A-Za-z0-9_.\-]+)(?:/([A-Za-z0-9_.\-]+))?"
)
_HOME = re.compile(rb"/home/([A-Za-z0-9_.\-]+)")
MACHINE_ACCOUNTS = {
    b"ubuntu",
    b"ec2-user",
    b"runner",
    b"admin",
    b"root",
    b"user",
    b"jovyan",
    b"vscode",
    b"codespace",
    b"azureuser",
    b"debian",
    b"centos",
    b"opc",
}
_WORLD_DIR = re.compile(r"^eval/(?:[a-z_]+/(?:scenarios|environment)|_harness)/")


def release_files() -> list[Path]:
    """The files a release carries: git's tracked files, or, without a checkout, every file but local state."""
    try:
        listed = subprocess.run(
            ["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        listed = b""
    files = sorted(
        p
        for p in (ROOT / name.decode() for name in listed.split(b"\0") if name)
        if p.is_file()
    )
    if files:
        return files
    out: list[Path] = []
    for path in ROOT.rglob("*"):
        rel = path.relative_to(ROOT).parts
        if (
            not path.is_file()
            or LOCAL_DIRS & set(rel)
            or rel[0] in LOCAL_ROOT_DIRS
            or rel[:2] in LOCAL_SUBDIRS
            or (
                len(rel) > 2
                and rel[0] == "eval"
                and rel[2] in ("runs", "readouts", "results")
            )
            or path.suffix == ".pyc"
            or path.name.endswith(".env")
        ):
            continue
        out.append(path)
    return sorted(out)


def expand(name: str, data: bytes) -> Iterator[tuple[str, bytes]]:
    """(member name, bytes) of a file and, recursively, of every archive member inside it."""
    if data[:4] == b"PK\x03\x04":
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            for info in z.infolist():
                yield f"{name}::{info.filename}", info.filename.encode()
                yield from expand(f"{name}::{info.filename}", z.read(info))
        return
    if data[:2] == b"\x1f\x8b":
        raw = gzip.decompress(data)
        try:
            with tarfile.open(fileobj=io.BytesIO(raw)) as tar:
                for member in tar.getmembers():
                    yield f"{name}::{member.name}", member.name.encode()
                    yield (
                        f"{name}::{member.name}",
                        f"{member.uname} {member.gname}".encode(),
                    )
                    body = tar.extractfile(member) if member.isfile() else None
                    if body is not None:
                        yield from expand(f"{name}::{member.name}", body.read())
            return
        except tarfile.TarError:
            yield from expand(f"{name}::gunzip", raw)
            return
    yield name, data


@functools.cache
def contents() -> tuple[tuple[str, bytes], ...]:
    """(name, bytes) of every release file's path and of everything inside it."""
    out: list[tuple[str, bytes]] = []
    for path in release_files():
        rel = path.relative_to(ROOT).as_posix()
        out.append((rel, rel.encode()))
        out.extend(expand(rel, path.read_bytes()))
    return tuple(out)


@functools.cache
def world_words() -> frozenset[bytes]:
    """Every lower-case word of the authored world sources: the names the worlds give their casts."""
    words: set[bytes] = set()
    for path in release_files():
        rel = path.relative_to(ROOT).as_posix()
        if (
            _WORLD_DIR.match(rel)
            and "/tests/" not in rel
            and path.suffix in (".py", ".json", ".md", ".txt")
        ):
            words |= set(re.findall(rb"[a-z0-9_\-]+", path.read_bytes().lower()))
    return frozenset(words)


def in_world(name: bytes, words: frozenset[bytes]) -> bool:
    return (
        name in words
        or name[1:] in words
        or (name.startswith(b"pa-") and name[3:] in words)
    )


def leaks(data: bytes, words: frozenset[bytes]) -> list[str]:
    found = [label for label, pattern in IDENTIFIERS.items() if pattern.search(data)]
    for m in _REPO_URL.finditer(data):
        org, repo = (
            m.group(1).decode(),
            (m.group(2) or b"").decode().removesuffix(".git"),
        )
        if f"{org}/{repo}" not in PUBLIC_REPOS:
            found.append(f"repository URL {m.group().decode()}")
    for m in _HOME.finditer(data):
        name = m.group(1).lower().rstrip(b".-")
        if name and (name in MACHINE_ACCOUNTS or not in_world(name, words)):
            found.append(f"home directory /home/{name.decode()}")
    return sorted(set(found))


#: shapes the scan must flag, and the placeholders and in-world paths it must pass
LEAKS = (
    b"cwd /Users/someone/project",
    b"C:\\\\Users\\\\someone\\\\project",
    b"ssh gpu-box.tail1234.ts.net",
    b"on instance-7 at ip-10-0-3-17.ec2.internal and worker-3.c.my-project.internal",
    b"slurm gpu-node12",
    b"git remote add origin git@github.com:someone/secret.git",
    b"https://github.com/someone/private-research",
    b"export OP_SERVICE_ACCOUNT_TOKEN; ANTHROPIC_API_KEY=$(op read op://vault/item/key)",
    b"ANTHROPIC_API_KEY=sk-ant-api03-" + b"A" * 40,
    b"OPENROUTER_API_KEY=sk-or-v1-" + b"0" * 64,
    b"hf_" + b"a" * 34 + b" ghp_" + b"b" * 36 + b" AKIA" + b"C" * 16,
    b"(org: 12345678-1234-4321-abcd-0123456789ab, model: m)",
    b"(\\u001b[0m\\u001b[32morg: \\u001b[0m\\n\\u001b[32m12345678-1234-4321-abcd-0123456789ab, model",
    b'"request_id":"req_011ExampleExampleExampl"',
    b"x-request-id: req_0123456789abcdef0123456789abcdef",
    b"org-AbCdEfGhIjKlMnOpQrStUvWx",
    b"mail someone@gmail.com",
    b"exceed your organization's rate limit of 30,000,000 input tokens per minute (org: 0000",
    b"on tokens per min (TPM): Limit 40000000, Used 40000000, Requested 1678.",
    b'"usage":{"input":3,"output":9,"cost":{"input":0.00001,"output":0.0049,"cacheRead":0,"cacheWrite":0,"total":0.0049}}',
    b"cd /home/ubuntu/repo",
    b"cd /home/qzxv/repo",
)
CLEAN = (
    b"(org: 00000000-0000-0000-0000-000000000000, model: m)",
    b'"request_id":"req_redacted"',
    b"org-XXXXXXXXXXXXXXXXXXXXXXXX",
    b"ANTHROPIC_API_KEY=sk-ant-... and /home/pa-<name>/dinner",
    b"see https://github.com/pallets/jinja and https://github.com/earendil-works/pi",
    b"cat /home/pa-darius/notes.md; ls /home/captain; cd /home/asha/distill; ls /home/kkirkwood/desk",
    b"git@github.internal is the world's forge; priya.shah@westford.dev",
    b"exceed your organization's rate limit of N input tokens per minute (org: 0000",
    b"on tokens per min (TPM): Limit N, Used N, Requested N.",
    b"organization's rate limit of 400,000 output tokens per minute. For details",
    b'"cost":{"input":0,"output":0,"cacheRead":0,"cacheWrite":0,"total":0}',
)


def test_the_scan_flags_the_shapes_and_passes_the_placeholders() -> None:
    words = world_words()
    assert {b"captain", b"asha", b"kirkwood", b"darius"} <= words
    assert [s for s in LEAKS if not leaks(s, words)] == []
    assert [s for s in CLEAN if leaks(s, words)] == []


def test_the_release_names_no_person_machine_or_account() -> None:
    words = world_words()
    this = THIS.relative_to(ROOT).as_posix()
    names: list[str] = []
    bad: list[str] = []
    for name, data in contents():
        names.append(name)
        if name.split("::", 1)[0] != this:
            bad += [f"{name}: {what}" for what in leaks(data, words)]
    assert not bad, "\n".join(bad[:20])
    # the scan read the whole tree and inside the archive kinds it carries: a zip's members and a gzip
    assert any(n.startswith("eval/") for n in names) and any(
        n.startswith("analysis/") for n in names
    )
    assert any(".zip::" in n for n in names)
    assert any(n.endswith("::gunzip") for n in names)


def test_the_maintainers_words_appear_nowhere() -> None:
    words = {
        w.lower().encode()
        for w in re.split(r"[\s,]+", os.environ.get(WORDS_VARIABLE, ""))
        if w
    }
    if not words:
        pytest.skip(f"{WORDS_VARIABLE} is not set")
    bad = sorted(
        {
            f"{name}: {word.decode()}"
            for name, data in contents()
            for word in words & set(re.findall(rb"[a-z0-9_]+", data.lower()))
        }
    )
    assert not bad, "\n".join(bad[:20])
