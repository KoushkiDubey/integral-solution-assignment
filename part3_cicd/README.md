# Part 3 — CI/CD and Deployment

## What's here
- `app/main.py` — small sample Flask app (stands in for "the provided
  repo") with a health endpoint and one piece of real business logic
  (`calculate_refund_eta`), kept separate from the route so it's easy to
  unit test.
- `tests/test_main.py` — unit tests + a route test.
- `ruff.toml` — lint config.
- `requirements.txt`
- `.github/workflows/ci-cd.yml` — the actual GitHub Actions pipeline.

> Note: this was built and reasoned about in a sandboxed environment with
> no network/pip access, so the test suite couldn't be executed locally
> here. It's standard Flask + pytest + ruff — running `pip install -r
> requirements.txt && pytest -v && ruff check .` on your machine or in
> GitHub Actions itself will run it for real. Please run this once on your
> machine before recording the video, so you can show it actually passing.

## 1. The CI/CD pipeline

Two jobs in `.github/workflows/ci-cd.yml`:

**`test`** — runs on every push (any branch) and every PR into `main`:
1. Checkout code
2. Set up Python
3. Install deps
4. `ruff check .` (lint)
5. `pytest -v` (tests)

**`deploy-staging`** — runs only when:
- the `test` job passed (`needs: test`), **and**
- the push landed on `main` (`if: github.ref == 'refs/heads/main'`)

So a PR gets tested but never deploys; only a merge to `main` deploys, and
only after tests are green. It also runs a smoke test (`/health` check)
right after deploying, so a broken deploy is caught immediately instead of
discovered later by a user.

## 2. Handling secrets / API keys

Rules I followed here, and would explain in the interview:

- **Never in code, never in the repo, never in the workflow file
  directly.** Every credential in `ci-cd.yml` is referenced via
  `${{ secrets.NAME }}`, pulled from **GitHub Actions Secrets**
  (Repo Settings → Secrets and variables → Actions).
- **Scoped by environment.** The deploy job is tied to a GitHub
  "Environment" called `staging` (`environment: staging` in the workflow).
  This means:
  - Secrets can be attached to that specific environment instead of being
    global to the whole repo — a staging key can't leak into a job that
    doesn't need it.
  - GitHub Environments also support **required reviewers** (manual
    approval before the job runs) and **deployment branch restrictions** —
    worth turning on for a production environment, even if staging doesn't
    need it.
- **Least privilege.** The deploy hook URL / token used here should only
  have permission to deploy to staging — not admin access to the whole
  infrastructure. If using cloud provider credentials (AWS/GCP/etc.)
  instead of a deploy-hook pattern, I'd use short-lived OIDC-based
  credentials (GitHub's OIDC provider → cloud IAM role) instead of a
  long-lived static access key, so there's no static secret to leak at
  all.
- **Never printed.** GitHub Actions automatically masks known secret
  values in logs, but I'd still avoid ever echoing a secret var directly
  (e.g. no `echo $STAGING_DEPLOY_HOOK_URL`) as a habit, since masking isn't
  bulletproof against string manipulation.
- **Rotation.** Secrets should be rotatable without a code change — since
  they're all referenced by name via `secrets.*`, rotating a key is just
  updating the value in GitHub settings, no PR needed.

## 3. Rollback plan — first 5 minutes if a deploy breaks production

**First move, immediately: roll back, don't debug forward.**
The instinct to "quickly fix the bug and redeploy" is the wrong first move
under pressure — it takes longer and risks a second bad deploy while
production is already broken. The first move is always to get back to the
last known-good state, then debug calmly afterward.

Concretely, in the first 5 minutes:

1. **Confirm it's actually the deploy** (30 sec) — check if the incident
   started right at deploy time (correlate the alert timestamp with the
   deploy timestamp). If yes, proceed to rollback immediately; don't
   spend time reading stack traces yet.
2. **Roll back to the previous known-good version** (next ~2-3 min) —
   depending on the deploy mechanism:
   - If deploys are tagged/versioned (e.g. container image tags, or a
     platform with "redeploy previous version" built in) — trigger a
     redeploy of the immediately prior successful build. This is why
     every deploy should be tied to an immutable identifier (commit SHA
     or image digest, like `github.sha` in this workflow) — "previous
     version" needs to be unambiguous.
   - If it's a simple platform-hook style deploy like the one in this
     workflow, re-run the same deploy hook but pointing at the last green
     commit SHA.
   - If a database migration shipped with the deploy, that needs its own
     rollback plan — ideally migrations are written backward-compatible
     (deploy-then-migrate, additive-only changes) specifically so a code
     rollback never depends on also reversing a schema change under
     pressure.
3. **Verify the rollback worked** (last ~1 min) — hit the health endpoint
   / smoke test again, check the error rate/alert clears, confirm with
   whatever monitoring is in place before declaring it resolved.
4. **Communicate** — in parallel with the above (not instead of it), a
   one-line status update to the team/stakeholders: "prod issue detected,
   rolling back to previous version, ETA X min" — so people aren't
   independently investigating the same thing or making it worse.

**After** the rollback, and only after production is stable again: pull
logs from the failed deploy, reproduce in staging, find the actual root
cause, fix it properly, and let it go through the normal CI/CD pipeline
again — not a rushed hotfix straight to prod.
