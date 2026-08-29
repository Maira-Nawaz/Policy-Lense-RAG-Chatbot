# PolicyLens Frontend

Next.js (App Router) + TypeScript + Tailwind CSS frontend for PolicyLens. Talks to the FastAPI
backend in `api/main.py` over HTTP -- it doesn't embed any of the Python pipeline itself, so the
backend must already be running.

## Setup

1. Install dependencies:

   ```bash
   npm install
   ```

2. Copy the environment example and point it at your running backend:

   ```bash
   cp .env.local.example .env.local
   ```

   `NEXT_PUBLIC_API_BASE_URL` must match wherever the FastAPI backend is actually running --
   `http://localhost:8000` for local dev (matches `uvicorn api.main:app --reload --port 8000` run
   from the project root), or a deployed URL later once the backend is deployed.

   `NEXT_PUBLIC_SUPABASE_URL` / `NEXT_PUBLIC_SUPABASE_ANON_KEY` are the same Supabase project the
   backend uses, for Auth (email/password login). The anon key is meant to be public/embedded in
   frontend code, unlike the backend's service-role key -- the example file already has real
   values filled in for this project.

3. Run the dev server:

   ```bash
   npm run dev
   ```

4. Open http://localhost:3000. You'll be redirected to `/login` -- use `/signup` to create an
   account first if you don't have one.

## Pages

- `/login`, `/signup` -- email/password auth via Supabase Auth. No roles or permission tiers --
  just "logged in as a specific user" vs "not logged in."
- `/` -- chat interface (requires login). Ask a question (with optional jurisdiction/segment
  filters), see the answer with a behavior badge (Answered / Needs clarification / Refused /
  Error) and any cited documents, and give thumbs-up/down feedback. The left sidebar lists your
  own recent questions from `/history`; clicking one brings that past Q&A back into the chat
  panel.
- `/metrics` -- eval run history from `/eval-runs`, as a table with trend arrows against the
  previous run for each metric. Requires login (though the underlying data isn't per-user).

Both `/` and `/metrics` redirect to `/login` if there's no active session, and show a brief
loading state while the session is being checked so the protected content never flashes on
screen first. Every backend call attaches the current session's access token as an
`Authorization: Bearer <token>` header automatically.

Both pages fail gracefully if the backend is unreachable or returns an error -- you'll see an
inline error message rather than a stuck spinner.
