# Git and GitHub working guide

This guide is for your private `bay-area-job-market-analytics` repository. Git tracks history on your Mac; GitHub stores a remote copy online. GitHub Desktop is a visual interface for both. Setting up version control does not authorize Phase 2 or change the project's approval gates.

## The essential terms

| Term | Meaning in this project |
|---|---|
| Repository (repo) | The project folder plus its Git history |
| Working tree | Files currently on your Mac, including edits not yet committed |
| Stage / git add | Choose the exact changes to include in the next saved checkpoint |
| Commit | A named checkpoint saved locally; committing does not upload files |
| Branch | A separate line of work; main is the accepted project version |
| origin | The conventional nickname for this project's GitHub remote |
| Push | Upload local commits to GitHub |
| Fetch | Check what changed on GitHub without changing your working files |
| Pull | Bring remote changes into your local branch; start with a clean working tree |
| Pull request (PR) | A review page proposing to merge a branch into main |
| Clone | Download an existing repository and history to a new local folder |

You already have the local project. Add that folder to GitHub Desktop; do not clone a second copy into it or create another nested repository.

## Publish this existing repository privately with GitHub Desktop

Use these steps only if the GitHub repository has not already been created and linked. First check the project's status and remote; avoid creating a second repository if origin is present.

1. Open GitHub Desktop and make sure the signed-in account is `NaingKaungKhant`.
2. Select **File > Add Local Repository**, choose this existing project folder, then **Add Repository**. The folder is `/Users/nkaungkhant/Desktop/Data_Analytic /bay-area-job-market-analytics`; note the space at the end of `Data_Analytic `.
3. Check **History** for the initial Phase 1 commit. A clean Changes tab after a commit is normal: the files are saved in history.
4. Click **Publish repository**. Set the name to `bay-area-job-market-analytics`, select your personal account, and leave **Keep this code private** checked.
5. Click **Publish Repository**, then **View on GitHub**. Confirm the repository has a Private badge and contains the README, docs and placeholder folders.

A commit must exist before upload. If the remote has already been created through another authorized tool, add the local repo to Desktop and use **Fetch origin** instead of publishing again. GitHub's official guides cover [adding a local repository](https://docs.github.com/en/desktop/adding-and-cloning-repositories/adding-a-repository-from-your-local-computer-to-github-desktop) and [publishing an existing project](https://docs.github.com/en/desktop/adding-and-cloning-repositories/adding-an-existing-project-to-github-using-github-desktop).

## Your everyday workflow in GitHub Desktop

At the start of a session, select this repository, check the current branch, and **Fetch origin**. If remote updates exist and your working tree is clean, use **Pull origin**. Before an approved new task, create a descriptive branch from the updated main branch, such as `docs/clarify-role-rules`.

Edit the intended files. In **Changes**, inspect each diff (the lines added/removed), select only intended changes, write a short meaningful summary such as `docs: clarify role classification rules`, and click **Commit to <branch>**. Then **Publish branch** on its first upload, or **Push origin** for subsequent commits. Commit and push are separate actions.

For a change you want reviewed, create a pull request to main, describe what changed and how it was checked, review the diff and merge only when ready. Then switch back to main and fetch/pull. With a private personal repository you can review your own PR; a PR is useful practice, not a substitute for the project's explicit approval gates.

A good checkpoint covers one coherent improvement. Avoid vague messages such as 'stuff' or 'final final'. You can ask your assistant: 'Show me the diff and explain it before we commit.'

## The same workflow in Terminal

Start in the project folder (quotes preserve its space):

```bash
cd '/Users/nkaungkhant/Desktop/Data_Analytic /bay-area-job-market-analytics'
git status
git remote -v
git log --oneline -5
```

After the remote exists and your working tree is clean, prepare a documentation branch:

```bash
git switch main
git pull --ff-only
git switch -c docs/clarify-role-rules
```

Edit the document, then review and save it. The file here is an example; use the file you actually edited:

```bash
git diff -- docs/business_requirements.md
git add docs/business_requirements.md
git diff --cached
git commit -m "docs: clarify role classification rules"
git push -u origin docs/clarify-role-rules
```

`git diff` shows unstaged changes; `git diff --cached` shows the selected next commit. `-u` sets the branch's upstream, so later pushes on the same branch can use `git push`. A branch name must be new when using `git switch -c`. If pull reports diverging branches or a conflict, stop and inspect; ask for help rather than force-pushing or discarding files.

## What belongs in GitHub

Commit reviewed Markdown, source code, SQL, tests and permitted portfolio assets. `.gitkeep` lets Git preserve otherwise empty folders; it is not data. `.env.example` contains variable names with empty values and is intended to be tracked.

Keep `.env`, tokens, passwords, virtual environments, raw/restricted data, local databases and unreviewed exports out of commits. `.gitignore` is already configured for these. It does not remove files previously committed and does not remove embedded notebook output or workbook data. Private GitHub visibility does not override source terms or make it appropriate to store credentials. Review Tableau workbook extracts and publication rights separately before sharing them.

Use `git status --short --ignored` to see what is ignored. If a secret is ever committed, revoke/rotate it and get help removing it from history; deleting the visible file alone is insufficient.

## Check that your work is saved online

On your branch, `git status -sb` should show a clean working tree and no unpushed commits relative to its upstream. Check `git log --oneline -5` locally and compare with GitHub's commit history. `git remote -v` only shows where uploads would go; it does not prove a push happened. GitHub Desktop's History view shows local commits, and Push origin uploads them.

You do not need to memorize everything. The repeatable cycle is: check updates, branch, edit, review, commit, push, and review/merge when ready.
