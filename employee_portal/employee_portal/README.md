# 🎯 Hunter Portal

Employee Performance & Management System

## Deploy to Streamlit Cloud (Free)

### Step 1 — Supabase (Free Database)
1. Go to [supabase.com](https://supabase.com) → Sign up with GitHub
2. Click **New Project** → give it a name and password
3. Go to **Settings → Database → Connection String → URI**
4. Copy the URL (looks like `postgresql://postgres:PASSWORD@db.xxx.supabase.co:5432/postgres`)

### Step 2 — GitHub
```bash
git init
git add .
git commit -m "Hunter Portal"
```
Create a new repo on GitHub, then:
```bash
git remote add origin https://github.com/YOUR_USERNAME/hunter-portal.git
git push -u origin main
```

### Step 3 — Streamlit Cloud
1. Go to [share.streamlit.io](https://share.streamlit.io) → Sign in with GitHub
2. Click **New app** → select your repo → set main file: `app.py`
3. Click **Advanced settings → Secrets** and paste:
```toml
[database]
url = "postgresql://postgres:YOUR_PASSWORD@db.XXXX.supabase.co:5432/postgres"
```
4. Click **Deploy** — done! 🎉

## Local Development

```bash
pip install -r requirements.txt

# Fill in your Supabase URL in .streamlit/secrets.toml
# OR run without it — app auto-falls back to local SQLite

streamlit run app.py
```

## Demo Accounts

| Username | Password | Role     |
|----------|----------|----------|
| admin    | admin123 | Admin    |
| leader   | lead123  | Leader   |
| john     | john123  | Employee |
| sara     | sara123  | Employee |
