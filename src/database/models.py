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

    assignments: List["BidAssignment"] = Relationship(back_populates="bid")

class Broker(SQLModel, table=True):
    """Represents an insurance broker who receives daily leads."""
    __tablename__ = "broker"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    email: str = Field(unique=True, index=True)
    is_active: bool = Field(default=True)

    mappings: List["BrokerMapping"] = Relationship(back_populates="broker")
    assignments: List["BidAssignment"] = Relationship(back_populates="broker")

class BrokerMapping(SQLModel, table=True):
    """Maps an issuing organization and bid size range to a broker.

    A broker receives bids from a given issuing_org when the bid amount
    falls within [min_threshold, max_threshold].
    """
    __tablename__ = "brokermapping"

    id: Optional[int] = Field(default=None, primary_key=True)
    issuing_org: str = Field(index=True)
    broker_id: int = Field(foreign_key="broker.id", index=True)
    min_threshold: Decimal = Field(default=Decimal("0.00"), decimal_places=2)
    max_threshold: Decimal = Field(default=Decimal("999999999.99"), decimal_places=2)

    broker: "Broker" = Relationship(back_populates="mappings")

class BidAssignment(SQLModel, table=True):
    """Link table connecting a Bid to the Broker(s) it was assigned to.

    Allows a many-to-many relationship between Bids and Brokers while
    preserving the assignment audit trail.
    """
    __tablename__ = "bidassignment"

    id: Optional[int] = Field(default=None, primary_key=True)
    bid_id: int = Field(foreign_key="bid.id", index=True)
    broker_id: int = Field(foreign_key="broker.id", index=True)

    bid: "Bid" = Relationship(back_populates="assignments")
    broker: "Broker" = Relationship(back_populates="assignments")

class SystemError(SQLModel, table=True):
    __tablename__ = "system_error"

    id: Optional[int] = Field(default=None, primary_key=True)
    source: str
    error_message: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    resolved: bool = Field(default=False)
