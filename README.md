# DailyBread

DailyBread runs as a local FastAPI/Uvicorn web app plus a Discord.py bot. Production access is intended to be exposed through a Cloudflare Tunnel.

## Local Startup

1. Create a `.env` file in the project root.
2. Install Python dependencies:

```powershell
pip install -r requirements.txt
```

3. Start the combined web and bot process:

```powershell
python main.py
```

The web app listens on `PORT` or `8000` by default.

## Cloudflare Tunnel

Point your Cloudflare Tunnel at the local Uvicorn server, for example `http://localhost:8000`.

Set either:

```env
DISCORD_REDIRECT_URI=https://your-tunnel-hostname.example.com/callback
```

or:

```env
PUBLIC_BASE_URL=https://your-tunnel-hostname.example.com
```

Then add the same callback URL to the Discord application OAuth2 redirect list.

## Required Environment

```env
DISCORD_CLIENT_ID=
DISCORD_CLIENT_SECRET=
DISCORD_TOKEN=
SESSION_SECRET=
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
API_BIBLE_KEY=
```

Optional Bible translation override:

```env
API_BIBLE_ID=de4e12af7f28f599-02
```

## Supabase Schema Note

Run [docs/supabase_embed_fields.sql](docs/supabase_embed_fields.sql) once to persist Discord message content and embed image URLs.
