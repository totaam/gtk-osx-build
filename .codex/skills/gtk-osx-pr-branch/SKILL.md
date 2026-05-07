---
name: gtk-osx-pr-branch
description: Create and update gtk-osx-build pull-request branches from a prepared source checkout into a fork checkout. Use when Codex needs to switch a gtk-osx-build fork back to master, create a new topic branch, apply one package or grouped package update across all applicable moduleset trees, commit the result, push the branch to origin, force-push after amending, and report the GitHub PR URL.
---

# GTK-OSX PR Branch

## Workflow

Use this skill for contribution branches in a fork such as `$HOME/projects/gtk-osx-build.totaam`, using a prepared source checkout such as `$HOME/projects/gtk-osx-build`.

1. Confirm the package id or ids, target branch name, commit subject, source repo, target repo, and remote.
2. Check the target worktree for tracked-file changes in the modulesets that will be touched.
3. Start from `master` unless the user asks to amend an existing branch.
4. Apply the update to every applicable moduleset tree:
   - `modulesets-stable`
   - `modulesets`
   - `modulesets-unstable`
5. Skip modulesets where the package is absent or intentionally unversioned, for example `<branch/>` Git-tracking modules with no tarball version.
6. Validate all touched XML files.
7. Commit with the requested subject.
8. Push to `origin/<branch>`, or use `--force-with-lease` when amending an already-pushed branch.
9. Report branch name, commit hash, touched files, skipped modulesets, and the PR URL.

## Helper Script

Prefer `scripts/pr_branch_update.py` for mechanical branch creation and XML block copying.

Create a new branch and update a single package everywhere applicable:

```bash
python3 .codex/skills/gtk-osx-pr-branch/scripts/pr_branch_update.py \
  --source $HOME/projects/gtk-osx-build \
  --target $HOME/projects/gtk-osx-build.totaam \
  --branch libpng-1.6.58 \
  --ids libpng \
  --commit-subject "libpng 1.6.58" \
  --push
```

Create a grouped update using multiple ids in one commit:

```bash
python3 .codex/skills/gtk-osx-pr-branch/scripts/pr_branch_update.py \
  --source $HOME/projects/gtk-osx-build \
  --target $HOME/projects/gtk-osx-build.totaam \
  --branch gstreamer-1.28.2 \
  --ids liborc,gstreamer,gst-plugins-base,gst-plugins-good,gst-plugins-ugly,gst-plugins-bad,gst-libav,python3-typing-extensions,gst-python \
  --commit-subject "gstreamer 1.28.2" \
  --push
```

Amend and force-push an existing branch:

```bash
python3 .codex/skills/gtk-osx-pr-branch/scripts/pr_branch_update.py \
  --source $HOME/projects/gtk-osx-build \
  --target $HOME/projects/gtk-osx-build.totaam \
  --branch gstreamer-1.28.2 \
  --ids liborc,gstreamer,gst-plugins-base,gst-plugins-good,gst-plugins-ugly,gst-plugins-bad,gst-libav,python3-typing-extensions,gst-python \
  --commit-subject "gstreamer 1.28.2" \
  --amend \
  --push
```

## Guardrails

- Never include unrelated untracked files in commits.
- Stage only touched moduleset files.
- Do not overwrite target-only patch children by blindly replacing whole files unless the user explicitly asks; copy module blocks by id.
- If the source checkout lacks updated `modulesets` or `modulesets-unstable` copies, use the updated stable module block only when it matches the same package and target moduleset is versioned.
- Treat `<branch/>` or Git branch entries without `version` as not applicable for tarball version updates.
- Use `git push --force-with-lease`, not plain force, when rewriting a pushed branch.
