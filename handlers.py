import streamlit as st
from models import Lead
from database import get_database_session

def update_lead_status(lead_id, new_status):
    """API handler to update lead status"""
    try:
        session = get_database_session()
        lead = session.query(Lead).filter_by(id=lead_id).first()
        
        if lead:
            lead.status = new_status
            session.commit()
            session.close()
            return {"success": True}
        
        session.close()
        return {"success": False, "error": "Lead not found"}
    except Exception as e:
        if session:
            session.rollback()
            session.close()
        return {"success": False, "error": str(e)}
