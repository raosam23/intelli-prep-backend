from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_session
from app.services.analytics_service import get_dashboard_data
from app.schemas.analytics import DashboardResponse
from app.models.user import User
from app.api.dependencies import get_current_user
from sqlalchemy.exc import SQLAlchemyError

router = APIRouter()

@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)) -> DashboardResponse:
    """Endpoint to retrieve dashboard data for the current user"""
    try:
        dashboard_data = await get_dashboard_data(session, user.id)
        return dashboard_data
    except SQLAlchemyError as err:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database error: {str(err)}")
    except Exception as err:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(err))
