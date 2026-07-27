"""Talk to GitHub: validate repos, clone them, read metadata."""

import asyncio
import shutil
import tempfile
from pathlib import Path

import httpx

API = "https://api.github.com"


class GitHubError(Exception):
    pass


async def get_repo_info(token: str, full_name: str) -> dict:
    """Validate the user can access the repo; return metadata."""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            f"{API}/repos/{full_name}",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
        )
    if resp.status_code == 404:
        raise GitHubError("Repository not found or no access")
    resp.raise_for_status()
    data = resp.json()
    return {
        "full_name": data["full_name"],
        "default_branch": data["default_branch"],
        "size_kb": data["size"],
        "private": data["private"],
    }


async def list_user_repos(token: str) -> list[dict]:
    """Repos the user owns or collaborates on, most recently updated first —
    used to power a picker so users don't have to type an exact owner/repo string."""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            f"{API}/user/repos",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
            params={"sort": "updated", "per_page": 100},
        )
    resp.raise_for_status()
    return [
        {
            "full_name": r["full_name"],
            "private": r["private"],
            "description": r.get("description"),
        }
        for r in resp.json()
    ]


async def get_head_sha(token: str, full_name: str, branch: str) -> str:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            f"{API}/repos/{full_name}/commits/{branch}",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
        )
    resp.raise_for_status()
    return resp.json()["sha"]


async def shallow_clone(token: str, full_name: str, branch: str) -> Path:
    """Clone depth=1 into a temp dir. Caller MUST call cleanup_clone() after."""
    dest = Path(tempfile.mkdtemp(prefix="devpilot_"))
    url = f"https://x-access-token:{token}@github.com/{full_name}.git"
    proc = await asyncio.create_subprocess_exec(
        "git", "clone", "--depth", "1", "--branch", branch, "--single-branch", url, str(dest),
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        shutil.rmtree(dest, ignore_errors=True)
        # NEVER include stderr verbatim in errors saved to DB — it contains the token URL
        raise GitHubError("git clone failed (check repo access and branch name)")
    return dest


def cleanup_clone(path: Path) -> None:
    shutil.rmtree(path, ignore_errors=True)
