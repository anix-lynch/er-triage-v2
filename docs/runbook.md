# Runbook

Operational reference for ED Triage v2 on Cloud Run. Read this if you're oncall, redeploying, or debugging a live issue.

## Service summary

| Field | Value |
|-------|-------|
| Service name | `er-triage-v2` |
| Region | `us-west1` |
| Project | `maps-platform-20251011-140544` |
| Live URL | https://er-triage-v2-tjb2srbb2q-uw.a.run.app |
| Service account | `835005185815-compute@developer.gserviceaccount.com` |
| Container registry | `us-west1-docker.pkg.dev/<project>/cloud-run-source-deploy/er-triage-v2` |
| Secret | `anthropic-api-key:latest` (mounted as `ANTHROPIC_API_KEY` env var) |
| Scale config | min=0 max=3 · memory 1Gi · cpu 1 · timeout 300s |
| Cold start | ~5s (Streamlit + Chroma load) |

## Common operations

### Tail live logs

```bash
gcloud run services logs read er-triage-v2 --region us-west1 --limit 50
gcloud run services logs tail er-triage-v2 --region us-west1
```

### Inspect current revision

```bash
gcloud run services describe er-triage-v2 --region us-west1
gcloud run services describe er-triage-v2 --region us-west1 \
  --format='value(status.latestReadyRevisionName,status.url)'
```

### Redeploy from local source

```bash
# from repo root
export GCP_PROJECT=maps-platform-20251011-140544
bash deploy/cloudrun.sh
```

This runs `gcloud builds submit` (Cloud Build) → pushes image to Artifact Registry → `gcloud run deploy`.

### Roll back to a previous revision

```bash
gcloud run services update-traffic er-triage-v2 \
  --region us-west1 \
  --to-revisions=er-triage-v2-00003-d5x=100
```

(Replace the revision name with whichever you're rolling back to.)

### Rotate the Anthropic API key

```bash
# new key already in global.env or Secret Manager
echo -n "<new-key>" | gcloud secrets versions add anthropic-api-key --data-file=-

# Cloud Run picks up the new version automatically because the binding
# uses ":latest". To force a refresh, redeploy:
gcloud run services update er-triage-v2 --region us-west1 \
  --update-secrets=ANTHROPIC_API_KEY=anthropic-api-key:latest
```

### Verify a request lands

```bash
curl -s -o /dev/null -w "HTTP %{http_code} · %{time_total}s\n" \
  https://er-triage-v2-tjb2srbb2q-uw.a.run.app/
```

Expected: `HTTP 200 · ~5s` (cold start) or `~1s` (warm).

## Failure modes seen and how to handle them

### Symptom: HTTP 503 from Cloud Run

**Likely cause:** container failing to start. Streamlit needs port 8080; Chroma needs to load `outputs/embeddings/chroma.db/`.

**Diagnose:**
```bash
gcloud run services logs read er-triage-v2 --region us-west1 --limit 100
# look for: "ImportError", "FileNotFoundError chroma.db", "PORT mismatch"
```

**Fix:** rebuild the image (`bash deploy/cloudrun.sh`) — if the chroma.db wasn't committed to the image, the COPY step in Dockerfile picks it up from local. If `outputs/embeddings/chroma.db/` is gitignored locally, run `python scripts/build_index.py` first.

### Symptom: Streamlit loads, but clicking a case shows error

**Likely cause:** assessment JSON missing in `outputs/assessments/`. The deployed app reads pre-generated assessments — if a case ID doesn't have a corresponding JSON, the app errors.

**Diagnose:** check `outputs/assessments/` is populated for ER-0042 through ER-0053.

**Fix:** locally run `python -m app.engine` to regenerate, then redeploy.

### Symptom: triage runs but cites a rule_id that doesn't exist

**Likely cause:** model drift from a new Claude snapshot, OR `inputs/guidelines.md` changed without re-running the engine.

**Diagnose:**
```bash
python scripts/eval.py
# rule_faithfulness_pct should be 100 — if not, inspect which case fabricated
```

**Fix:** regenerate assessments (`python -m app.engine`). If the issue persists, the prompt may need tightening — see `app/prompt.py`.

### Symptom: Firestore writes failing in logs

**Likely cause:** Firestore not reachable, or service account lacks `roles/datastore.user`.

**Diagnose:**
```bash
gcloud projects get-iam-policy maps-platform-20251011-140544 \
  --flatten="bindings[].members" \
  --filter="bindings.members:835005185815-compute@developer.gserviceaccount.com"
```

**Fix:** the service is designed to no-op when Firestore is unavailable (`memory.py` falls back gracefully). User-facing functionality continues. Grant `roles/datastore.user` to restore override persistence.

### Symptom: Vertex AI embedding call failing during build

**Likely cause:** Vertex API not enabled, OR service account lacks `aiplatform.user` role, OR rate-limited.

**Diagnose:**
```bash
gcloud services list --enabled --filter="name:aiplatform.googleapis.com"
```

**Fix:**
```bash
gcloud services enable aiplatform.googleapis.com
gcloud projects add-iam-policy-binding maps-platform-20251011-140544 \
  --member="serviceAccount:835005185815-compute@developer.gserviceaccount.com" \
  --role="roles/aiplatform.user"
```

If rate-limited: build is offline, just retry. The `cache.json` already covers existing cases so re-embedding only happens for new ones.

## Cost monitoring

```bash
# Cloud Run billing for this service
gcloud billing accounts list
# expect: 01BF27-7A90D2-EDD523 (the $900 GCP credit account)

# Recent usage (rough)
gcloud run services describe er-triage-v2 --region us-west1 \
  --format='value(metadata.annotations["run.googleapis.com/cpu-throttling"])'
```

Expected monthly cost at current usage: **$0** (idle most of the time, scale-to-zero, free tier covers light demo traffic).

## Security checklist (per redeploy)

- [ ] `_private/` is in `.gitignore` and the public repo returns 404 on it.
- [ ] No `.env` file ends up in the build context (`.gcloudignore` covers this).
- [ ] Container does not have `ANTHROPIC_API_KEY` baked in — it's mounted from Secret Manager at runtime.
- [ ] Service is `--allow-unauthenticated` only because this is a public demo. Any real PHI deployment requires IAP / auth proxy.
- [ ] gitleaks pre-commit hook stays enabled — never bypass with `--no-verify` on this repo.
