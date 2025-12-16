import logging
from typing import Optional

import requests

try:
    from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "tenacity is required for retry support. Install with: pip install tenacity"
    ) from exc


logger = logging.getLogger(__name__)


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
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type((requests.RequestException, ConnectionError)),
    before_sleep=_log_before_sleep,
    reraise=True,
)
def _requests_get_with_retry(url: str, **kwargs):
    response = requests.get(url, **kwargs)
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

