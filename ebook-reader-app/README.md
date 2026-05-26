# Django EPUB Reader with Uploads

## Features

- Email magic-link sign-in with Supabase
- Upload `.epub` files from the browser
- Django file storage via `MEDIA_ROOT`
- Browser EPUB rendering with `epub.js`
- Continue reading section
- Reading progress saving
- Bookmarks
- Notes
- Theme and font controls

## Local run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py makemigrations
python manage.py migrate
python manage.py runserver
```

## Supabase Auth redirect URLs

Add these in Supabase Auth:
- `http://127.0.0.1:8000/**`
- `http://localhost:8000/**`
- your production Vercel URL

## Notes

- This version uploads EPUB files into Django media storage for local development.
- Django handles uploaded files through `request.FILES` and media storage. [web:88][web:330]
- `epub.js` can render EPUB content in the browser from a served file URL, and browser-side workflows can also use blob or binary sources. [web:317][web:331][web:336]
- For production on Vercel, local filesystem uploads are not persistent, so switch the `epub_file` storage to Supabase Storage or another object store. Signed upload flows are supported by Supabase Storage. [web:325][web:326][web:327]
