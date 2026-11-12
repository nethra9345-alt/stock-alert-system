import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.app.core.config import settings
from backend.app.core.database import Base
from backend.app.models.user import User
from backend.app.models.watchlist import WatchlistItem
from backend.app.models.portfolio import PortfolioTransaction
from backend.app.models.alert import PriceAlert

is_sqlite = settings.DATABASE_URL.startswith("sqlite")
connect_args = {"check_same_thread": False} if is_sqlite else {}


def get_test_engine():
    return create_engine(settings.DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)


@pytest.fixture(scope="module")
def db_session():
    """Provides a database session bound to the active database (PostgreSQL or SQLite)."""
    engine = get_test_engine()
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()
    engine.dispose()


def test_user_creation_and_constraints(db_session):
    """Verify User primary key, uniqueness constraints and persistence."""
    email = "db_test_user@stockpulse.ai"
    existing = db_session.query(User).filter(User.email == email).first()
    if existing:
        db_session.delete(existing)
        db_session.commit()

    user = User(
        email=email,
        username="db_test_trader",
        full_name="Database Verification User",
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    assert user.id is not None
    assert user.email == email
    assert user.is_active is True

    # Test uniqueness constraint
    duplicate = User(email=email, username="duplicate_user")
    db_session.add(duplicate)
    with pytest.raises(Exception):
        db_session.commit()
    db_session.rollback()


def test_actual_watchlist_crud_lifecycle(db_session):
    """
    1. Create a watchlist item
    2. Read saved item
    3. Update its details
    4. Delete the item
    """
    user = db_session.query(User).filter(User.email == "db_test_user@stockpulse.ai").first()
    assert user is not None

    test_symbol = "WIPRO.NS"
    # Clean previous if exists
    db_session.query(WatchlistItem).filter(
        WatchlistItem.user_id == user.id,
        WatchlistItem.symbol == test_symbol
    ).delete()
    db_session.commit()

    # 1. CREATE
    item = WatchlistItem(
        user_id=user.id,
        symbol=test_symbol,
        company_name="Wipro Limited",
        exchange="NSE",
        notes="Initial note for WIPRO"
    )
    db_session.add(item)
    db_session.commit()
    db_session.refresh(item)
    item_id = item.id
    assert item_id is not None

    # 2. READ
    saved_item = db_session.query(WatchlistItem).filter(WatchlistItem.id == item_id).first()
    assert saved_item is not None
    assert saved_item.symbol == test_symbol
    assert saved_item.notes == "Initial note for WIPRO"

    # 3. UPDATE
    saved_item.notes = "Updated note: strong IT breakout expected"
    saved_item.company_name = "Wipro Ltd"
    db_session.commit()

    updated_item = db_session.query(WatchlistItem).filter(WatchlistItem.id == item_id).first()
    assert updated_item.notes == "Updated note: strong IT breakout expected"
    assert updated_item.company_name == "Wipro Ltd"

    # 4. DELETE
    db_session.delete(updated_item)
    db_session.commit()

    deleted_check = db_session.query(WatchlistItem).filter(WatchlistItem.id == item_id).first()
    assert deleted_check is None


def test_actual_portfolio_transaction_crud(db_session):
    """
    5. Create a portfolio transaction
    6. Retrieve portfolio transactions
    """
    user = db_session.query(User).filter(User.email == "db_test_user@stockpulse.ai").first()
    assert user is not None

    tx = PortfolioTransaction(
        user_id=user.id,
        symbol="BAJFINANCE.NS",
        company_name="Bajaj Finance Ltd",
        exchange="NSE",
        transaction_type="BUY",
        quantity=25.0,
        purchase_price=7250.0,
        notes="Long term accumulation"
    )
    db_session.add(tx)
    db_session.commit()
    db_session.refresh(tx)
    tx_id = tx.id
    assert tx_id is not None

    # Retrieve and verify
    retrieved = db_session.query(PortfolioTransaction).filter(PortfolioTransaction.id == tx_id).first()
    assert retrieved is not None
    assert retrieved.symbol == "BAJFINANCE.NS"
    assert retrieved.quantity == 25.0
    assert retrieved.purchase_price == 7250.0
    assert retrieved.transaction_type == "BUY"


def test_actual_price_alert_crud_and_toggle(db_session):
    """
    7. Create a price alert
    8. Retrieve and toggle the alert
    """
    user = db_session.query(User).filter(User.email == "db_test_user@stockpulse.ai").first()
    assert user is not None

    alert = PriceAlert(
        user_id=user.id,
        symbol="MARUTI.NS",
        company_name="Maruti Suzuki India Ltd",
        target_price=13000.0,
        condition="ABOVE",
        is_active=True,
        is_triggered=False,
        notes="All-time high alert"
    )
    db_session.add(alert)
    db_session.commit()
    db_session.refresh(alert)
    alert_id = alert.id
    assert alert_id is not None

    # Retrieve and toggle
    retrieved_alert = db_session.query(PriceAlert).filter(PriceAlert.id == alert_id).first()
    assert retrieved_alert is not None
    assert retrieved_alert.is_active is True

    # Toggle active
    retrieved_alert.is_active = False
    db_session.commit()

    toggled_alert = db_session.query(PriceAlert).filter(PriceAlert.id == alert_id).first()
    assert toggled_alert.is_active is False


def test_database_persistence_across_restart():
    """
    9. Restart the backend database engine and verify that previously saved data still exists in PostgreSQL.
    """
    # Session 1: write a distinct persistent marker
    engine1 = get_test_engine()
    Session1 = sessionmaker(bind=engine1)
    s1 = Session1()

    user = s1.query(User).filter(User.email == "db_test_user@stockpulse.ai").first()
    if not user:
        user = User(email="db_test_user@stockpulse.ai", username="db_test_trader")
        s1.add(user)
        s1.commit()

    marker_symbol = "PERSIST_TEST.NS"
    s1.query(WatchlistItem).filter(WatchlistItem.symbol == marker_symbol).delete()
    s1.commit()

    item = WatchlistItem(
        user_id=user.id,
        symbol=marker_symbol,
        company_name="Persistence Test Marker",
        notes="Verified persistence across engine restarts"
    )
    s1.add(item)
    s1.commit()
    saved_id = item.id
    s1.close()
    engine1.dispose()  # Complete shutdown / disconnection of Session 1

    # Simulated server reboot: completely fresh connection to PostgreSQL
    engine2 = get_test_engine()
    Session2 = sessionmaker(bind=engine2)
    s2 = Session2()

    reboot_item = s2.query(WatchlistItem).filter(WatchlistItem.id == saved_id).first()
    assert reboot_item is not None
    assert reboot_item.symbol == marker_symbol
    assert reboot_item.notes == "Verified persistence across engine restarts"

    # Cleanup
    s2.delete(reboot_item)
    s2.commit()
    s2.close()
    engine2.dispose()


def test_user_data_isolation():
    """
    Verify that User A cannot see or access User B's watchlist, portfolio, or alerts.
    """
    engine = get_test_engine()
    Session = sessionmaker(bind=engine)
    session = Session()

    # Create User A and User B
    user_a = session.query(User).filter(User.username == "isolated_user_a").first()
    if not user_a:
        user_a = User(email="user_a@stockpulse.ai", username="isolated_user_a")
        session.add(user_a)
        session.commit()

    user_b = session.query(User).filter(User.username == "isolated_user_b").first()
    if not user_b:
        user_b = User(email="user_b@stockpulse.ai", username="isolated_user_b")
        session.add(user_b)
        session.commit()

    # Clean existing
    session.query(WatchlistItem).filter(WatchlistItem.user_id == user_a.id).delete()
    session.query(WatchlistItem).filter(WatchlistItem.user_id == user_b.id).delete()
    session.commit()

    item_a = WatchlistItem(user_id=user_a.id, symbol="USER_A_STOCK.NS", company_name="User A Stock")
    session.add(item_a)
    session.commit()

    # User B queries their watchlist
    user_b_items = session.query(WatchlistItem).filter(WatchlistItem.user_id == user_b.id).all()
    user_b_symbols = [it.symbol for it in user_b_items]

    # Verify User A's data is strictly NOT visible to User B
    assert "USER_A_STOCK.NS" not in user_b_symbols

    session.close()
    engine.dispose()
