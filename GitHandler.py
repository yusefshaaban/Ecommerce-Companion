import subprocess
from pathlib import Path

def sh(args, cwd="."):
    try:
        res = subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        print(f"Error occurred while running command: {e}")
        print(f"Stdout: {e.stdout}")
        print(f"Stderr: {e.stderr}")
        return e
    return res

def in_progress(repo: Path) -> bool:
    try:
        out = sh(["git", "status", "--porcelain", "--branch"], cwd=repo).stdout
    except subprocess.CalledProcessError:
        return True
    markers = ("rebase in progress", "rebase-i", "rebase-m",
               "merge in progress", "cherry-pick in progress", "bisect in progress")
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

def ensure_upstream(repo: Path, branch: str):
    if has_upstream(repo):
        return
    try:
        exists = bool(sh(["git", "ls-remote", "--heads", "origin", branch], cwd=repo).stdout.strip())
        if exists:
            sh(["git", "branch", "--set-upstream-to", f"origin/{branch}", branch], cwd=repo)
    except subprocess.CalledProcessError:
        pass

def rebase_onto_upstream(repo: Path):
    """Fetch + rebase only. No merges."""
    if in_progress(repo):
        raise RuntimeError("Repository has an operation in progress (rebase/merge/etc.). Resolve it first.")

    branch = current_branch(repo) or "main"
    ensure_upstream(repo, branch)

    sh(["git", "fetch", "--prune"], cwd=repo)

    # Stash if dirty, then rebase
    dirty = bool(sh(["git", "status", "--porcelain"], cwd=repo).stdout.strip())
    if dirty:
        sh(["git", "stash", "push", "--include-untracked", "-m", "autostash-before-rebase"], cwd=repo)

    try:
        # Always rebase, never merge
        sh(["git", "rebase", "@{u}"], cwd=repo)
    finally:
        if dirty:
            try:
                sh(["git", "stash", "pop"], cwd=repo)
            except subprocess.CalledProcessError as e:
                print("Stash pop had conflicts; leaving changes to resolve. ",
                      (e.stderr or e.stdout or "").strip())

def self_update(repo_dir: str | Path = "."):
    rebase_onto_upstream(Path(repo_dir).resolve())

def self_push_all(repo_target: str | Path = "."):
    target_path = Path(repo_target).resolve()
    repo_dir = target_path.parent if target_path.is_file() else target_path

    sh(["git", "rev-parse", "--is-inside-work-tree"], cwd=repo_dir)
    repo_root = Path(sh(["git", "rev-parse", "--show-toplevel"], cwd=repo_dir).stdout.strip())

    to_add = str(target_path.relative_to(repo_root)) if target_path.is_file() else "."
    sh(["git", "add", to_add], cwd=repo_root)

    committed = False
    try:
        sh(["git", "commit", "-m", "Auto-commit job lots"], cwd=repo_root)
        committed = True
    except subprocess.CalledProcessError as e:
        msg = (e.stdout or "") + (e.stderr or "")
        if "nothing to commit" in msg.lower() or "your branch is up to date" in msg.lower():
            print("No changes to commit.")
        else:
            raise

    branch = current_branch(repo_root) or "main"
    ensure_upstream(repo_root, branch)

    def push(normal=True, set_up=False, force=False):
        if force:
            return sh(["git", "push", "--force-with-lease", "origin", branch], cwd=repo_root)
        if set_up and not has_upstream(repo_root):
            return sh(["git", "push", "-u", "origin", branch], cwd=repo_root)
        if normal:
            return sh(["git", "push"], cwd=repo_root)

    # 1) Try normal push
    try:
        push(set_up=True)
        print("Pushed successfully.")
        return
    except subprocess.CalledProcessError as e1:
        msg1 = (e1.stdout or "") + (e1.stderr or "")
        # 2) If behind, rebase onto upstream and retry (no merge)
        if any(k in msg1.lower() for k in ("non-fast-forward", "behind", "fetch first")):
            # Use pull --rebase --autostash so we never merge
            sh(["git", "pull", "--rebase", "--autostash"], cwd=repo_root)
            try:
                push()
                print("Pushed successfully after rebase.")
                return
            except subprocess.CalledProcessError as e2:
                print("Normal push still failed after rebase:",
                      ((e2.stderr or e2.stdout or "").strip()))
                # 3) Last resort: push anyway but safely
                try:
                    push(force=True)
                    print("Force-pushed with lease after rebase.")
                    return
                except subprocess.CalledProcessError as e3:
                    raise RuntimeError("Force-with-lease push failed:\n" +
                                       ((e3.stderr or e3.stdout or "").strip()))
        else:
            raise

if __name__ == "__main__":
    # Always rebase-based update; never merge.
    # self_update()
    self_push_all("GitHandler.py")
