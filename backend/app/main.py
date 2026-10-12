from fastapi import FastAPI

from app.api.v1.router import router
from app.core.config import get_settings
from app.core.logging import configure_logging

settings = get_settings()
configure_logging(settings.log_level)
app = FastAPI(title="ResQ", version="0.1.0", description="Earthquake catalog research and simulation foundation; not a prediction system.")
app.include_router(router)
