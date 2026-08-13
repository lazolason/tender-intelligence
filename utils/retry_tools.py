import ipaddress
import logging
from typing import Optional
from urllib.parse import urlparse

import requests

try:
    from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "tenacity is required for retry support. Install with: pip install tenacity"
    ) from exc


logger = logging.getLogger(__name__)


def validate_outbound_url(url: str, *, allow_local_http: bool = False) -> str:
    """Require authenticated transport for outbound requests.

    Plain HTTP is allowed only for explicit loopback development endpoints when
    ``allow_local_http`` is requested. Scrapers never enable that exception.
    """
    parsed = urlparse(str(url or ""))
    hostname = (parsed.hostname or "").lower()
    if (
        allow_local_http
        and parsed.scheme == "http"
        and hostname in {"localhost", "127.0.0.1", "::1"}
    ):
        return url
    if hostname == "localhost" or hostname.endswith(".localhost"):
        raise ValueError(f"Refusing local outbound URL: {url}")
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        address = None
    if address and not address.is_global:
        raise ValueError(f"Refusing non-public outbound IP: {url}")
    if parsed.scheme == "https" and hostname:
        return url
    raise ValueError(f"Refusing insecure or invalid outbound URL: {url}")


def secure_request_kwargs(kwargs):
    """Apply secure TLS defaults and reject attempts to disable verification."""
    prepared = dict(kwargs)
    if prepared.get("verify") is False:
        raise ValueError("TLS certificate verification cannot be disabled")
    prepared.setdefault("verify", True)
    prepared.setdefault("timeout", 30)
    return prepared


def _log_before_sleep(retry_state):
    url = retry_state.args[0] if retry_state.args else None
    exc = retry_state.outcome.exception() if retry_state.outcome else None
    attempt = retry_state.attempt_number
    sleep = getattr(getattr(retry_state, "next_action", None), "sleep", None)

    if url:
        logger.warning(
            "Retrying %s (attempt %s/3) in %ss due to: %s",
            url,
            attempt,
            sleep,
            exc,
        )
    else:
        logger.warning(
            "Retrying (attempt %s/3) in %ss due to: %s",
            attempt,
            sleep,
            exc,
        )


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=60),
    retry=retry_if_exception_type((requests.RequestException, ConnectionError)),
    before_sleep=_log_before_sleep,
    reraise=True,
)
def _requests_get_with_retry(url: str, **kwargs):
    validate_outbound_url(url)
    response = requests.get(url, **secure_request_kwargs(kwargs))
    try:
        validate_outbound_url(response.url)
    except ValueError:
        response.close()
        raise
    # Retry on 5xx server errors
    if response.status_code in [502, 503, 504]:
        response.raise_for_status()
    return response


def safe_get(url: str, *, log: Optional[logging.Logger] = None, **kwargs):
    """
    requests.get wrapper with exponential-backoff retries.
    Returns a Response or None (after final failure).
    """
    active_logger = log or logger
    try:
        return _requests_get_with_retry(url, **kwargs)
    except Exception as exc:
        active_logger.error("Final failure after retries: %s (%s)", url, exc)
        return None


def build_selenium_get_with_retry(retry_exceptions):
    from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(retry_exceptions),
        before_sleep=_log_before_sleep,
        reraise=True,
    )
    def _driver_get(driver, url: str):
        driver.get(url)

    return _driver_get


def safe_driver_get(driver, url: str, *, driver_get_with_retry=None, log: Optional[logging.Logger] = None) -> bool:
    """
    Selenium driver.get wrapper with exponential-backoff retries.
    Returns True on success, False after final failure.
    """
    active_logger = log or logger

    if driver_get_with_retry is None:
        from selenium.common.exceptions import TimeoutException, WebDriverException

        driver_get_with_retry = build_selenium_get_with_retry(
            (WebDriverException, TimeoutException, ConnectionError)
        )

    try:
        driver_get_with_retry(driver, url)
        return True
    except Exception as exc:
        active_logger.error("Final failure after retries: %s (%s)", url, exc)
        return False

# ==========================================================
# SIMPLE RETRY DECORATOR (User Requested)
# ==========================================================
from functools import wraps
import time

def retry_request(max_attempts=3, delay=2):
    """
    Simple retry decorator for requests.
    Usage:
        @retry_request(max_attempts=3, delay=2)
        def fetch_url(url):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        time.sleep(delay)
            if last_exception:
                raise last_exception
        return wrapper
    return decorator

