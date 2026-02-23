from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.notification import NotificationOut, NotificationUpdate
from app.crud import notification as crud_notification

router = APIRouter()


@router.get(
    "/notifications",
    response_model=List[NotificationOut],
    status_code=status.HTTP_200_OK,
    tags=["Notifications"],
)
async def get_current_user_notifications(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all notifications for current user."""
    return crud_notification.get_user_notifications(db, current_user.id, skip=skip, limit=limit)


@router.get(
    "/notifications/unread/count",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    tags=["Notifications"],
)
async def get_unread_notifications_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get count of unread notifications for current user."""
    count = crud_notification.get_unread_notifications_count(db, current_user.id)
    return {"unread_count": count}


@router.patch(
    "/notifications/{notification_id}",
    response_model=NotificationOut,
    status_code=status.HTTP_200_OK,
    tags=["Notifications"],
)
async def update_notification(
    notification_id: str,
    notification_data: NotificationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark notification as read."""
    notification = crud_notification.get_notification_by_id(db, notification_id)
    if not notification or notification.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )
    
    updated = crud_notification.update_notification(db, notification_id, notification_data)
    return updated


@router.post(
    "/notifications/mark-all-read",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    tags=["Notifications"],
)
async def mark_all_notifications_as_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark all notifications for current user as read."""
    count = crud_notification.mark_all_user_notifications_as_read(db, current_user.id)
    return {"marked_as_read": count}


@router.delete(
    "/notifications/{notification_id}",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    tags=["Notifications"],
)
async def delete_notification(
    notification_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a notification."""
    deleted = crud_notification.delete_user_notification(db, notification_id, current_user.id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )
    return {"deleted": True}
