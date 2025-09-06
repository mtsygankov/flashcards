"""
Database models using SQLAlchemy for the flashcards application.
Based on the schema defined in the design document.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Integer, 
    String, Text, UUID, Float, func
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Mapped, mapped_column

Base = declarative_base()


def utc_now():
    """Helper function to get current UTC timestamp"""
    return datetime.now(timezone.utc)


class User(Base):
    """User model for authentication and profile management"""
    __tablename__ = "users"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=utc_now
    )
    last_active_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=utc_now
    )
    
    # Relationships
    decks: Mapped[List["Deck"]] = relationship("Deck", back_populates="user")
    user_statistics: Mapped[Optional["UserStatistics"]] = relationship(
        "UserStatistics", back_populates="user", uselist=False
    )
    card_progress: Mapped[List["UserCardProgress"]] = relationship(
        "UserCardProgress", back_populates="user"
    )
    study_sessions: Mapped[List["StudySession"]] = relationship(
        "StudySession", back_populates="user"
    )
    card_interactions: Mapped[List["CardInteraction"]] = relationship(
        "CardInteraction", back_populates="user"
    )


class UserStatistics(Base):
    """Overall user statistics"""
    __tablename__ = "user_statistics"
    
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("users.id", ondelete="CASCADE"), 
        primary_key=True
    )
    total_views: Mapped[int] = mapped_column(Integer, default=0)
    total_correct_answers: Mapped[int] = mapped_column(Integer, default=0)
    total_quiz_attempts: Mapped[int] = mapped_column(Integer, default=0)
    study_time_minutes: Mapped[int] = mapped_column(Integer, default=0)
    
    # Relationship
    user: Mapped["User"] = relationship("User", back_populates="user_statistics")


class Deck(Base):
    """Deck model for organizing flashcards"""
    __tablename__ = "decks"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("users.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=utc_now
    )
    last_studied_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    total_study_time: Mapped[int] = mapped_column(Integer, default=0)  # in seconds
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="decks")
    cards: Mapped[List["Card"]] = relationship("Card", back_populates="deck")
    study_sessions: Mapped[List["StudySession"]] = relationship(
        "StudySession", back_populates="deck"
    )


class Card(Base):
    """Card model for individual flashcards"""
    __tablename__ = "cards"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )
    deck_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("decks.id", ondelete="CASCADE")
    )
    hanzi: Mapped[str] = mapped_column(Text, nullable=False)
    pinyin: Mapped[str] = mapped_column(Text, nullable=False)
    english: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=utc_now
    )
    
    # Relationships
    deck: Mapped["Deck"] = relationship("Deck", back_populates="cards")
    user_progress: Mapped[List["UserCardProgress"]] = relationship(
        "UserCardProgress", back_populates="card"
    )
    card_interactions: Mapped[List["CardInteraction"]] = relationship(
        "CardInteraction", back_populates="card"
    )


class UserCardProgress(Base):
    """User-specific progress tracking for each card"""
    __tablename__ = "user_card_progress"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("users.id", ondelete="CASCADE")
    )
    card_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("cards.id", ondelete="CASCADE")
    )
    
    # Flip tracking
    flip_count: Mapped[int] = mapped_column(Integer, default=0)
    first_flipped_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_flipped_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Quiz tracking
    quiz_attempts: Mapped[int] = mapped_column(Integer, default=0)
    quiz_correct: Mapped[int] = mapped_column(Integer, default=0)
    last_quiz_attempt_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Learning metrics
    difficulty_score: Mapped[float] = mapped_column(Float, default=1.0)
    mastery_level: Mapped[int] = mapped_column(Integer, default=0)  # 0=new, 1=learning, 2=review, 3=mastered
    next_review_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=utc_now
    )
    
    # Performance tracking
    consecutive_correct: Mapped[int] = mapped_column(Integer, default=0)
    total_study_time: Mapped[int] = mapped_column(Integer, default=0)  # seconds spent on this card
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=utc_now, 
        onupdate=utc_now
    )
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="card_progress")
    card: Mapped["Card"] = relationship("Card", back_populates="user_progress")
    
    # Unique constraint
    __table_args__ = ({"schema": None},)


class StudySession(Base):
    """Study session tracking"""
    __tablename__ = "study_sessions"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("users.id", ondelete="CASCADE")
    )
    deck_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("decks.id", ondelete="CASCADE")
    )
    direction: Mapped[str] = mapped_column(
        String(20), 
        nullable=False
    )  # 'chinese_to_english' or 'english_to_chinese'
    cards_studied: Mapped[int] = mapped_column(Integer, default=0)
    correct_answers: Mapped[int] = mapped_column(Integer, default=0)
    session_duration: Mapped[int] = mapped_column(Integer, default=0)  # minutes
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=utc_now
    )
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="study_sessions")
    deck: Mapped["Deck"] = relationship("Deck", back_populates="study_sessions")
    card_interactions: Mapped[List["CardInteraction"]] = relationship(
        "CardInteraction", back_populates="session"
    )


class CardInteraction(Base):
    """Individual card interactions within study sessions"""
    __tablename__ = "card_interactions"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("study_sessions.id", ondelete="CASCADE")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("users.id", ondelete="CASCADE")
    )
    card_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("cards.id", ondelete="CASCADE")
    )
    interaction_type: Mapped[str] = mapped_column(
        String(20), 
        nullable=False
    )  # 'flip', 'quiz_correct', 'quiz_incorrect'
    direction: Mapped[Optional[str]] = mapped_column(String(20))  # for quiz interactions
    response_time: Mapped[Optional[int]] = mapped_column(Integer)  # milliseconds
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=utc_now
    )
    
    # Relationships
    session: Mapped["StudySession"] = relationship(
        "StudySession", back_populates="card_interactions"
    )
    user: Mapped["User"] = relationship("User", back_populates="card_interactions")
    card: Mapped["Card"] = relationship("Card", back_populates="card_interactions")