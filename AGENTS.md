# Repository Engineering Rules

- Source code, file names, documentation, and commit messages must be in English.
- Explanations to the project owner may be in Portuguese.
- Prefer simple and explicit solutions over clever abstractions.
- Avoid overengineering.
- Do not add functionality before its planned phase.
- Never claim a feature, test result, deployment, or metric that has not actually been verified.
- Run relevant tests and checks before each commit.
- Use Conventional Commits with meaningful scopes.
- Keep commits small and atomic by logical change.
- Never use `git add .`, `git add -A`, or `git commit -am`.
- Stage intended files explicitly by path.
- Review `git diff` and `git diff --staged` before committing.
- Do not amend, squash, rewrite history, or force-push unless explicitly requested.
- Never commit `.env` files, API keys, secrets, local databases, caches, virtual environments, build outputs, or editor files.
- After each commit, report the commit hash, message, files, checks run, and why those files belong together.
