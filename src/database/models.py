from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional
from pydantic import field_validator
from sqlmodel import Field, Relationship, SQLModel

class Project(SQLModel, table=True):
    __tablename__ = "project"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    opportunity_id: str = Field(unique=True, index=True)
    name: str
    issuing_org: str
    date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    url: str
    
    bids: List["Bid"] = Relationship(back_populates="project")

class Company(SQLModel, table=True):
    __tablename__ = "company"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    legal_name: str = Field(unique=True, index=True)
    google_found: Optional[bool] = Field(default=None)
    website_found: Optional[str] = Field(default=None)
    linkedin_found: Optional[str] = Field(default=None)
    
    bids: List["Bid"] = Relationship(back_populates="company")

    def __init__(self, **data):
        if "legal_name" in data and isinstance(data["legal_name"], str):
            data["legal_name"] = data["legal_name"].lower().strip()
        super().__init__(**data)

class Bid(SQLModel, table=True):
    __tablename__ = "bid"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    amount: Decimal = Field(default=Decimal("0.0"), decimal_places=2)
    is_winner: bool = Field(default=False)
    
    project_id: int = Field(foreign_key="project.id")
    company_id: int = Field(foreign_key="company.id")
    
    project: Project = Relationship(back_populates="bids")
    company: Company = Relationship(back_populates="bids")

class SystemError(SQLModel, table=True):
    __tablename__ = "system_error"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    source: str
    error_message: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    resolved: bool = Field(default=False)
