"""
FastAPI dependencies — reusable across all endpoints.

  - verify_api_key  : checks X-API-Key header
  - validate_ghana  : rejects GPS coords outside Ghana's bounding box
"""

from fastapi import Header, HTTPException, status
from app.core.config import get_settings


async def verify_api_key(x_api_key: str = Header(..., description="API key for authentication")):
    """
    All endpoints require an X-API-Key header.
    Set API_KEY in .env to a strong secret in production.
    """
    settings = get_settings()
    if x_api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key.",
        )


def validate_ghana_coordinates(lat: float, lng: float):
    """
    Reject coordinates that fall outside Ghana's geographic bounding box.
    Prevents garbage GPS data from polluting the database.

    Ghana bounds:
      Latitude  : 4.5°N  – 11.5°N
      Longitude : 3.5°W  – 1.5°E
    """
    settings = get_settings()
    if not (settings.ghana_lat_min <= lat <= settings.ghana_lat_max):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Latitude {lat} is outside Ghana's bounds "
                f"({settings.ghana_lat_min}°N – {settings.ghana_lat_max}°N)."
            ),
        )
    if not (settings.ghana_lng_min <= lng <= settings.ghana_lng_max):

        def _lng_label(value: float) -> str:
            return f"{abs(value)}°W" if value < 0 else f"{value}°E"

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Longitude {lng} is outside Ghana's bounds "
                f"({_lng_label(settings.ghana_lng_min)} – {_lng_label(settings.ghana_lng_max)})."
            ),
        )
