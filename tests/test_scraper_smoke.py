from contextlib import contextmanager
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

from scrapers.municipalities import CapeTownScraper


@contextmanager
def serve_directory(directory: Path):
    handler = partial(SimpleHTTPRequestHandler, directory=str(directory))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        yield f"http://{host}:{port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_cape_town_scraper_smoke_against_controlled_http_source(monkeypatch):
    monkeypatch.setattr(
        "utils.retry_tools.validate_outbound_url",
        lambda url: url,
    )
    fixtures_dir = Path(__file__).resolve().parent / "fixtures"

    with serve_directory(fixtures_dir) as base_url:
        scraper = CapeTownScraper(timeout=5)
        scraper.url = f"{base_url}/cape_town_tenders.html"
        tenders = scraper.run()

    assert scraper.last_error is None
    assert len(tenders) == 2

    included = next(t for t in tenders if "cooling water treatment chemicals" in t["title"].lower())
    assert included["client"] == "City of Cape Town"
    assert included["source"] == "City of Cape Town"
    assert included["category"] == "MEXEL"
    assert included["ref"].startswith("CPT123")
