from fastapi import FastAPI
from fastapi.responses import Response
import httpx
from xml.etree.ElementTree import Element, SubElement, tostring

app = FastAPI()

CATALOGS = [
    {
        "name": "Project Gutenberg",
        "type": "json",
        "search_url": "https://gutendex.com/books/?search={query}"
    },
]

# ROOT OPDS CATALOG
@app.api_route("/", methods=["GET", "HEAD"])
def root_catalog():

    feed = Element("feed")
    feed.set("xmlns", "http://www.w3.org/2005/Atom")

    title = SubElement(feed, "title")
    title.text = "Global OPDS"

    id_tag = SubElement(feed, "id")
    id_tag.text = "global-opds"

    updated = SubElement(feed, "updated")
    updated.text = "2026-01-01T00:00:00Z"

    search_link = SubElement(feed, "link")
    search_link.set("rel", "search")
    search_link.set("type", "application/opensearchdescription+xml")
    search_link.set(
        "href",
        "https://web-production-ec95c.up.railway.app/opensearch.xml"
    )

    entry = SubElement(feed, "entry")

    entry_title = SubElement(entry, "title")
    entry_title.text = "Search Books"

    entry_id = SubElement(entry, "id")
    entry_id.text = "search-books"

    entry_updated = SubElement(entry, "updated")
    entry_updated.text = "2026-01-01T00:00:00Z"

    entry_link = SubElement(entry, "link")
    entry_link.set(
        "href",
        "https://web-production-ec95c.up.railway.app/opensearch.xml"
    )
    entry_link.set("rel", "search")
    entry_link.set("type", "application/opensearchdescription+xml")

    xml_output = tostring(feed, encoding="utf-8")

    return Response(content=xml_output, media_type="application/atom+xml")

@app.api_route("/opensearch.xml", methods=["GET", "HEAD"])
def opensearch():

    xml = '''<?xml version="1.0" encoding="UTF-8"?>
<OpenSearchDescription xmlns="http://a9.com/-/spec/opensearch/1.1/">
  <ShortName>Global OPDS Search</ShortName>
  <Description>Search books</Description>
  <Url type="application/atom+xml"
       template="https://web-production-ec95c.up.railway.app/search?q={searchTerms}" />
</OpenSearchDescription>
'''

    return Response(content=xml, media_type="application/xml")

# SEARCH ENDPOINT
@app.api_route("/search", methods=["GET", "HEAD"])
async def search(q: str):

    feed = Element("feed")
    feed.set("xmlns", "http://www.w3.org/2005/Atom")

    title = SubElement(feed, "title")
    title.text = f"Search Results for: {q}"

    async with httpx.AsyncClient(timeout=15) as client:

        for catalog in CATALOGS:

            try:

                url = catalog["search_url"].format(query=q)

                response = await client.get(
                    url,
                    follow_redirects=True,
                    headers={"User-Agent": "Mozilla/5.0"}

)

                response.raise_for_status()

                data = response.json()

                # GUTENBERG
                if catalog["name"] == "Project Gutenberg":

                    for book in data.get("results", [])[:5]:

                        entry = SubElement(feed, "entry")

                        entry_title = SubElement(entry, "title")
                        entry_title.text = book.get("title", "Unknown")

                        author = "Unknown"

                        if book.get("authors"):
                            author = book["authors"][0]["name"]

                        author_tag = SubElement(entry, "author")
                        author_name = SubElement(author_tag, "name")
                        author_name.text = author

                        entry_id = SubElement(entry, "id")
                        entry_id.text = str(book.get("id", "unknown"))

                        entry_updated = SubElement(entry, "updated")
                        entry_updated.text = "2026-01-01T00:00:00Z"

                        content = SubElement(entry, "content")
                        content.text = book.get("title", "Unknown")

                        formats = book.get("formats", {})

                        epub_url = (
                        formats.get("application/epub+zip")
                        or formats.get("application/epub+zip; charset=utf-8") )

                        if epub_url:
                            link = SubElement(entry, "link")
                            link.set("href", epub_url)
                            link.set("type", "application/epub+zip")
                            link.set("rel", "http://opds-spec.org/acquisition")

            except Exception as e:
                import traceback
                print(f"ERROR in {catalog['name']}")
                print(f"Skipping failed source: {catalog['name']}")

        xml_output = tostring(feed, encoding="utf-8")
        return Response(content=xml_output, media_type="application/atom+xml")

        