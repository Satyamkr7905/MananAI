# Code sandbox routes — proxy to Piston for safe sandboxed execution.
#
# We never run user code in our own process. Instead we forward `language`
# + `source` to the public Piston API (https://github.com/engineer-man/piston),
# which executes the snippet inside its own ephemeral container and returns
# stdout / stderr / exit code. Auth is required so anonymous traffic can't
# burn through the upstream rate limit.

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from .deps import get_current_user
from .models import User

log = logging.getLogger(__name__)

router = APIRouter(tags=["sandbox"])

_PISTON_EXECUTE = "https://emkc.org/api/v2/piston/execute"
_PISTON_TIMEOUT_SECONDS = 25

# Curated language list — id, label, Piston runtime, default file extension,
# and a starter template the editor pre-fills so users can run something
# immediately. Versions match what the public Piston instance ships.
_LANGUAGES: list[dict] = [
    {
        "id": "python",
        "label": "Python 3",
        "piston": "python",
        "version": "3.10.0",
        "filename": "main.py",
        "starter": (
            "def solve():\n"
            "    # write your solution here\n"
            "    pass\n\n"
            "\n"
            "if __name__ == \"__main__\":\n"
            "    solve()\n"
        ),
    },
    {
        "id": "javascript",
        "label": "JavaScript (Node)",
        "piston": "javascript",
        "version": "18.15.0",
        "filename": "main.js",
        "starter": (
            "function solve() {\n"
            "  // write your solution here\n"
            "}\n\n"
            "solve();\n"
        ),
    },
    {
        "id": "typescript",
        "label": "TypeScript",
        "piston": "typescript",
        "version": "5.0.3",
        "filename": "main.ts",
        "starter": (
            "function solve(): void {\n"
            "  // write your solution here\n"
            "}\n\n"
            "solve();\n"
        ),
    },
    {
        "id": "java",
        "label": "Java",
        "piston": "java",
        "version": "15.0.2",
        "filename": "Main.java",
        "starter": (
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        // write your solution here\n"
            "    }\n"
            "}\n"
        ),
    },
    {
        "id": "cpp",
        "label": "C++",
        "piston": "c++",
        "version": "10.2.0",
        "filename": "main.cpp",
        "starter": (
            "#include <bits/stdc++.h>\n"
            "using namespace std;\n\n"
            "int main() {\n"
            "    // write your solution here\n"
            "    return 0;\n"
            "}\n"
        ),
    },
    {
        "id": "c",
        "label": "C",
        "piston": "c",
        "version": "10.2.0",
        "filename": "main.c",
        "starter": (
            "#include <stdio.h>\n\n"
            "int main(void) {\n"
            "    /* write your solution here */\n"
            "    return 0;\n"
            "}\n"
        ),
    },
    {
        "id": "go",
        "label": "Go",
        "piston": "go",
        "version": "1.16.2",
        "filename": "main.go",
        "starter": (
            "package main\n\n"
            "import \"fmt\"\n\n"
            "func main() {\n"
            "    _ = fmt.Sprint\n"
            "    // write your solution here\n"
            "}\n"
        ),
    },
    {
        "id": "rust",
        "label": "Rust",
        "piston": "rust",
        "version": "1.68.2",
        "filename": "main.rs",
        "starter": (
            "fn main() {\n"
            "    // write your solution here\n"
            "}\n"
        ),
    },
]

_LANG_BY_ID = {lang["id"]: lang for lang in _LANGUAGES}


class RunBody(BaseModel):
    language: str = Field(min_length=1, max_length=32)
    source: str = Field(max_length=200_000)
    stdin: str | None = Field(default=None, max_length=20_000)


def _public_lang(lang: dict) -> dict:
    # Drop the upstream-only "piston" field — the frontend doesn't need it.
    return {k: v for k, v in lang.items() if k != "piston"}


@router.get("/sandbox/languages")
def sandbox_languages(_user: User = Depends(get_current_user)):
    return {"languages": [_public_lang(lang) for lang in _LANGUAGES]}


@router.post("/sandbox/run")
def sandbox_run(body: RunBody, _user: User = Depends(get_current_user)):
    lang = _LANG_BY_ID.get(body.language.strip().lower())
    if lang is None:
        raise HTTPException(status_code=400, detail=f"Unsupported language: {body.language}")

    if not body.source.strip():
        raise HTTPException(status_code=400, detail="Empty source — write some code first.")

    payload = {
        "language": lang["piston"],
        "version": lang["version"],
        "files": [{"name": lang["filename"], "content": body.source}],
        "stdin": body.stdin or "",
        # gentle limits so a runaway loop cannot tie up the upstream worker.
        "compile_timeout": 10_000,
        "run_timeout": 10_000,
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        _PISTON_EXECUTE,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=_PISTON_TIMEOUT_SECONDS) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            result = json.loads(raw or "{}")
    except urllib.error.HTTPError as exc:
        log.warning("Piston returned %s: %s", exc.code, exc.reason)
        raise HTTPException(
            status_code=502,
            detail="Code execution service rejected the request. Try again in a moment.",
        ) from exc
    except urllib.error.URLError as exc:
        log.warning("Piston unreachable: %s", exc.reason)
        raise HTTPException(
            status_code=503,
            detail="Code execution service is unreachable right now. Please try again shortly.",
        ) from exc
    except (json.JSONDecodeError, TimeoutError) as exc:
        log.exception("Piston produced an unreadable response")
        raise HTTPException(
            status_code=502,
            detail="Code execution service returned an unexpected response.",
        ) from exc

    run = result.get("run") or {}
    compile_ = result.get("compile") or {}

    # Merge compile + run into one normalized shape so the UI can render it
    # without caring whether the language has a separate compile phase.
    return {
        "language": lang["id"],
        "version": result.get("version") or lang["version"],
        "stdout": run.get("stdout", ""),
        "stderr": run.get("stderr", ""),
        "exitCode": run.get("code"),
        "signal": run.get("signal"),
        "compileStdout": compile_.get("stdout", ""),
        "compileStderr": compile_.get("stderr", ""),
        "compileExitCode": compile_.get("code"),
    }
