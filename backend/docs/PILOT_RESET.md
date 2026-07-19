# NeuroCortex Pilot Reset Runbook

Use this checklist before opening a real, ethically approved longitudinal pilot study.

## 1. Purge synthetic test data

The integration scripts (`test_phase2d.py`, `test_phase2e.py`, `test_phase2f.py`) create synthetic participants, datasets, models, predictions, and SHAP explanations. These must not remain in the pilot database.

### Dry-run

```powershell
cd backend
.venv\Scripts\python.exe scripts\purge_test_data.py
```

Review the report:

- `participants_removed`
- `datasets_removed`
- `predictions_removed`
- `models_removed`
- `explanations_removed`
- `artifact_folders_removed`

### Execute purge

```powershell
.venv\Scripts\python.exe scripts\purge_test_data.py --execute
```

The script is idempotent. Running it again after a successful purge should report zero removals.

### What gets removed

- Participants whose `public_id` starts with prefixes in `BLOCK_SYNTHETIC_PREFIXES`
- Datasets whose names start with `SYNTHETIC_DATASET_PREFIX` (default: `phase-2`)
- Related dataset rows, artifacts, models, predictions, explanations, sessions, and module results
- Model artifact folders under `backend/models/<model_id>/`

## 2. Model cleanup verification

After purge:

```sql
SELECT COUNT(*) FROM participants WHERE public_id ILIKE 'MLSEED%'
   OR public_id ILIKE 'MLPRED%'
   OR public_id ILIKE 'MLSHAP%';

SELECT COUNT(*) FROM ml_datasets WHERE name ILIKE 'phase-2%';
SELECT COUNT(*) FROM ml_models;
SELECT COUNT(*) FROM ml_predictions;
SELECT COUNT(*) FROM ml_explanations;
```

All counts should be `0` before recruitment.

Confirm `backend/models/` contains only `.gitkeep` (or real pilot model artifacts after future validated training).

## 3. Artifact cleanup

If orphaned folders remain:

```powershell
Get-ChildItem backend\models -Directory | Remove-Item -Recurse -Force
```

Keep `backend\models/.gitkeep`.

## 4. Database reset (optional full clean slate)

If the database still contains mixed dev data, prefer a fresh managed PostgreSQL instance for pilot:

1. Create a new empty database.
2. Set `DATABASE_URL` to the new database.
3. Run migrations:

```powershell
cd backend
alembic upgrade head
```

4. Do **not** rely on the dev researcher invite seeded in migration `003_researchers.py` for production access.

## 5. Secret rotation checklist

- [ ] Generate a new `JWT_SECRET` (minimum 32 characters).
- [ ] Update backend environment variables on the deployment platform.
- [ ] Rotate PostgreSQL username/password.
- [ ] Remove any local `.env` files from shared machines after copying secrets to the secure store.
- [ ] Rebuild the frontend so no stale API URLs remain in `dist/`.

## 6. Invite rotation checklist

- [ ] Replace the development invite code (`yash gupta`) in the database.
- [ ] Issue single-use researcher invites for approved study staff only.
- [ ] Confirm frontend local-mode bypass is disabled: `VITE_USE_LOCAL_STORE=false`.
- [ ] Confirm researcher login is API-only in pilot/production builds.

## 7. Study mode verification

Set pilot environment variables:

```env
STUDY_MODE=pilot
SHOW_TEST_DATA=false
ALLOW_PARTICIPANT_PREDICTIONS=false
BLOCK_SYNTHETIC_PREFIXES=MLSEED,MLPRED,MLSHAP
SYNTHETIC_DATASET_PREFIX=phase-2
```

Verify:

- Researcher dashboard shows the experimental banner.
- Synthetic participants/datasets/models/predictions do not appear in researcher lists or exports.
- Participant UI uses neutral research language only.
- `GET /v1/research/study-config` returns `filter_synthetic_data=true`.

## 8. Pre-recruitment verification steps

- [ ] Run `scripts/purge_test_data.py --execute` and confirm zero synthetic rows remain.
- [ ] Run `scripts/test_phase3b.py` against the pilot API.
- [ ] Confirm `npm run build` succeeds with production `VITE_API_URL`.
- [ ] Confirm HTTPS is enabled for frontend and backend.
- [ ] Confirm backups and migration deploy steps are documented for ops.
- [ ] Confirm IRB-approved protocol version is recorded outside the application (Phase 3C will add in-app consent tracking).
- [ ] Do **not** run `test_phase2d.py`, `test_phase2e.py`, or `test_phase2f.py` against the pilot database.

## 9. After recruitment begins

- Do not change cognitive module scoring without protocol amendment.
- Treat all ML outputs as experimental until the Phase 3 validation checklist is complete.
- Keep `ALLOW_PARTICIPANT_PREDICTIONS=false` unless IRB explicitly approves participant-facing model output.
