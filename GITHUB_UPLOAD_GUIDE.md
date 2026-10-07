# Uploading updates to GitHub

This project deliberately does **not** upload local virtual environments, temporary uploads, generated output, input photos, or `api.txt`. The last item contains an API key and must remain private. If that key has been exposed outside this computer, revoke and replace it before using the project again.

## First-time setup

1. Sign in at [GitHub](https://github.com) and create a new empty repository. Do not add a README, `.gitignore`, or license during repository creation.
2. Copy the repository HTTPS address, which looks like `https://github.com/YOUR-ACCOUNT/YOUR-REPOSITORY.git`.
3. In PowerShell, open this project folder and run:

```powershell
git remote add origin https://github.com/YOUR-ACCOUNT/YOUR-REPOSITORY.git
git branch -M main
git push -u origin main
```

GitHub may open a browser window so that you can sign in and approve the upload.

## Upload later changes

From the project folder, run:

```powershell
git status
git add .
git commit -m "Describe your change"
git push
```

Before `git add .`, always check `git status` and make sure you are not adding passwords, API keys, customer photos, or generated private output. If you need to store configuration, create a safe `.env.example` file with placeholder values instead of uploading the real `.env` file.

## Check the connected GitHub repository

```powershell
git remote -v
```

## If the remote already has files

If `git push` says that the GitHub repository has changes you do not have locally, first run:

```powershell
git pull --rebase origin main
git push
```

Resolve any reported conflicts before pushing again. Do not use force-push unless you fully understand that it can overwrite remote history.
