import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.keitaro_client import KeitaroClient, KeitaroError
from app.schemas import (
  CampaignCreateRequest,
  CampaignCreateResponse,
  CampaignDetail,
  OffersUpdateRequest,
  OffersUpdateResponse,
)
from app.services import CampaignService

logging.basicConfig(
  level=logging.INFO,
  format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
  app.state.keitaro = KeitaroClient()
  logger.info("Keitaro client initialized")
  yield
  await app.state.keitaro.close()
  logger.info("Keitaro client closed")


app = FastAPI(
  title="Streamflow",
  description="UI для создания и редактирования кампаний Keitaro",
  version="0.1.0",
  lifespan=lifespan,
)

def get_keitaro(request: Request) -> KeitaroClient:
  return request.app.state.keitaro

@app.exception_handler(KeitaroError)
async def keitaro_error_handler(request: Request, exc: KeitaroError):
  status = 502 if (exc.status_code is None or exc.status_code >= 500) else 400
  logger.error("Keitaro error on %s: %s", request.url.path, exc)
  return JSONResponse(
    status_code=status,
    content={
      "detail": str(exc),
      "keitaro_status": exc.status_code,
      "keitaro_body": (exc.body or "")[:1000],
    },
  )

@app.post(
  "/api/campaigns",
  response_model=CampaignCreateResponse,
  summary="Создать кампанию с двумя потоками",
)
async def create_campaign(
  req: CampaignCreateRequest,
  client: KeitaroClient = Depends(get_keitaro),
  session: AsyncSession = Depends(get_session),
) -> CampaignCreateResponse:
  service = CampaignService(client=client, session=session)
  result = await service.create_campaign_with_streams(req)
  return CampaignCreateResponse(**result)

@app.get(
  "/api/campaigns/{campaign_id}",
  response_model=CampaignDetail,
  summary="Получить кампанию с потоками и офферами",
)
async def get_campaign(
  campaign_id: int,
  client: KeitaroClient = Depends(get_keitaro),
) -> CampaignDetail:
  service = CampaignService(client=client)
  result = await service.get_campaign_detail(campaign_id)
  return CampaignDetail(**result)

@app.post(
  "/api/streams/{stream_id}/offers",
  response_model=OffersUpdateResponse,
  summary="Заменить список офферов в потоке",
)
async def update_stream_offers(
  stream_id: int,
  req: OffersUpdateRequest,
  client: KeitaroClient = Depends(get_keitaro),
  session: AsyncSession = Depends(get_session),
) -> OffersUpdateResponse:
  service = CampaignService(client=client, session=session)
  result = await service.update_stream_offers(stream_id, req)
  return OffersUpdateResponse(**result)

@app.get("/api/domains", summary="Домены Keitaro")
async def list_domains(client: KeitaroClient = Depends(get_keitaro)):
  return await client.list_domains()


@app.get("/api/groups", summary="Группы кампаний")
async def list_groups(client: KeitaroClient = Depends(get_keitaro)):
  return await client.list_groups()


@app.get("/api/sources", summary="Источники трафика")
async def list_sources(client: KeitaroClient = Depends(get_keitaro)):
  return await client.list_sources()


@app.get("/api/offers", summary="Офферы Keitaro")
async def list_offers(client: KeitaroClient = Depends(get_keitaro)):
  return await client.list_offers()

@app.get("/api/campaigns", summary="Список кампаний Keitaro")
async def list_campaigns(client: KeitaroClient = Depends(get_keitaro)):
  return await client.list_campaigns()

@app.get("/health", summary="Проверка живости")
async def health():
  return {"status": "ok"}


app.mount("/static", StaticFiles(directory="static", html=True), name="static")