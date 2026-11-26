from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.rate_limit import enforce_public_rate_limit
from backend.app.infrastructure.database.session import get_db_session
from backend.app.modules.catalog.repository import CatalogRepository
from backend.app.modules.catalog.schemas import CatalogFiltersResponse

router = APIRouter(prefix="/catalog", tags=["Catalog"])
_catalog_repository = CatalogRepository()


@router.get(
    "/filters",
    response_model=CatalogFiltersResponse,
    dependencies=[Depends(enforce_public_rate_limit)],
)
async def get_catalog_filters(
    response: Response,
    session: AsyncSession = Depends(get_db_session),
) -> CatalogFiltersResponse:
    response.headers["Cache-Control"] = "public, max-age=3600"
    return await _catalog_repository.get_filter_options(session)
