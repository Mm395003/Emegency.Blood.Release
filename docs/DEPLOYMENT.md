# Deployment & Rollback

## Local run

```bash
pip install -r requirements.txt
PORT=43147 python3 -m uvicorn server:app --host 127.0.0.1 --port 43147
```

Open http://127.0.0.1:43147/

Default seeded admin (change immediately): `admin` / `admin123`

Recommended env:

- `BLOOD_TOKEN_SECRET` — strong random secret
- `BLOOD_ADMIN_PASSWORD` — initial admin password
- `BLOOD_DATA_DIR` — durable path for JSON stores

## Vercel / hosted

Redeploy from GitHub `main`. Set `BLOOD_TOKEN_SECRET` in project env.  
JSON file storage may reset on serverless instances — do not treat as durable production EHR storage without architecture approval.

## Print Agent (Windows)

1. Run `BUILD_PrintAgent.bat`
2. Run `START_PrintAgent.bat`
3. Confirm agent URL/port in the app Printer Connection card (source defaults and UI URL may differ by version; verify `/status`)

## Rollback

1. Revert GitHub `main` to previous commit
2. Redeploy hosting
3. Keep local `data/` backups if present

## Production approval gate

Do not change clinical compatibility rules or migrate production patient data without explicit approval.
