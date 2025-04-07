from datetime import datetime
from sqlalchemy import Column, String, DateTime, Float
from database import Base

class Lead(Base):
    """Lead model for storing lead information"""
    __tablename__ = 'leads'
    
    id = Column(String(50), primary_key=True)
    name = Column(String(100), nullable=False)
    source = Column(String(50), nullable=False)
    contact_method = Column(String(50), nullable=False)
    quote_status = Column(String(50), nullable=False)
    lead_status = Column(String(20), nullable=False)
    quoted_price = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    next_followup = Column(DateTime, nullable=False)
    status = Column(String(20), default='Active', nullable=False)
    
    def __repr__(self):
        return f"<Lead {self.id}: {self.name}>"
