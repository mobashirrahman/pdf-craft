"""Small offline checks; not a replacement for EPUBCheck or reader testing."""

import posixpath
from urllib.parse import unquote, urlsplit
from xml.etree import ElementTree as ET
from zipfile import ZipFile, ZIP_STORED


def validate_publication(path):
    """Raise on missing manifest resources, duplicate IDs or broken local links."""
    with ZipFile(path) as archive:
        names = set(archive.namelist())
        first = archive.infolist()[0]
        if first.filename != "mimetype" or first.compress_type != ZIP_STORED or archive.read(first) != b"application/epub+zip":
            raise ValueError("EPUB mimetype must be first and uncompressed")
        roots = {name: ET.fromstring(archive.read(name)) for name in names
                 if name.endswith((".xhtml", ".opf", ".ncx"))}
        ids = {}
        for name, root in roots.items():
            values = [node.get("id") for node in root.iter() if node.get("id")]
            if len(set(values)) != len(values):
                raise ValueError(f"Duplicate XML IDs in {name}")
            ids[name] = set(values)
        for name, root in roots.items():
            for node in root.iter():
                if node.tag.endswith("}itemref") and node.get("idref") not in ids[name]:
                    raise ValueError(f"Missing spine item in {name}")
                for key in ("href", "src"):
                    link = node.get(key)
                    if link is None:
                        continue
                    parsed = urlsplit(link)
                    if parsed.scheme or parsed.netloc:
                        continue
                    target = posixpath.normpath(posixpath.join(posixpath.dirname(name), unquote(parsed.path))) if parsed.path else name
                    if target not in names:
                        raise ValueError(f"Missing EPUB resource: {name}: {link}")
                    if parsed.fragment and target in ids and unquote(parsed.fragment) not in ids[target]:
                        raise ValueError(f"Broken EPUB fragment: {name}: {link}")
        return {"status": "passed", "xml_documents": len(roots), "resources": len(names),
                "scope": "XML, mimetype, manifest/spine and local href/src links; not full EPUB conformance"}
