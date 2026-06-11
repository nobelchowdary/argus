# Deployment Runbook

## Prerequisites

- Google Cloud project with billing enabled
- Elastic Cloud Serverless (Search project) deployment
- `gcloud` CLI authenticated
- `uv` and `pnpm` installed

## Environment Setup

```bash
# Clone the repository
git clone https://github.com/YOUR_ORG/argus.git
cd argus

# Copy environment template
cp .env.example .env
```

Edit `.env`:
- `GOOGLE_CLOUD_PROJECT` — your GCP project ID
- `GOOGLE_API_KEY` — Gemini API key from AI Studio or Vertex AI
- `ELASTIC_URL` — your Elastic Cloud deployment URL
- `ELASTIC_API_KEY` — read-only API key scoped to `argus-*`

## Generate & Index Dataset

```bash
# Generate synthetic data
python -m tools.dataset.generate

# Index into Elastic (requires Elastic connection)
python -m tools.dataset.index
```

## Local Development

### Backend
```bash
uv sync
uvicorn argus.server:app --reload --port 8000
```

### Frontend
```bash
cd web
pnpm install
pnpm dev
```

## Cloud Run Deployment

### Backend
```bash
gcloud run deploy argus-orchestrator \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars "ELASTIC_URL=$ELASTIC_URL,ELASTIC_API_KEY=$ELASTIC_API_KEY,GOOGLE_API_KEY=$GOOGLE_API_KEY" \
  --min-instances 1 \
  --max-instances 5
```

### Frontend
```bash
cd web
gcloud run deploy argus-web \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars "BACKEND_URL=https://argus-orchestrator-XXXXX.run.app"
```

## Verify Deployment

1. Visit the frontend URL in incognito
2. Click GC-001 alert
3. Verify investigation runs and produces SAR draft
4. Check the reasoning trace shows Skeptic verification

## Reset Demo

```bash
# Regenerate dataset from seed
python -m tools.dataset.generate

# Re-index
python -m tools.dataset.index

# Clear local case data
rm -rf data/cases data/traces
```
