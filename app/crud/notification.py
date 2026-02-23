from sqlalchemy.orm import Session
from app.models.notification import Notification, NotificationType
from app.schemas.notification import NotificationCreate, NotificationUpdate
from uuid import UUID
from typing import Optional, List


def create_notification(db: Session, notification_data: NotificationCreate) -> Notification:
    """Create a new notification"""
    db_notification = Notification(
        user_id=notification_data.user_id,
        title=notification_data.title,
        message=notification_data.message,
        notification_type=notification_data.notification_type,
        ticket_id=notification_data.ticket_id,
        related_user_id=notification_data.related_user_id,
    )
    db.add(db_notification)
    db.commit()
    db.refresh(db_notification)
    return db_notification


def get_notification_by_id(db: Session, notification_id: UUID) -> Optional[Notification]:
    """Get notification by ID"""
    return db.query(Notification).filter(Notification.id == notification_id).first()


def get_user_notifications(db: Session, user_id: UUID, skip: int = 0, limit: int = 100) -> List[Notification]:
    """Get all notifications for a user, ordered by most recent first"""
    return (
        db.query(Notification)
        .filter(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_unread_notifications_count(db: Session, user_id: UUID) -> int:
    """Get count of unread notifications for a user"""
    return db.query(Notification).filter(
        Notification.user_id == user_id,
        Notification.is_read == False
    ).count()


def get_user_unread_notifications(db: Session, user_id: UUID, limit: int = 10) -> List[Notification]:
    """Get unread notifications for a user"""
    return (
        db.query(Notification)
        .filter(Notification.user_id == user_id, Notification.is_read == False)
        .order_by(Notification.created_at.desc())
        .limit(limit)
        .all()
    )


def mark_notification_as_read(db: Session, notification_id: UUID) -> Optional[Notification]:
    """Mark a notification as read"""
    notification = get_notification_by_id(db, notification_id)
    if notification:
        notification.is_read = True
        db.commit()
        db.refresh(notification)
    return notification


def mark_all_user_notifications_as_read(db: Session, user_id: UUID) -> int:
    """Mark all notifications for a user as read"""
    result = db.query(Notification).filter(
        Notification.user_id == user_id,
        Notification.is_read == False
    ).update({Notification.is_read: True})
    db.commit()
    return result


def delete_notification(db: Session, notification_id: UUID) -> bool:
    """Delete a notification"""
    notification = get_notification_by_id(db, notification_id)
    if notification:
        db.delete(notification)
        db.commit()
        return True
    return False


def delete_user_notification(db: Session, notification_id: UUID, user_id: UUID) -> bool:
    """Delete a notification that belongs to a user"""
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == user_id
    ).first()
    if notification:
        db.delete(notification)
        db.commit()
        return True
    return False


def update_notification(db: Session, notification_id: UUID, notification_data: NotificationUpdate) -> Optional[Notification]:
    """Update a notification"""
    notification = get_notification_by_id(db, notification_id)
    if notification:
        for key, value in notification_data.dict(exclude_unset=True).items():
            if value is not None:
                setattr(notification, key, value)
        db.commit()
        db.refresh(notification)
    return notification
