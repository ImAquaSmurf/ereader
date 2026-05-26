import html
from pathlib import Path
from zipfile import ZipFile
import xml.etree.ElementTree as ET

from django.http import Http404
from bs4 import BeautifulSoup

NS = {
    'opf': 'http://www.idpf.org/2007/opf',
    'dc': 'http://purl.org/dc/elements/1.1/',
    'container': 'urn:oasis:names:tc:opendocument:xmlns:container',
}


def find_opf(zf: ZipFile) -> str:
    container_xml = ET.fromstring(zf.read('META-INF/container.xml'))
    rootfile = container_xml.find('container:rootfiles/container:rootfile', NS)
    if rootfile is None:
        raise Http404('Invalid EPUB: OPF file not found')
    return rootfile.attrib['full-path']


def load_toc_labels(zf: ZipFile, toc_path: str) -> dict[str, str]:
    labels = {}
    if toc_path.endswith('.ncx'):
        root = ET.fromstring(zf.read(toc_path))
        for nav_point in root.findall('.//{*}navPoint'):
            src = nav_point.find('.//{*}content')
            text = nav_point.find('.//{*}text')
            if src is not None and text is not None:
                labels[src.attrib.get('src', '').split('#')[0]] = text.text or 'Chapter'
    else:
        soup = BeautifulSoup(zf.read(toc_path), 'html.parser')
        for link in soup.select('nav a[href]'):
            labels[link['href'].split('#')[0]] = link.get_text(' ', strip=True)
    return labels


def parse_book(epub_path: Path) -> dict:
    with ZipFile(epub_path) as zf:
        opf_path = find_opf(zf)
        opf_dir = Path(opf_path).parent
        opf_root = ET.fromstring(zf.read(opf_path))
        metadata = opf_root.find('opf:metadata', NS)
        manifest = opf_root.find('opf:manifest', NS)
        spine = opf_root.find('opf:spine', NS)
        if manifest is None or spine is None:
            raise Http404('Invalid EPUB: missing manifest or spine')

        title = metadata.findtext('dc:title', default=epub_path.stem, namespaces=NS) if metadata is not None else epub_path.stem
        author = metadata.findtext('dc:creator', default='Unknown author', namespaces=NS) if metadata is not None else 'Unknown author'

        manifest_items = {}
        toc_path = None
        for item in manifest.findall('opf:item', NS):
            manifest_items[item.attrib['id']] = item.attrib
            if item.attrib.get('properties') == 'nav':
                toc_path = str((opf_dir / item.attrib['href']).as_posix())
            if item.attrib.get('id') == spine.attrib.get('toc'):
                toc_path = str((opf_dir / item.attrib['href']).as_posix())

        chapters = []
        for itemref in spine.findall('opf:itemref', NS):
            item = manifest_items.get(itemref.attrib['idref'])
            if not item:
                continue
            href = str((opf_dir / item['href']).as_posix())
            chapters.append({
                'id': itemref.attrib['idref'],
                'href': href,
                'label': Path(item['href']).stem.replace('_', ' ').title(),
            })

        toc_labels = load_toc_labels(zf, toc_path) if toc_path else {}
        for chapter in chapters:
            chapter['label'] = toc_labels.get(chapter['href'], chapter['label'])

        return {'title': title, 'author': author, 'chapters': chapters}


def chapter_html(epub_path: Path, href: str) -> str:
    with ZipFile(epub_path) as zf:
        raw = zf.read(href)
        soup = BeautifulSoup(raw, 'html.parser')
        body = soup.find('body')
        if body is None:
            return '<p>No readable content found.</p>'
        for tag in body.find_all(['script', 'style']):
            tag.decompose()
        for img in body.find_all('img'):
            alt = html.escape(img.get('alt', 'Illustration omitted'))
            img.replace_with(BeautifulSoup(f'<p class="image-note">[{alt}]</p>', 'html.parser'))
        return ''.join(str(node) for node in body.contents)
