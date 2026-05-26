from __future__ import annotations

import html
import tempfile
from pathlib import Path
from zipfile import ZipFile
import xml.etree.ElementTree as ET

from bs4 import BeautifulSoup
from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
BOOKS_DIR = DATA_DIR / "books"
BOOKS_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="FastAPI EPUB Reader")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

NS = {
    "opf": "http://www.idpf.org/2007/opf",
    "dc": "http://purl.org/dc/elements/1.1/",
    "container": "urn:oasis:names:tc:opendocument:xmlns:container",
    "xhtml": "http://www.w3.org/1999/xhtml",
}


def safe_slug(name: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "-" for ch in name).strip("-") or "book"


def find_opf(zf: ZipFile) -> str:
    container_xml = ET.fromstring(zf.read("META-INF/container.xml"))
    rootfile = container_xml.find("container:rootfiles/container:rootfile", NS)
    if rootfile is None:
        raise HTTPException(status_code=400, detail="Invalid EPUB: OPF file not found")
    return rootfile.attrib["full-path"]


def parse_book(epub_path: Path) -> dict:
    with ZipFile(epub_path) as zf:
        opf_path = find_opf(zf)
        opf_dir = Path(opf_path).parent
        opf_root = ET.fromstring(zf.read(opf_path))

        metadata = opf_root.find("opf:metadata", NS)
        manifest = opf_root.find("opf:manifest", NS)
        spine = opf_root.find("opf:spine", NS)
        if manifest is None or spine is None:
            raise HTTPException(status_code=400, detail="Invalid EPUB: missing manifest or spine")

        title = metadata.findtext("dc:title", default=epub_path.stem, namespaces=NS) if metadata is not None else epub_path.stem
        creator = metadata.findtext("dc:creator", default="Unknown author", namespaces=NS) if metadata is not None else "Unknown author"

        manifest_items = {}
        toc_path = None
        for item in manifest.findall("opf:item", NS):
            manifest_items[item.attrib["id"]] = item.attrib
            media_type = item.attrib.get("media-type", "")
            if media_type in {"application/x-dtbncx+xml", "application/xhtml+xml"} and item.attrib.get("properties") == "nav":
                toc_path = str((opf_dir / item.attrib["href"]).as_posix())
            if item.attrib.get("id") == spine.attrib.get("toc"):
                toc_path = str((opf_dir / item.attrib["href"]).as_posix())

        spine_items = []
        for itemref in spine.findall("opf:itemref", NS):
            item = manifest_items.get(itemref.attrib["idref"])
            if item:
                chapter_path = str((opf_dir / item["href"]).as_posix())
                spine_items.append({
                    "id": itemref.attrib["idref"],
                    "href": chapter_path,
                    "label": Path(item["href"]).stem.replace("_", " ").title(),
                })

        toc_labels = load_toc_labels(zf, toc_path) if toc_path else {}
        for chapter in spine_items:
            chapter["label"] = toc_labels.get(chapter["href"], chapter["label"])

        return {
            "title": title,
            "author": creator,
            "chapters": spine_items,
        }


def load_toc_labels(zf: ZipFile, toc_path: str) -> dict[str, str]:
    labels: dict[str, str] = {}
    if toc_path.endswith(".ncx"):
        root = ET.fromstring(zf.read(toc_path))
        for nav_point in root.findall(".//{*}navPoint"):
            src = nav_point.find(".//{*}content")
            text = nav_point.find(".//{*}text")
            if src is not None and text is not None:
                labels[src.attrib.get("src", "").split("#")[0]] = text.text or "Chapter"
    else:
        soup = BeautifulSoup(zf.read(toc_path), "html.parser")
        for link in soup.select("nav a[href]"):
            labels[link["href"].split("#")[0]] = link.get_text(" ", strip=True)
    return labels


def chapter_html(epub_path: Path, href: str) -> str:
    with ZipFile(epub_path) as zf:
        try:
            raw = zf.read(href)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Chapter not found") from exc
        soup = BeautifulSoup(raw, "html.parser")
        body = soup.find("body")
        if body is None:
            return "<p>No readable content found.</p>"
        for tag in body.find_all(["script", "style"]):
            tag.decompose()
        for img in body.find_all("img"):
            alt = html.escape(img.get("alt", "Illustration omitted"))
            img.replace_with(BeautifulSoup(f'<p class="image-note">[{alt}]</p>', "html.parser"))
        return "".join(str(node) for node in body.contents)


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    books = []
    for book_dir in sorted(BOOKS_DIR.iterdir() if BOOKS_DIR.exists() else [], key=lambda p: p.name):
        if not book_dir.is_dir():
            continue
        epub_files = list(book_dir.glob("*.epub"))
        meta_file = book_dir / "meta.txt"
        if epub_files and meta_file.exists():
            title, author = meta_file.read_text(encoding="utf-8").splitlines()[:2]
            books.append({"slug": book_dir.name, "title": title, "author": author})
    return templates.TemplateResponse("index.html", {"request": request, "books": books})


@app.post("/upload")
async def upload_epub(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".epub"):
        raise HTTPException(status_code=400, detail="Upload a valid .epub file")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".epub") as tmp:
        tmp.write(await file.read())
        temp_path = Path(tmp.name)

    meta = parse_book(temp_path)
    slug = safe_slug(meta["title"])
    book_dir = BOOKS_DIR / slug
    book_dir.mkdir(parents=True, exist_ok=True)
    final_path = book_dir / f"{slug}.epub"
    temp_path.replace(final_path)
    (book_dir / "meta.txt").write_text(f"{meta['title']}\n{meta['author']}\n", encoding="utf-8")
    return RedirectResponse(url=f"/books/{slug}", status_code=303)


@app.get("/books/{slug}", response_class=HTMLResponse)
async def read_book(request: Request, slug: str, chapter: int = Query(0, ge=0)):
    book_dir = BOOKS_DIR / slug
    epub_files = list(book_dir.glob("*.epub"))
    if not epub_files:
        raise HTTPException(status_code=404, detail="Book not found")
    epub_path = epub_files[0]
    meta = parse_book(epub_path)
    chapters = meta["chapters"]
    if not chapters:
        raise HTTPException(status_code=400, detail="This EPUB has no readable spine")
    chapter = min(chapter, len(chapters) - 1)
    content = chapter_html(epub_path, chapters[chapter]["href"])
    prev_index = chapter - 1 if chapter > 0 else None
    next_index = chapter + 1 if chapter < len(chapters) - 1 else None
    return templates.TemplateResponse(
        "reader.html",
        {
            "request": request,
            "book": meta,
            "slug": slug,
            "chapter_index": chapter,
            "chapter": chapters[chapter],
            "content": content,
            "prev_index": prev_index,
            "next_index": next_index,
        },
    )