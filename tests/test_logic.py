"""
Tests for business logic: winner identification and broker assignment.

Uses an in-memory SQLite database so tests are self-contained and fast.
"""
from decimal import Decimal

import pytest
from sqlmodel import Session, SQLModel, create_engine

from src.database.models import (
    Bid,
    BidAssignment,
    Broker,
    BrokerMapping,
    Company,
    Project,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(name="session")
def session_fixture():
    """Provide a clean in-memory SQLite session for each test."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def _make_project(session: Session, issuing_org: str = "Test Org") -> Project:
    project = Project(
        opportunity_id=f"OPP-{issuing_org[:4].upper()}-001",
        name="Test Project",
        issuing_org=issuing_org,
        url="http://example.com",
    )
    session.add(project)
    session.commit()
    session.refresh(project)
    return project


def _make_company(session: Session, name: str = "acme ltd") -> Company:
    company = Company(legal_name=name)
    session.add(company)
    session.commit()
    session.refresh(company)
    return company


def _make_bid(
    session: Session, project: Project, company: Company, amount: Decimal
) -> Bid:
    bid = Bid(project_id=project.id, company_id=company.id, amount=amount)
    session.add(bid)
    session.commit()
    session.refresh(bid)
    return bid


# ---------------------------------------------------------------------------
# Task 2: Winner Identification Tests (PROC-01)
# ---------------------------------------------------------------------------

def test_flag_winners_single_winner(session: Session):
    """The bid with the lowest amount for a project is marked is_winner=True."""
    from src.processor.winner_logic import flag_winners

    project = _make_project(session)
    c1 = _make_company(session, "company a")
    c2 = _make_company(session, "company b")
    c3 = _make_company(session, "company c")

    bid_low = _make_bid(session, project, c1, Decimal("1000.00"))
    bid_mid = _make_bid(session, project, c2, Decimal("2000.00"))
    bid_high = _make_bid(session, project, c3, Decimal("3000.00"))

    flag_winners(session, project.id)

    session.refresh(bid_low)
    session.refresh(bid_mid)
    session.refresh(bid_high)

    assert bid_low.is_winner is True
    assert bid_mid.is_winner is False
    assert bid_high.is_winner is False


def test_flag_winners_tied_lowest(session: Session):
    """When multiple bids share the lowest amount, all are marked as winners."""
    from src.processor.winner_logic import flag_winners

    project = _make_project(session)
    c1 = _make_company(session, "tie company a")
    c2 = _make_company(session, "tie company b")
    c3 = _make_company(session, "tie company c")

    bid_tied_1 = _make_bid(session, project, c1, Decimal("500.00"))
    bid_tied_2 = _make_bid(session, project, c2, Decimal("500.00"))
    bid_higher = _make_bid(session, project, c3, Decimal("750.00"))

    flag_winners(session, project.id)

    session.refresh(bid_tied_1)
    session.refresh(bid_tied_2)
    session.refresh(bid_higher)

    assert bid_tied_1.is_winner is True
    assert bid_tied_2.is_winner is True
    assert bid_higher.is_winner is False


def test_flag_winners_resets_previous(session: Session):
    """Calling flag_winners resets any stale is_winner flags before re-flagging."""
    from src.processor.winner_logic import flag_winners

    project = _make_project(session)
    c1 = _make_company(session, "reset a")
    c2 = _make_company(session, "reset b")

    bid_old_winner = _make_bid(session, project, c1, Decimal("2000.00"))
    bid_actual_winner = _make_bid(session, project, c2, Decimal("1000.00"))

    # Manually flag the wrong bid as winner to simulate stale data
    bid_old_winner.is_winner = True
    session.add(bid_old_winner)
    session.commit()

    flag_winners(session, project.id)

    session.refresh(bid_old_winner)
    session.refresh(bid_actual_winner)

    assert bid_old_winner.is_winner is False
    assert bid_actual_winner.is_winner is True


def test_flag_winners_single_bid(session: Session):
    """A project with only one bid marks that bid as winner."""
    from src.processor.winner_logic import flag_winners

    project = _make_project(session)
    c1 = _make_company(session, "solo company")
    bid = _make_bid(session, project, c1, Decimal("9999.99"))

    flag_winners(session, project.id)

    session.refresh(bid)
    assert bid.is_winner is True


# ---------------------------------------------------------------------------
# Task 3: Broker Assignment Tests (PROC-02, PROC-03)
# ---------------------------------------------------------------------------

def test_broker_assignment_single_match(session: Session):
    """A bid matching an org and threshold is assigned to the correct broker."""
    from src.processor.broker_engine import assign_brokers

    broker = Broker(name="Alice Smith", email="alice@example.com")
    session.add(broker)
    session.commit()
    session.refresh(broker)

    mapping = BrokerMapping(
        issuing_org="City of Vancouver",
        broker_id=broker.id,
        min_threshold=Decimal("0.00"),
        max_threshold=Decimal("500000.00"),
    )
    session.add(mapping)
    session.commit()

    project = _make_project(session, issuing_org="City of Vancouver")
    company = _make_company(session, "demo corp")
    bid = _make_bid(session, project, company, Decimal("100000.00"))

    assign_brokers(session, bid.id)

    assignments = session.query(BidAssignment).filter(BidAssignment.bid_id == bid.id).all()
    assert len(assignments) == 1
    assert assignments[0].broker_id == broker.id


def test_broker_assignment_no_match(session: Session):
    """A bid with no matching org/threshold creates no BidAssignment records."""
    from src.processor.broker_engine import assign_brokers

    broker = Broker(name="Bob Jones", email="bob@example.com")
    session.add(broker)
    session.commit()
    session.refresh(broker)

    # Mapping is for a different org
    mapping = BrokerMapping(
        issuing_org="City of Victoria",
        broker_id=broker.id,
        min_threshold=Decimal("0.00"),
        max_threshold=Decimal("500000.00"),
    )
    session.add(mapping)
    session.commit()

    project = _make_project(session, issuing_org="City of Vancouver")
    company = _make_company(session, "no match corp")
    bid = _make_bid(session, project, company, Decimal("100000.00"))

    assign_brokers(session, bid.id)

    assignments = session.query(BidAssignment).filter(BidAssignment.bid_id == bid.id).all()
    assert len(assignments) == 0


def test_broker_assignment_threshold_boundary(session: Session):
    """A bid outside the threshold range is not assigned to the broker."""
    from src.processor.broker_engine import assign_brokers

    broker = Broker(name="Carol White", email="carol@example.com")
    session.add(broker)
    session.commit()
    session.refresh(broker)

    mapping = BrokerMapping(
        issuing_org="City of Burnaby",
        broker_id=broker.id,
        min_threshold=Decimal("10000.00"),
        max_threshold=Decimal("50000.00"),
    )
    session.add(mapping)
    session.commit()

    project = _make_project(session, issuing_org="City of Burnaby")
    company = _make_company(session, "too expensive corp")
    bid = _make_bid(session, project, company, Decimal("100000.00"))  # above max

    assign_brokers(session, bid.id)

    assignments = session.query(BidAssignment).filter(BidAssignment.bid_id == bid.id).all()
    assert len(assignments) == 0


def test_broker_assignment_multiple_brokers(session: Session):
    """A bid can be assigned to multiple brokers if multiple mappings match."""
    from src.processor.broker_engine import assign_brokers

    broker1 = Broker(name="Dave Green", email="dave@example.com")
    broker2 = Broker(name="Eve Brown", email="eve@example.com")
    session.add(broker1)
    session.add(broker2)
    session.commit()
    session.refresh(broker1)
    session.refresh(broker2)

    for broker in [broker1, broker2]:
        mapping = BrokerMapping(
            issuing_org="City of Surrey",
            broker_id=broker.id,
            min_threshold=Decimal("0.00"),
            max_threshold=Decimal("999999.00"),
        )
        session.add(mapping)
    session.commit()

    project = _make_project(session, issuing_org="City of Surrey")
    company = _make_company(session, "multi assign corp")
    bid = _make_bid(session, project, company, Decimal("200000.00"))

    assign_brokers(session, bid.id)

    assignments = session.query(BidAssignment).filter(BidAssignment.bid_id == bid.id).all()
    assert len(assignments) == 2
    assigned_broker_ids = {a.broker_id for a in assignments}
    assert broker1.id in assigned_broker_ids
    assert broker2.id in assigned_broker_ids


def test_broker_assignment_inactive_broker_excluded(session: Session):
    """An inactive broker should not receive assignments."""
    from src.processor.broker_engine import assign_brokers

    active_broker = Broker(name="Frank Active", email="frank@example.com", is_active=True)
    inactive_broker = Broker(name="Grace Inactive", email="grace@example.com", is_active=False)
    session.add(active_broker)
    session.add(inactive_broker)
    session.commit()
    session.refresh(active_broker)
    session.refresh(inactive_broker)

    for broker in [active_broker, inactive_broker]:
        mapping = BrokerMapping(
            issuing_org="City of Richmond",
            broker_id=broker.id,
            min_threshold=Decimal("0.00"),
            max_threshold=Decimal("999999.00"),
        )
        session.add(mapping)
    session.commit()

    project = _make_project(session, issuing_org="City of Richmond")
    company = _make_company(session, "active test corp")
    bid = _make_bid(session, project, company, Decimal("50000.00"))

    assign_brokers(session, bid.id)

    assignments = session.query(BidAssignment).filter(BidAssignment.bid_id == bid.id).all()
    assert len(assignments) == 1
    assert assignments[0].broker_id == active_broker.id
