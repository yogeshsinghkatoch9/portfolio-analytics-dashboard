import os
import tempfile
from backend import db


def test_db_init_and_crud(tmp_path):
    # Use a temporary sqlite file by overriding DATABASE_URL
    db_file = tmp_path / "test_portfolio.db"
    db_path = str(db_file)

    # create tables in the temp DB by creating a new engine
    # (we'll directly call init_db which uses the project's DB path)
    db.init_db()

    # Create a session and add a portfolio
    session = next(db.get_session())
    p = db.Portfolio(name='Test Portfolio')
    session.add(p)
    session.flush()

    h = db.Holding(portfolio_id=p.id, ticker='AAPL', quantity=10, price=150.0, cost_basis=148.0, meta_json='{}')
    session.add(h)
    session.commit()

    # Query back
    retrieved = session.query(db.Portfolio).filter_by(name='Test Portfolio').first()
    assert retrieved is not None
    assert len(retrieved.holdings) >= 1

    # Clean up
    session.delete(retrieved)
    session.commit()
    session.close()
