import subprocess
from pathlib import Path

def sh(args, cwd="."):
    return subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True)

def in_progress(repo: Path) -> bool:
    # Detect ongoing rebase/merge/cherry-pick
    try:
        out = sh(["git", "status", "--porcelain", "--branch"], cwd=repo).stdout
    except subprocess.CalledProcessError:
        return True
    markers = ( "rebase in progress", "rebase-i", "rebase-m", "merge in progress",
                "cherry-pick in progress", "bisect in progress" )
    return any(m in out.lower() for m in markers)

def current_branch(repo: Path) -> str | None:
    # None if detached
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
        # else: leave unset; first push will set it.

    # Stash if dirty
    had_stash = False
    if sh(["git", "status", "--porcelain"], cwd=repo).stdout.strip():
        had_stash = True
        sh(["git", "stash", "push", "--include-untracked", "-m", "autostash-before-update"], cwd=repo)

    update_ok = False
    try:
        protected = [".env"]
        sh(["git", "fetch", "--prune"], cwd=repo)
        try:
            sh(["git", "merge", "--ff-only", "@{u}"], cwd=repo)
            update_ok = True
        except subprocess.CalledProcessError:
            sh(["git", "rebase", "@{u}"], cwd=repo)
            update_ok = True
            sh(["git", "stash", "pop", protected], cwd=repo) if had_stash else None
    finally:
        if had_stash and update_ok:
            # Reapply only if we actually updated cleanly
            subprocess.run(["git", "stash", "pop"], cwd=repo)

def self_push_all(repo_target: str | Path = "."):
    target_path = Path(repo_target).resolve()
    repo_dir = target_path.parent if target_path.is_file() else target_path

    sh(["git", "rev-parse", "--is-inside-work-tree"], cwd=repo_dir)
    repo_root = Path(sh(["git", "rev-parse", "--show-toplevel"], cwd=repo_dir).stdout.strip())

    to_add = str(target_path.relative_to(repo_root)) if target_path.is_file() else "."
    sh(["git", "add", to_add], cwd=repo_root)

# test
    committed = False
    try:
        sh(["git", "commit", "-m", '\"Auto-commit job lots\"'], cwd=repo_root)
        committed = True
    except subprocess.CalledProcessError as e:
        if "nothing to commit" in (e.stdout + e.stderr).lower() or "your branch is up to date" in (e.stdout + e.stderr).lower():
            print("No changes to commit.")
        else:
            raise

    if committed:
        # Ensure there is an upstream; if not, set it on first push
        branch = current_branch(repo_root) or "main"
        if has_upstream(repo_root):
            try:
                sh(["git", "push"], cwd=repo_root)
                print("Pushed successfully.")
            except subprocess.CalledProcessError as e:
                print("Push failed:", e.stderr or e.stdout)
        else:
            try:
                sh(["git", "push", "-u", "origin", branch], cwd=repo_root)
                print("Pushed successfully (set upstream).")
            except subprocess.CalledProcessError as e:
                print("Push failed:", e.stderr or e.stdout)

if __name__ == "__main__":
    # self_update()
    self_push_all("GitHandler.py")
