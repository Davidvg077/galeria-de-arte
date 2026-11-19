import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class ServiceUnavailable(RuntimeError):
    pass


class UpstreamError(RuntimeError):
    def __init__(self, status_code: int):
        self.status_code = status_code


def get_json(service_url: str, path: str, headers: dict[str, str] | None = None) -> dict:
    base_url = os.getenv(service_url)
    if not base_url:
        raise ServiceUnavailable(f"{service_url} is not configured.")
    if not base_url.startswith(("http://", "https://")):
        base_url = f"http://{base_url}"
    request = Request(f"{base_url.rstrip('/')}{path}", headers=headers or {})
    try:
        with urlopen(request, timeout=5) as response:
            return json.loads(response.read())
    except HTTPError as error:
        if 400 <= error.code < 500:
            raise UpstreamError(error.code) from error
        raise ServiceUnavailable(f"Could not reach {service_url}.") from error
    except (URLError, TimeoutError, ValueError) as error:
        raise ServiceUnavailable(f"Could not reach {service_url}.") from error
