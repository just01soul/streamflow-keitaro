from pydantic import BaseModel, Field


class CampaignCreateRequest(BaseModel):
  """Что приходит с фронта при создании кампании."""

  name: str = Field(
    min_length=1,
    max_length=255,
    description="Название кампании (с префиксом test_фамилия_)",
    examples=["test_ivanov_campaign1"],
  )
  geo: str = Field(
    min_length=2,
    max_length=2,
    description="ISO-код страны (2 буквы), например RU",
    examples=["RU"],
  )
  offer_id: int = Field(
    gt=0,
    description="ID оффера в Keitaro",
  )
  domain_id: int | None = Field(
    None,
    description="ID домена. Если не указан — берётся первый доступный в Keitaro",
  )
  group_id: int | None = Field(
    None,
    description="ID группы кампаний в Keitaro (необязательно)",
  )
  source_id: int | None = Field(
    None,
    description="ID источника трафика в Keitaro (необязательно)",
  )


class CampaignCreateResponse(BaseModel):
  """Что отдаём фронту после создания кампании."""

  campaign_id: int = Field(description="ID кампании в Keitaro")
  campaign_name: str = Field(description="Имя созданной кампании")
  stream_ids: list[int] = Field(description="ID созданных потоков")
  message: str = Field(description="Человекочитаемое сообщение")


class StreamInfo(BaseModel):
  """Информация об одном потоке кампании."""

  id: int = Field(description="ID потока в Keitaro")
  name: str = Field(description="Имя потока")
  schema: str = Field(default="", description="Схема потока: landings, redirect, action")
  offer_ids: list[int] = Field(
    default_factory=list,
    description="ID офферов, привязанных к потоку",
  )


class CampaignDetail(BaseModel):
  """Детальная информация о кампании с её потоками."""

  id: int = Field(description="ID кампании в Keitaro")
  name: str = Field(description="Имя кампании")
  streams: list[StreamInfo] = Field(description="Потоки кампании")


class OffersUpdateRequest(BaseModel):
  """Что приходит с фронта при обновлении офферов в потоке."""

  offer_ids: list[int] = Field(
    description="Новый список ID офферов. Заменяет текущий целиком (так работает Keitaro API)",
    examples=[[1, 2, 3]],
  )


class OffersUpdateResponse(BaseModel):
  """Что отдаём после обновления офферов."""

  stream_id: int = Field(description="ID потока, где обновили офферы")
  offer_ids: list[int] = Field(description="Актуальный список ID офферов")
  message: str = Field(description="Человекочитаемое сообщение")