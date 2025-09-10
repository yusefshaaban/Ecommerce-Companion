import subprocess
import sys
from pathlib import Path

def sh(args, cwd="."):
    return subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True)

def self_update(repo_dir: str | Path = "."):
    repo = Path(repo_dir).resolve()

    # Verify git available and in a repo
    sh(["git", "rev-parse", "--is-inside-work-tree"], cwd=repo)

    # Determine current branch (fallback to main)
    try:
        branch = sh(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=repo).stdout.strip()
    except subprocess.CalledProcessError:
        branch = "main"

    # Make sure an upstream exists; set it if missing
    try:
        sh(["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"], cwd=repo)
    except subprocess.CalledProcessError:
        # Assumes origin/<branch> exists
        sh(["git", "branch", "--set-upstream-to", f"origin/{branch}", branch], cwd=repo)

    # Stash local changes (including untracked), pull with rebase, then pop stash (if any)
    had_stash = False
    status = sh(["git", "status", "--porcelain"], cwd=repo).stdout
    if status.strip():
        had_stash = True
        sh(["git", "stash", "push", "--include-untracked", "-m", "autostash-before-start"], cwd=repo)

    try:
        sh(["git", "fetch", "--prune"], cwd=repo)
        # Prefer fast-forward; if not possible, rebase
        try:
            sh(["git", "merge", "--ff-only", "@{u}"], cwd=repo)
        except subprocess.CalledProcessError:
            sh(["git", "rebase", "@{u}"], cwd=repo)
    finally:
        if had_stash:
            # Try to reapply stashed work; if conflicts, keep working tree as-is
            subprocess.run(["git", "stash", "pop"], cwd=repo)

if __name__ == "__main__":
    try:
        self_update(".")
    except FileNotFoundError:
        print("Git not found on PATH. Please contact Anas.")
    except subprocess.CalledProcessError as e:
        print("Self-update failed:", e.stderr or e)
    # start your app after updating
    # main()
