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
    title.text = "Global OPDS Search"

    author = SubElement(feed, "author")
    author_name = SubElement(author, "name")
    author_name.text = "Global OPDS"

    icon = SubElement(feed, "icon")
    icon.text = ""

    id_tag = SubElement(feed, "id")
    id_tag.text = "global-opds"

    updated = SubElement(feed, "updated")
    updated.text = "2026-01-01T00:00:00Z"

    link = SubElement(feed, "link")
    link.set("rel", "http://opds-spec.org/search")
    link.set("type", "application/opensearchdescription+xml")
    link.set("href", "http://192.168.1.7:8000/opensearch.xml")

    xml_output = tostring(feed, encoding="utf-8")

    return Response(content=xml_output, media_type="application/atom+xml")

@app.api_route("/opensearch.xml", methods=["GET", "HEAD"])
def opensearch():

    xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<OpenSearchDescription xmlns="http://a9.com/-/spec/opensearch/1.1/">
  <ShortName>Global OPDS Search</ShortName>
  <Description>Search books</Description>
  <Url type="application/atom+xml"
       template="http://192.168.1.7:8000/search?q={{searchTerms}}" />
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

        