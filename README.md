# Emergency Blood Release

Blood bank compatibility tag and emergency issue report tool, with shared history login.

## Login (fixed)

The app needs the API server for sign-in. A default admin is created automatically when the user list is empty:

- **Username:** `admin`
- **Password:** `admin123`

Change this password after first login (Users → Change Password).

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python server.py
```

Open [http://127.0.0.1:43147/](http://127.0.0.1:43147/)

Optional env vars:

- `BLOOD_ADMIN_USER` — seed admin username (default `admin`)
- `BLOOD_ADMIN_PASSWORD` — seed admin password (default `admin123`)
- `BLOOD_DATA_DIR` — where users/history JSON is stored (default `./data`)
- `PORT` — server port (default `43147`)

## Why login failed on the old Vercel site

The live site required login, but:

1. There was no seeded admin user
2. Creating users required an admin session first
3. Local/serverless storage could start empty, so every login returned “Invalid username or password”

This repo seeds an admin on first start so login works.

## Print agent (Windows)

See `README_V69.txt` and `BUILD_PrintAgent.bat` for the Zebra print agent.
