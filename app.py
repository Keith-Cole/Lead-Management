import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import logging
import os
from database import get_database_session
from models import Lead
from sqlalchemy import func

# Set page config
st.set_page_config(
    page_title="Keith Cole Systems - Lead Management",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Add custom CSS
st.markdown("""
<style>
    .reportview-container {
        background-color: #212529;
        color: white;
    }
    .sidebar .sidebar-content {
        background-color: #343a40;
    }
    .stButton button {
        background-color: #0d6efd;
        color: white;
    }
    .stButton button:hover {
        background-color: #0b5ed7;
    }
</style>
""", unsafe_allow_html=True)

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
LEAD_STATUSES = ["Hot", "Warm", "Cold"]
STATUS_FOLLOWUP_HOURS = {"Hot": 3, "Warm": 24, "Cold": 72}

# Helper Functions
def generate_lead_id():
    """Generate a unique lead ID based on timestamp"""
    return f"LEAD-{datetime.now().strftime('%Y%m%d%H%M%S')}"

def calculate_next_followup(lead_status):
    """Calculate next follow-up time based on lead status"""
    hours = STATUS_FOLLOWUP_HOURS.get(lead_status, 24)
    return datetime.now() + timedelta(hours=hours)

def save_lead(lead_data):
    """Save lead to database"""
    try:
        session = get_database_session()
        
        new_lead = Lead(
            id=lead_data['id'],
            name=lead_data['name'],
            source=lead_data['source'],
            contact_method=lead_data['contact_method'],
            quote_status=lead_data['quote_status'],
            lead_status=lead_data['lead_status'],
            quoted_price=lead_data.get('quoted_price'),
            created_at=lead_data['created_at'],
            next_followup=lead_data['next_followup'],
            status=lead_data['status']
        )
        
        session.add(new_lead)
        session.commit()
        session.close()
        return True
    except Exception as e:
        logger.error(f"Error saving lead: {str(e)}")
        if session:
            session.rollback()
            session.close()
        return False

def update_lead_status(lead_id, new_status):
    """Update lead status in database"""
    try:
        session = get_database_session()
        lead = session.query(Lead).filter_by(id=lead_id).first()
        
        if lead:
            lead.status = new_status
            session.commit()
            session.close()
            return True
        
        session.close()
        return False
    except Exception as e:
        logger.error(f"Error updating lead status: {str(e)}")
        if session:
            session.rollback()
            session.close()
        return False

def get_all_leads():
    """Get all leads from database"""
    try:
        session = get_database_session()
        leads = session.query(Lead).all()
        
        result = []
        for lead in leads:
            result.append({
                'id': lead.id,
                'name': lead.name,
                'source': lead.source,
                'contact_method': lead.contact_method,
                'quote_status': lead.quote_status,
                'lead_status': lead.lead_status,
                'quoted_price': lead.quoted_price,
                'created_at': lead.created_at,
                'next_followup': lead.next_followup,
                'status': lead.status
            })
        
        session.close()
        return result
    except Exception as e:
        logger.error(f"Error getting leads: {str(e)}")
        if session:
            session.close()
        return []

def get_active_leads():
    """Get all active leads from database"""
    try:
        session = get_database_session()
        leads = session.query(Lead).filter_by(status='Active').all()
        
        result = []
        for lead in leads:
            result.append({
                'id': lead.id,
                'name': lead.name,
                'source': lead.source,
                'contact_method': lead.contact_method,
                'quote_status': lead.quote_status,
                'lead_status': lead.lead_status,
                'quoted_price': lead.quoted_price,
                'created_at': lead.created_at,
                'next_followup': lead.next_followup,
                'status': lead.status
            })
        
        session.close()
        return result
    except Exception as e:
        logger.error(f"Error getting active leads: {str(e)}")
        if session:
            session.close()
        return []

def get_followup_leads():
    """Get leads that need follow-up based on next_followup datetime"""
    try:
        session = get_database_session()
        now = datetime.now()
        leads = session.query(Lead).filter_by(status='Active').filter(Lead.next_followup <= now).all()
        
        result = []
        for lead in leads:
            result.append({
                'id': lead.id,
                'name': lead.name,
                'source': lead.source,
                'contact_method': lead.contact_method,
                'quote_status': lead.quote_status,
                'lead_status': lead.lead_status,
                'quoted_price': lead.quoted_price,
                'created_at': lead.created_at,
                'next_followup': lead.next_followup,
                'status': lead.status
            })
        
        session.close()
        return result
    except Exception as e:
        logger.error(f"Error getting follow-up leads: {str(e)}")
        if session:
            session.close()
        return []

def calculate_close_ratio(source=None):
    """Calculate the close ratio from the database, optionally filtered by source"""
    try:
        session = get_database_session()
        
        # Build queries
        if source:
            total_count = session.query(func.count(Lead.id)).filter_by(source=source).scalar()
            closed_count = session.query(func.count(Lead.id)).filter_by(source=source, status='Closed').scalar()
        else:
            total_count = session.query(func.count(Lead.id)).scalar()
            closed_count = session.query(func.count(Lead.id)).filter_by(status='Closed').scalar()
        
        session.close()
        
        if total_count == 0:
            return 0
        
        return (closed_count / total_count) * 100
    except Exception as e:
        logger.error(f"Error calculating close ratio: {str(e)}")
        if session:
            session.close()
        return 0

def get_source_close_ratios():
    """Get close ratios for all important sources"""
    return {
        'overall': calculate_close_ratio(),
        'media_alpha': calculate_close_ratio('Media Alpha'),
        'smart_financial': calculate_close_ratio('Smart Financial'),
        'other': calculate_close_ratio('Other')
    }

def get_lead_counts():
    """Get counts for various lead metrics"""
    try:
        session = get_database_session()
        
        # Today's leads
        today = datetime.now()
        today_start = datetime(today.year, today.month, today.day, 0, 0, 0)
        today_end = datetime(today.year, today.month, today.day, 23, 59, 59)
        today_count = session.query(func.count(Lead.id)).filter(
            Lead.created_at >= today_start,
            Lead.created_at <= today_end
        ).scalar()
        
        # Yesterday's leads
        yesterday = today - timedelta(days=1)
        yesterday_start = datetime(yesterday.year, yesterday.month, yesterday.day, 0, 0, 0)
        yesterday_end = datetime(yesterday.year, yesterday.month, yesterday.day, 23, 59, 59)
        yesterday_count = session.query(func.count(Lead.id)).filter(
            Lead.created_at >= yesterday_start,
            Lead.created_at <= yesterday_end
        ).scalar()
        
        # Status counts
        status_counts = {}
        status_results = session.query(Lead.status, func.count(Lead.id)).group_by(Lead.status).all()
        for status, count in status_results:
            status_counts[status] = count
        
        # Lead status counts
        lead_status_counts = {}
        lead_status_results = session.query(Lead.lead_status, func.count(Lead.id)).group_by(Lead.lead_status).all()
        for status, count in lead_status_results:
            lead_status_counts[status] = count
        
        session.close()
        
        return {
            'today_count': today_count,
            'yesterday_count': yesterday_count,
            'status_counts': status_counts,
            'lead_status_counts': lead_status_counts
        }
    except Exception as e:
        logger.error(f"Error getting lead counts: {str(e)}")
        if session:
            session.close()
        return {
            'today_count': 0,
            'yesterday_count': 0,
            'status_counts': {},
            'lead_status_counts': {}
        }

# Streamlit UI Components
def display_header():
    """Display the application header"""
    st.title("Keith Cole Systems - Lead Management")
    st.markdown("---")

def display_dashboard():
    """Display the main dashboard"""
    st.header("Lead Dashboard")
    
    # Get data
    leads = get_all_leads()
    lead_count = len(leads)
    close_ratios = get_source_close_ratios()
    
    # Display KPI metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Leads", lead_count)
    with col2:
        st.metric("Overall Close Ratio", f"{close_ratios['overall']:.2f}%")
    with col3:
        st.metric("Media Alpha", f"{close_ratios['media_alpha']:.2f}%")
    with col4:
        st.metric("Smart Financial", f"{close_ratios['smart_financial']:.2f}%")
    
    # Display action buttons
    st.button("Add New Lead", on_click=lambda: st.session_state.update({"page": "add_lead"}))
    
    # Display leads table
    st.subheader("All Leads")
    if leads:
        df = pd.DataFrame(leads)
        # Format dates for display
        df['created_at'] = pd.to_datetime(df['created_at']).dt.strftime('%Y-%m-%d %H:%M')
        df['next_followup'] = pd.to_datetime(df['next_followup']).dt.strftime('%Y-%m-%d %H:%M')
        
        # Add action column for active leads
        def create_action_buttons(row):
            if row['status'] == 'Active':
                close_button = f"<a href='#' onclick=\"markLeadStatus('{row['id']}', 'Closed'); return false;\">Mark Closed</a>"
                lost_button = f"<a href='#' onclick=\"markLeadStatus('{row['id']}', 'Lost'); return false;\">Mark Lost</a>"
                return f"{close_button} | {lost_button}"
            return ""
        
        df['Actions'] = df.apply(create_action_buttons, axis=1)
        
        # Add custom styling for lead status
        def style_status(val):
            if val == 'Closed':
                return 'background-color: #28a745; color: white;'
            elif val == 'Lost':
                return 'background-color: #dc3545; color: white;'
            else:
                return 'background-color: #ffc107; color: black;'
        
        # Define columns to display
        display_columns = ['name', 'source', 'contact_method', 'lead_status', 'quote_status', 
                           'quoted_price', 'next_followup', 'status', 'Actions']
        
        st.dataframe(df[display_columns].style.applymap(style_status, subset=['status']))
        
        # JavaScript for button actions
        st.markdown("""
        <script>
        function markLeadStatus(leadId, newStatus) {
            const data = {
                leadId: leadId,
                newStatus: newStatus
            };
            
            fetch('/update_status', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data)
            }).then(() => {
                window.location.reload();
            });
        }
        </script>
        """, unsafe_allow_html=True)
    else:
        st.info("No leads found. Get started by adding a new lead!")

def display_add_lead_form():
    """Display form to add a new lead"""
    st.header("Add New Lead")
    
    # Create a form
    with st.form("lead_form"):
        name = st.text_input("Name", required=True)
        source = st.selectbox("Source", ["", "Smart Financial", "Media Alpha", "Website", 
                                        "Referral", "Social Media", "Email", "Phone", "Other"], 
                              index=0, required=True)
        contact_method = st.text_input("Contact Method", required=True)
        quote_status = st.selectbox("Quote Status", ["", "Requested", "Sent", "Negotiating", 
                                                   "Accepted", "Declined"], 
                                   index=0, required=True)
        lead_status = st.selectbox("Lead Status", ["", "Hot", "Warm", "Cold"], 
                                  index=0, required=True)
        quoted_price = st.number_input("Quoted Price ($)", min_value=0.0, value=None, 
                                      format="%.2f", help="Optional: Enter quoted price for recommended home coverage")
        
        # Submit button
        submitted = st.form_submit_button("Submit")
        
    # Handle form submission
    if submitted:
        if not name or not source or not contact_method or not quote_status or not lead_status:
            st.error("Please fill in all required fields")
        else:
            now = datetime.now()
            next_followup = calculate_next_followup(lead_status)
            
            lead_data = {
                'id': generate_lead_id(),
                'name': name,
                'source': source,
                'contact_method': contact_method,
                'quote_status': quote_status,
                'lead_status': lead_status,
                'quoted_price': quoted_price,
                'created_at': now,
                'next_followup': next_followup,
                'status': "Active"
            }
            
            success = save_lead(lead_data)
            
            if success:
                st.success("Lead added successfully!")
                st.session_state.update({"page": "dashboard"})
            else:
                st.error("Error adding lead. Please try again.")
    
    if st.button("Cancel"):
        st.session_state.update({"page": "dashboard"})

def display_reports():
    """Display the reports page"""
    st.header("Lead Reports")
    
    # Get data
    close_ratios = get_source_close_ratios()
    counts = get_lead_counts()
    
    # Display KPI metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Today's Leads", counts['today_count'])
    with col2:
        st.metric("Yesterday's Leads", counts['yesterday_count'])
    with col3:
        st.metric("Overall Close Ratio", f"{close_ratios['overall']:.2f}%")
    with col4:
        st.metric("Media Alpha", f"{close_ratios['media_alpha']:.2f}%")
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Smart Financial", f"{close_ratios['smart_financial']:.2f}%")
    with col2:
        st.metric("Other Sources", f"{close_ratios['other']:.2f}%")
    
    # Display lead status breakdown
    st.subheader("Lead Status Breakdown")
    col1, col2 = st.columns(2)
    
    with col1:
        if counts['status_counts']:
            status_df = pd.DataFrame({
                'Status': counts['status_counts'].keys(),
                'Count': counts['status_counts'].values()
            })
            st.dataframe(status_df)
            
            # Create a pie chart
            st.bar_chart(status_df.set_index('Status'))
    
    with col2:
        if counts['lead_status_counts']:
            lead_status_df = pd.DataFrame({
                'Temperature': counts['lead_status_counts'].keys(),
                'Count': counts['lead_status_counts'].values()
            })
            st.dataframe(lead_status_df)
            
            # Create a pie chart
            st.bar_chart(lead_status_df.set_index('Temperature'))
    
    if st.button("Back to Dashboard"):
        st.session_state.update({"page": "dashboard"})

# Handle page routing
def main():
    # Initialize session state for page routing
    if "page" not in st.session_state:
        st.session_state.update({"page": "dashboard"})
    
    # Display header
    display_header()
    
    # Create a sidebar navigation
    st.sidebar.title("Navigation")
    if st.sidebar.button("Dashboard"):
        st.session_state.update({"page": "dashboard"})
    if st.sidebar.button("Add Lead"):
        st.session_state.update({"page": "add_lead"})
    if st.sidebar.button("Reports"):
        st.session_state.update({"page": "reports"})
    
    # Display copyright
    st.sidebar.markdown("---")
    st.sidebar.markdown("© 2025 Keith Cole Systems LLC. All rights reserved.")
    
    # Route to the correct page
    if st.session_state.page == "dashboard":
        display_dashboard()
    elif st.session_state.page == "add_lead":
        display_add_lead_form()
    elif st.session_state.page == "reports":
        display_reports()

# Run the application
if __name__ == "__main__":
    main()
