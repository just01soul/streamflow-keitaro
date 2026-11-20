from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CampaignLog(Base):
  """Лог действий с кампаниями Keitaro: кто, что и когда сделал."""

  __tablename__ = "campaign_logs"

  id: Mapped[int] = mapped_column(primary_key=True)
  action: Mapped[str] = mapped_column(String(20), nullable=False)
  campaign_name: Mapped[str] = mapped_column(String(100), nullable=False)
  keitaro_campaign_id: Mapped[int | None] = mapped_column( nullable=True)
  keitaro_stream_id: Mapped[int | None] = mapped_column( nullable=True)
  payload: Mapped[str | None] = mapped_column(String, nullable=True)
  created_at: Mapped[datetime] = mapped_column(
    DateTime(timezone=True), server_default=func.now(), nullable=False
  )