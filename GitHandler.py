import subprocess
from pathlib import Path
from typing import Iterable

def sh(args, cwd="."):
    return subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True)

def in_progress(repo: Path) -> bool:
    try:
        out = sh(["git", "status", "--porcelain", "--branch"], cwd=repo).stdout
    except subprocess.CalledProcessError:
        return True
    markers = (
        "rebase in progress", "rebase-i", "rebase-m",
        "merge in progress", "cherry-pick in progress", "bisect in progress"
    )
    return any(m in out.lower() for m in markers)

def current_branch(repo: Path) -> str | None:
    out = sh(["git", "symbolic-ref", "--short", "-q", "HEAD"], cwd=repo).stdout.strip()
    return out or None

def has_upstream(repo: Path) -> bool:
    try:
        sh(["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"], cwd=repo)
        return True
    except subprocess.CalledProcessError:
        return False

def remote_has_branch(repo: Path, remote: str, branch: str) -> bool:
    try:
        out = sh(["git", "ls-remote", "--heads", remote, branch], cwd=repo).stdout.strip()
        return bool(out)
    except subprocess.CalledProcessError:
        return False

def self_update(repo_dir: str | Path = "."):
    repo = Path(repo_dir).resolve()
    sh(["git", "rev-parse", "--is-inside-work-tree"], cwd=repo)

    if in_progress(repo):
        raise RuntimeError("Repository has an operation in progress (merge/rebase/etc.). Resolve it first.")

    branch = current_branch(repo) or "main"

    # Ensure upstream
    if not has_upstream(repo):
        if remote_has_branch(repo, "origin", branch):
            sh(["git", "branch", "--set-upstream-to", f"origin/{branch}", branch], cwd=repo)
        # else leave unset; first push will set it

    # Stash if dirty
    had_stash = False
    if sh(["git", "status", "--porcelain"], cwd=repo).stdout.strip():
        had_stash = True
        sh(["git", "stash", "push", "--include-untracked", "-m", "autostash-before-update"], cwd=repo)

    update_ok = False
    try:
        sh(["git", "fetch", "--prune"], cwd=repo)
        try:
            sh(["git", "merge", "--ff-only", "@{u}"], cwd=repo)
            update_ok = True
        except subprocess.CalledProcessError:
            sh(["git", "rebase", "@{u}"], cwd=repo)
            update_ok = True
    finally:
        # Reapply only if we actually updated cleanly and had stashed changes
        if had_stash and update_ok:
            # Pop once; if conflicts, Git will say so
            subprocess.run(["git", "stash", "pop"], cwd=repo)

def _ensure_iterable_targets(repo_target: str | Path | Iterable[str | Path]) -> list[Path]:
    """
    Normalize targets. Accept:
      - a Path
      - a string path
      - a list/tuple of paths
      - a single string with commas -> split on commas
    """
    if isinstance(repo_target, (str, Path)):
        # If it's a single string, allow "a,b,c" and split on commas
        if isinstance(repo_target, str) and "," in repo_target:
            parts = [p.strip() for p in repo_target.split(",") if p.strip()]
            return [Path(p) for p in parts]
        return [Path(repo_target)]
    else:
        return [Path(p) for p in repo_target]

def self_push_all(repo_target: str | Path | Iterable[str | Path] = "."):
    targets = _ensure_iterable_targets(repo_target)

    # Use the first target to discover the repo root
    first = targets[0].resolve()
    probe_dir = first.parent if first.exists() and first.is_file() else first
    sh(["git", "rev-parse", "--is-inside-work-tree"], cwd=probe_dir)
    repo_root = Path(sh(["git", "rev-parse", "--show-toplevel"], cwd=probe_dir).stdout.strip())

    # Stage all targets (relative to repo root)
    args = ["git", "add"]
    for t in targets:
        t_abs = t.resolve()
        if t_abs.is_file():
            rel = t_abs.relative_to(repo_root)
        else:
            # If it doesn't exist yet or is a directory, add as given (relative or absolute)
            try:
                rel = t_abs.relative_to(repo_root)
            except ValueError:
                # If outside repo, this will fail later; but keep as-is
                rel = t
        args.append(str(rel))
    sh(args, cwd=repo_root)

    committed = False
    try:
        sh(["git", "commit", "-m", "Auto-commit job lots"], cwd=repo_root)
        committed = True
    except subprocess.CalledProcessError as e:
        msg = (e.stdout or "") + (e.stderr or "")
        if "nothing to commit" in msg.lower() or "your branch is up to date" in msg.lower():
            pass  # No changes to commit
        else:
            raise

    if committed:
        branch = current_branch(repo_root) or "main"
        if has_upstream(repo_root):
            try:
                sh(["git", "push"], cwd=repo_root)
            except subprocess.CalledProcessError as e:
                print("Push failed:", e.stderr or e.stdout, "Please contact the developer.")
        else:
            try:
                sh(["git", "push", "-u", "origin", branch], cwd=repo_root)
            except subprocess.CalledProcessError as e:
                print("Push failed:", e.stderr or e.stdout, "Please contact the developer.")

if __name__ == "__main__":
    # Any of these forms now work:
    self_push_all("Operations/all_job_lots.pkl, " \
    "Main.py, " \
    "GitHandler.py, " \
    "EbayJobLotsCreator.py")
    # self_push_all("Main.py")
