import os
import sqlalchemy as sa
from sqlalchemy.orm import declarative_base, sessionmaker

# Define base class for SQLAlchemy models
Base = declarative_base()

def get_database_session():
    """Get a database session to interact with the database"""
    # Get database URL from environment variable or use SQLite as fallback for local development
    database_url = os.environ.get("DATABASE_URL", "sqlite:///leads.db")
    
    # Create SQLAlchemy engine
    engine = sa.create_engine(database_url, pool_recycle=300, pool_pre_ping=True)
    
    # Create tables if they don't exist
    Base.metadata.create_all(engine)
    
    # Create session factory
    Session = sessionmaker(bind=engine)
    
    # Return a session
    return Session()
