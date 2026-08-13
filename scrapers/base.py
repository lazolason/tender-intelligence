# ==========================================================
# BASE SCRAPER — ABSTRACT CLASS
# Standardized interface for all tender scrapers
# ==========================================================

from abc import ABC, abstractmethod
from dataclasses import dataclass
import logging
from typing import Any, Callable, Dict, List, Optional

from utils.retry_tools import safe_get

logger = logging.getLogger(__name__)

TenderList = List[Dict[str, Any]]


class BaseScraper(ABC):
    """Abstract base class for all tender scrapers.

    Provides standardized error handling, logging, and return types.
    All scrapers should inherit from this class and implement `scrape()`.

    Example:
        class MyScraper(BaseScraper):
            def __init__(self):
                super().__init__("My Source")

            def scrape(self) -> List[Dict[str, Any]]:
                response = self.request("https://example.com/tenders")
                # parse and return tenders
                return tenders
    """

    def __init__(self, source_name: str, log_file: Optional[str] = None) -> None:
        self.source_name = source_name
        self.log_file = log_file
        self.errors: List[str] = []
        self.last_error: Optional[str] = None
        self._logger = logging.getLogger(f"{__name__}.{source_name}")

    @abstractmethod
    def scrape(self) -> TenderList:
        """Execute the scrape and return list of tender dicts.

        Returns:
            List of tender dictionaries with standard keys:
            ref, title, description, client, source, url, closing_date,
            category, reason, short_title
        """
        ...

    def run(self, *, raise_on_error: bool = False) -> TenderList:
        """Template method with standardized error handling.

        Args:
            raise_on_error: Re-raise the underlying exception after logging.

        Returns:
            List of tender dicts, or empty list on failure.
        """
        try:
            self.last_error = None
            self.errors.clear()
            tenders = self.scrape()
            if not isinstance(tenders, list):
                raise TypeError(
                    f"{self.source_name} scraper returned {type(tenders).__name__}, expected list"
                )
            self._logger.info("%s: found %d tenders", self.source_name, len(tenders))
            return tenders
        except Exception as exc:
            error_msg = f"{self.source_name} scraper failed: {exc}"
            self.last_error = str(exc)
            self.errors.append(error_msg)
            self._logger.exception(error_msg)
            if raise_on_error:
                raise
            return []

    def request(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 20,
    ) -> Any:
        """Wrapper around safe_get with source logging.

        Args:
            url: URL to fetch
            headers: Optional request headers
            timeout: Request timeout in seconds. TLS certificates are always verified.

        Returns:
            Response object or None on failure
        """
        response = safe_get(
            url,
            headers=headers,
            timeout=timeout,
            log=self._logger,
        )
        if response is None:
            self.errors.append(f"Failed to fetch: {url}")
            self._logger.warning("Failed to fetch %s", url)
        return response


@dataclass(frozen=True)
class ScraperRegistration:
    """Static registration describing one scraper entrypoint."""

    name: str
    scrape_func: Callable[[], TenderList]
    requires_selenium: bool = False
    description: str = ""

    def build(self) -> "FunctionScraper":
        """Build a runnable scraper wrapper for this registration."""
        return FunctionScraper(
            source_name=self.name,
            scrape_func=self.scrape_func,
            description=self.description,
        )


class FunctionScraper(BaseScraper):
    """Adapter that wraps an existing scraper function in the BaseScraper contract."""

    def __init__(
        self,
        source_name: str,
        scrape_func: Callable[[], TenderList],
        *,
        description: str = "",
        log_file: Optional[str] = None,
    ) -> None:
        super().__init__(source_name, log_file=log_file)
        self.scrape_func = scrape_func
        self.description = description

    def scrape(self) -> TenderList:
        return self.scrape_func()
