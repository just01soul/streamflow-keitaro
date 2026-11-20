import json
import logging
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class KeitaroError(Exception):
  """Ошибка при обращении к Keitaro API."""

  def __init__(
    self,
    message: str,
    status_code: int | None = None,
    body: str | None = None,
  ):
    self.status_code = status_code
    self.body = body
    super().__init__(message)


class KeitaroClient:
  """Асинхронный клиент для Admin API Keitaro."""

  def __init__(self, base_url: str | None = None, api_key: str | None = None):
    self.base_url = (base_url or settings.keitaro_base_url).rstrip("/")
    self.api_key = api_key or settings.keitaro_api_key
    self._client = httpx.AsyncClient(
      base_url=self.base_url,
      headers={"Api-Key": self.api_key},
      timeout=httpx.Timeout(connect=5.0, read=30.0, write=10.0, pool=5.0),
    )

  async def close(self) -> None:
    await self._client.aclose()

  async def _request(
    self,
    method: str,
    path: str,
    *,
    json: Any = None,
    params: dict[str, Any] | None = None,
    timeout: float | None = None,
  ) -> Any:
    url = f"{self.base_url}{path}"
    try:
      response = await self._client.request(
        method, url, json=json, params=params, timeout=timeout
      )
    except httpx.RequestError as exc:
      logger.error("Keitaro request failed: %s %s — %s", method, path, exc)
      raise KeitaroError(f"Сетевая ошибка при запросе к Keitaro: {exc}") from exc

    if response.status_code >= 400:
      logger.error(
        "Keitaro returned %s for %s %s: %s",
        response.status_code,
        method,
        path,
        response.text[:500],
      )
      raise KeitaroError(
        f"Keitaro вернул {response.status_code}",
        status_code=response.status_code,
        body=response.text,
      )

    if response.status_code == 204 or not response.content:
      return None

    try:
      return response.json()
    except json.JSONDecodeError as exc:
      logger.error("Keitaro returned non-JSON: %s", response.text[:500])
      raise KeitaroError(
        "Keitaro вернул не-JSON ответ",
        status_code=response.status_code,
        body=response.text,
      ) from exc

  async def create_campaign(self, payload: dict[str, Any]) -> dict[str, Any]:
    return await self._request("POST", "/campaigns", json=payload)

  async def get_campaign(self, campaign_id: int) -> dict[str, Any]:
    return await self._request("GET", f"/campaigns/{campaign_id}")

  async def delete_campaign(self, campaign_id: int) -> None:
    """Удалить кампанию (для rollback при ошибке создания потоков)."""
    await self._request("DELETE", f"/campaigns/{campaign_id}", timeout=60.0)

  async def create_stream(self, payload: dict[str, Any]) -> dict[str, Any]:
    return await self._request("POST", "/streams", json=payload)

  async def update_stream(
    self, stream_id: int, payload: dict[str, Any]
  ) -> dict[str, Any]:
    return await self._request("PUT", f"/streams/{stream_id}", json=payload)

  async def get_campaign_streams(self, campaign_id: int) -> list[dict[str, Any]]:
    data = await self._request("GET", f"/campaigns/{campaign_id}/streams")
    return data if isinstance(data, list) else []

  async def list_domains(self) -> list[dict[str, Any]]:
    data = await self._request("GET", "/domains")
    return data if isinstance(data, list) else []

  async def list_groups(self) -> list[dict[str, Any]]:
    data = await self._request("GET", "/groups", params={"type": "campaign"})
    return data if isinstance(data, list) else []

  async def list_sources(self) -> list[dict[str, Any]]:
    data = await self._request("GET", "/traffic_sources")
    return data if isinstance(data, list) else []

  async def list_offers(self) -> list[dict[str, Any]]:
    data = await self._request("GET", "/offers")
    return data if isinstance(data, list) else []

  async def list_campaigns(self) -> list[dict[str, Any]]:
    data = await self._request("GET", "/campaigns")
    return data if isinstance(data, list) else []

  async def get_stream(self, stream_id: int) -> dict[str, Any]:
    return await self._request("GET", f"/streams/{stream_id}")