"""
Pydantic schemas for API request/response validation
"""
import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, validator


class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr


class UserCreate(UserBase):
    password: str = Field(..., min_length=6)


class UserUpdate(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[EmailStr] = None


class UserResponse(BaseModel):
    id: uuid.UUID
    username: str
    email: str
    created_at: datetime
    last_active_at: datetime
    
    class Config:
        from_attributes = True


class UserStatisticsResponse(BaseModel):
    total_views: int
    total_correct_answers: int
    total_quiz_attempts: int
    study_time_minutes: int
    accuracy_rate: Optional[float] = None
    
    @validator("accuracy_rate", always=True)
    def calculate_accuracy_rate(cls, v, values):
        if values.get("total_quiz_attempts", 0) > 0:
            return values["total_correct_answers"] / values["total_quiz_attempts"]
        return 0.0
    
    class Config:
        from_attributes = True


class DeckBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None


class DeckCreate(DeckBase):
    pass


class DeckUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None


class DeckResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str]
    created_at: datetime
    last_studied_at: Optional[datetime]
    total_study_time: int
    card_count: Optional[int] = 0
    
    class Config:
        from_attributes = True


class UserDeckProgress(BaseModel):
    """User-specific progress for a deck"""
    cards_new: int = 0
    cards_learning: int = 0
    cards_review: int = 0
    cards_mastered: int = 0
    average_accuracy: float = 0.0


class DeckWithProgress(DeckResponse):
    """Deck response including user progress"""
    user_progress: Optional[UserDeckProgress] = None


class CardBase(BaseModel):
    hanzi: str = Field(..., min_length=1)
    pinyin: str = Field(..., min_length=1)
    english: str = Field(..., min_length=1)


class CardCreate(CardBase):
    pass


class CardUpdate(BaseModel):
    hanzi: Optional[str] = Field(None, min_length=1)
    pinyin: Optional[str] = Field(None, min_length=1)
    english: Optional[str] = Field(None, min_length=1)


class CardResponse(BaseModel):
    id: uuid.UUID
    deck_id: uuid.UUID
    hanzi: str
    pinyin: str
    english: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class UserCardProgressResponse(BaseModel):
    """User-specific progress for a card"""
    flip_count: int
    quiz_attempts: int
    quiz_correct: int
    difficulty_score: float
    mastery_level: int
    next_review_at: datetime
    consecutive_correct: int
    total_study_time: int
    accuracy_rate: Optional[float] = None
    
    @validator("accuracy_rate", always=True)
    def calculate_accuracy_rate(cls, v, values):
        if values.get("quiz_attempts", 0) > 0:
            return values["quiz_correct"] / values["quiz_attempts"]
        return 0.0
    
    class Config:
        from_attributes = True


class CardWithProgress(CardResponse):
    """Card response including user progress"""
    user_progress: Optional[UserCardProgressResponse] = None


class StudySessionCreate(BaseModel):
    deck_id: uuid.UUID
    direction: str = Field(..., regex="^(chinese_to_english|english_to_chinese)$")


class StudySessionUpdate(BaseModel):
    cards_studied: Optional[int] = None
    correct_answers: Optional[int] = None
    session_duration: Optional[int] = None


class StudySessionResponse(BaseModel):
    id: uuid.UUID
    deck_id: uuid.UUID
    direction: str
    cards_studied: int
    correct_answers: int
    session_duration: int
    created_at: datetime
    accuracy_rate: Optional[float] = None
    
    @validator("accuracy_rate", always=True)
    def calculate_accuracy_rate(cls, v, values):
        if values.get("cards_studied", 0) > 0:
            return values["correct_answers"] / values["cards_studied"]
        return 0.0
    
    class Config:
        from_attributes = True


class CardInteractionCreate(BaseModel):
    session_id: uuid.UUID
    card_id: uuid.UUID
    interaction_type: str = Field(
        ..., 
        regex="^(flip|quiz_correct|quiz_incorrect)$"
    )
    direction: Optional[str] = Field(
        None, 
        regex="^(chinese_to_english|english_to_chinese)$"
    )
    response_time: Optional[int] = None  # milliseconds


class CardInteractionResponse(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    card_id: uuid.UUID
    interaction_type: str
    direction: Optional[str]
    response_time: Optional[int]
    created_at: datetime
    
    class Config:
        from_attributes = True


class CSVImportRequest(BaseModel):
    """Request model for CSV import"""
    deck_id: uuid.UUID
    validate_only: bool = False  # If true, only validate without importing


class CSVImportResponse(BaseModel):
    """Response model for CSV import"""
    success: bool
    imported_count: int
    errors: List[str] = []
    validated_cards: Optional[List[CardCreate]] = None


class QuizQuestionResponse(BaseModel):
    """Quiz question with multiple choice options"""
    card_id: uuid.UUID
    question: str
    options: List[str]
    correct_answer: str
    direction: str


class QuizAnswerRequest(BaseModel):
    """User's answer to a quiz question"""
    card_id: uuid.UUID
    selected_answer: str
    response_time: Optional[int] = None  # milliseconds


class QuizAnswerResponse(BaseModel):
    """Response to quiz answer"""
    correct: bool
    correct_answer: str
    explanation: Optional[str] = None


class PaginationParams(BaseModel):
    """Common pagination parameters"""
    page: int = Field(1, ge=1)
    size: int = Field(20, ge=1, le=100)
    
    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size


class SearchParams(BaseModel):
    """Common search parameters"""
    query: Optional[str] = None
    sort_by: Optional[str] = None
    sort_order: str = Field("asc", regex="^(asc|desc)$")


class PaginatedResponse(BaseModel):
    """Generic paginated response"""
    items: List[BaseModel]
    total: int
    page: int
    size: int
    pages: int
    
    @validator("pages", always=True)
    def calculate_pages(cls, v, values):
        total = values.get("total", 0)
        size = values.get("size", 1)
        return (total + size - 1) // size if total > 0 else 0


# Authentication schemas
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    username: Optional[str] = None


class LoginRequest(BaseModel):
    username: str
    password: str