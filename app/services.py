import logging
import re
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.keitaro_client import KeitaroClient, KeitaroError
from app.models import CampaignLog
from app.schemas import CampaignCreateRequest, OffersUpdateRequest

logger = logging.getLogger(__name__)

class CampaignService:
  """Бизнес-логика: создание кампаний с потоками, обновление офферов."""

  def __init__(self, client: KeitaroClient, session: AsyncSession | None = None):
    self.client = client
    self.session = session

  async def create_campaign_with_streams(self, req: CampaignCreateRequest) -> dict[str, Any]:
    """
    Создаёт кампанию в Keitaro с двумя потоками:
    - белый: geo = req.geo → редирект на Google
    - офферный: редирект на req.offer_id
    При ошибке создания потоков — откатывает кампанию.
    """
    domain_id = await self._resolve_domain_id(req.domain_id)

    campaign_payload = self._build_campaign_payload(req, domain_id)
    campaign = await self.client.create_campaign(campaign_payload)
    campaign_id: int = campaign["id"]
    logger.info("Created campaign %s (id=%s)", req.name, campaign_id)

    stream_ids: list[int] = []
    try:
      white_stream = await self.client.create_stream(
        self._build_white_stream_payload(campaign_id, req.geo)
      )
      stream_ids.append(white_stream["id"])

      offer_stream = await self.client.create_stream(
        self._build_offer_stream_payload(campaign_id, req.offer_id)
      )
      stream_ids.append(offer_stream["id"])

    except KeitaroError:
      logger.exception(
        "Failed to create streams for campaign %s, rolling back",
        campaign_id,
      )
      await self._rollback_campaign(campaign_id)
      raise

    await self._log(
      action="create",
      campaign_name=req.name,
      campaign_id=campaign_id,
      stream_id=None,
      payload=req.model_dump_json(),
    )

    return {
      "campaign_id": campaign_id,
      "campaign_name": req.name,
      "stream_ids": stream_ids,
      "message": f"Кампания «{req.name}» создана с {len(stream_ids)} потоками",
    }

  async def _resolve_domain_id(self, domain_id: int | None) -> int:
    """Если domain_id не передан — берём первый доступный в Keitaro."""
    if domain_id is not None:
        return domain_id
    domains = await self.client.list_domains()
    if not domains:
        raise KeitaroError("В Keitaro нет доступных доменов")
    return domains[0]["id"]

  def _build_campaign_payload(
    self, req: CampaignCreateRequest, domain_id: int
  ) -> dict[str, Any]:
    payload = {
      "name": req.name,
      "alias": self._slugify(req.name),
      "domain_id": domain_id,
      "group_id": req.group_id,
      "traffic_source_id": req.source_id,
      "type": "position",
      "state": "active",
    }
    return {k: v for k, v in payload.items() if v is not None}

  def _build_white_stream_payload(
    self, campaign_id: int, geo: str
  ) -> dict[str, Any]:
    """
    Белый поток: schema=redirect, редирект на Google, фильтр GEO.
    """
    return {
      "campaign_id": campaign_id,
      "name": "White (Google)",
      "type": "regular",
      "schema": "redirect",
      "action_type": "http",
      "action_payload": "https://www.google.com/",
      "filters": [
        {
          "name": "country",
          "mode": "accept",
          "payload": geo.upper(),
        }
      ],
      "weight": 100,
    }

  def _build_offer_stream_payload(
    self, campaign_id: int, offer_id: int
  ) -> dict[str, Any]:
    """Офферный поток: schema=offers, без action_type/action_payload."""

    return {
      "campaign_id": campaign_id,
      "name": "Offer",
      "type": "regular",
      "schema": "landings",
      "action_type": "http",
      "landings": [],
      "offers": [{
        "offer_id": offer_id,
        "landing_id": 0,
        "share": 100,
        "state": "active",
      }],
      "weight": 100,
    }

  async def _rollback_campaign(self, campaign_id: int) -> None:
    try:
      await self.client.delete_campaign(campaign_id)
      logger.info("Rolled back campaign %s", campaign_id)
    except KeitaroError:
      logger.error(
        "Rollback failed: campaign %s left in Keitaro, remove manually",
        campaign_id,
      )


  async def get_campaign_detail(self, campaign_id: int) -> dict[str, Any]:
    """Возвращает кампанию с её потоками и списком ID офферов в каждом."""
    campaign = await self.client.get_campaign(campaign_id)
    streams = await self.client.get_campaign_streams(campaign_id)
    return {
      "id": campaign["id"],
      "name": campaign.get("name", ""),
      "streams": [
        {
          "id": s["id"],
          "name": s.get("name", ""),
          "schema": s.get("schema", ""),
          "offer_ids": [
            oid
            for o in (s.get("offers") or [])
            for oid in (o.get("offer_id", o.get("id")),)
            if oid is not None
          ],
        }
        for s in streams
      ],
    }

  async def update_stream_offers(
    self, stream_id: int, req: OffersUpdateRequest
  ) -> dict[str, Any]:
    """
    Заменяет список офферов в потоке целиком (так работает Keitaro API).
    """
    current = await self.client.get_stream(stream_id)

    if current.get("schema") != "landings":
      raise KeitaroError(
        f"Stream {stream_id} has schema={current.get('schema')!r}, "
        "offers can only be managed on 'landings' streams"
      )

    current["offers"] = [
      {
        "offer_id": oid,
        "landing_id": 0,
        "share": self._share_for_index(i, len(req.offer_ids)),
        "state": "active",
      }
      for i, oid in enumerate(req.offer_ids)
    ]

    await self.client.update_stream(stream_id, current)

    await self._log(
      action="update",
      campaign_name=f"stream_{stream_id}",
      campaign_id=None,
      stream_id=stream_id,
      payload=req.model_dump_json(),
    )

    return {
      "stream_id": stream_id,
      "offer_ids": req.offer_ids,
      "message": f"Обновлено {len(req.offer_ids)} офферов в потоке {stream_id}",
    }


  async def _log(
    self,
    action: str,
    campaign_name: str,
    campaign_id: int | None,
    stream_id: int | None,
    payload: str | None,
  ) -> None:
    if self.session is None:
      logger.warning("No DB session, skipping log")
      return
    try:
      log = CampaignLog(
        action=action,
        campaign_name=campaign_name,
        keitaro_campaign_id=campaign_id,
        keitaro_stream_id=stream_id,
        payload=payload,
      )
      self.session.add(log)
      await self.session.commit()
    except Exception:
      logger.exception("Failed to write campaign log, continuing")
      await self.session.rollback()

  @staticmethod
  def _slugify(name: str) -> str:
    """Alias для Keitaro: латиница/цифры, остальное — в '_'."""
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", name).strip("_").lower()
    return slug or "campaign"
  
  @staticmethod
  def _share_for_index(i: int, total: int) -> int:
    """Равномерно делит 100% на total офферов; последнему — остаток."""
    base = 100 // total
    return 100 - base * (total - 1) if i == total - 1 else base