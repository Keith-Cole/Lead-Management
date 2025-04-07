import os
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from flask import request, redirect, render_template_string, url_for, flash
from app import app
from models import db, Lead

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
        new_lead = Lead(
            id=lead_data['id'],
            name=lead_data['name'],
            source=lead_data['source'],
            contact_method=lead_data['contact_method'],
            quote_status=lead_data['quote_status'],
            lead_status=lead_data['lead_status'],
            quoted_price=lead_data.get('quoted_price'),  # Handle quoted price
            created_at=datetime.strptime(lead_data['created_at'], '%Y-%m-%d %H:%M:%S'),
            next_followup=datetime.strptime(lead_data['next_followup'], '%Y-%m-%d %H:%M:%S'),
            status=lead_data['status']
        )
        db.session.add(new_lead)
        db.session.commit()
        return True
    except Exception as e:
        logger.error(f"Error saving lead: {str(e)}")
        db.session.rollback()
        return False

def update_lead_status(lead_id: str, new_status: str):
    """Update lead status in database"""
    try:
        lead = Lead.query.filter_by(id=lead_id).first()
        if lead:
            lead.status = new_status
            db.session.commit()
            return True
        return False
    except Exception as e:
        logger.error(f"Error updating lead status: {str(e)}")
        db.session.rollback()
        return False

def get_all_leads():
    """Get all leads from database"""
    try:
        leads = Lead.query.all()
        return [
            {
                'id': lead.id,
                'name': lead.name,
                'source': lead.source,
                'contact_method': lead.contact_method,
                'quote_status': lead.quote_status,
                'lead_status': lead.lead_status,
                'quoted_price': lead.quoted_price,  # Include quoted price
                'created_at': lead.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'next_followup': lead.next_followup.strftime('%Y-%m-%d %H:%M:%S'),
                'status': lead.status
            }
            for lead in leads
        ]
    except Exception as e:
        logger.error(f"Error getting leads: {str(e)}")
        return []

def get_active_leads():
    """Get all active leads from database"""
    try:
        leads = Lead.query.filter_by(status='Active').all()
        return [
            {
                'id': lead.id,
                'name': lead.name,
                'source': lead.source,
                'contact_method': lead.contact_method,
                'quote_status': lead.quote_status,
                'lead_status': lead.lead_status,
                'quoted_price': lead.quoted_price,  # Include quoted price
                'created_at': lead.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'next_followup': lead.next_followup.strftime('%Y-%m-%d %H:%M:%S'),
                'status': lead.status
            }
            for lead in leads
        ]
    except Exception as e:
        logger.error(f"Error getting active leads: {str(e)}")
        return []

def get_followup_leads():
    """Get leads that need follow-up based on next_followup datetime"""
    try:
        now = datetime.now()
        leads = Lead.query.filter_by(status='Active').filter(Lead.next_followup <= now).all()
        return [
            {
                'id': lead.id,
                'name': lead.name,
                'source': lead.source,
                'contact_method': lead.contact_method,
                'quote_status': lead.quote_status,
                'lead_status': lead.lead_status,
                'quoted_price': lead.quoted_price,  # Include quoted price
                'created_at': lead.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'next_followup': lead.next_followup.strftime('%Y-%m-%d %H:%M:%S'),
                'status': lead.status
            }
            for lead in leads
        ]
    except Exception as e:
        logger.error(f"Error getting follow-up leads: {str(e)}")
        return []

def calculate_close_ratio(source=None):
    """Calculate the close ratio from the database, optionally filtered by source"""
    try:
        # Base query
        if source:
            total_query = Lead.query.filter_by(source=source)
            closed_query = Lead.query.filter_by(source=source, status='Closed')
        else:
            total_query = Lead.query
            closed_query = Lead.query.filter_by(status='Closed')
        
        # Get counts
        total = total_query.count()
        if total == 0:
            return 0
        closed = closed_query.count()
        return (closed / total) * 100
    except Exception as e:
        logger.error(f"Error calculating close ratio: {str(e)}")
        return 0

def get_source_close_ratios():
    """Get close ratios for all important sources"""
    sources = {
        'overall': calculate_close_ratio(),
        'media_alpha': calculate_close_ratio('Media Alpha'),
        'smart_financial': calculate_close_ratio('Smart Financial'),
        'other': calculate_close_ratio('Other')
    }
    return sources

def generate_daily_report():
    """Generate daily report with previous day's leads and close ratio"""
    try:
        yesterday = datetime.now() - timedelta(days=1)
        yesterday_start = datetime(yesterday.year, yesterday.month, yesterday.day, 0, 0, 0)
        yesterday_end = datetime(yesterday.year, yesterday.month, yesterday.day, 23, 59, 59)
        
        # Get leads created yesterday
        yesterday_leads = Lead.query.filter(
            Lead.created_at >= yesterday_start,
            Lead.created_at <= yesterday_end
        ).all()
        
        # Calculate close ratio
        close_ratio = calculate_close_ratio()
        
        # Create report message
        report = f"Daily Report - {yesterday.strftime('%Y-%m-%d')}\n"
        report += f"New Leads: {len(yesterday_leads)}\n"
        report += f"Close Ratio: {close_ratio:.2f}%\n"
        
        # Log report details
        logger.info(report)
        
        return report
    except Exception as e:
        logger.error(f"Error generating daily report: {str(e)}")
        return f"Error generating report: {str(e)}"

def send_followup_reminders():
    """Send reminders for follow-ups"""
    leads_to_followup = get_followup_leads()
    if leads_to_followup:
        reminder_message = "Reminder: Follow up with these leads:\n"
        for lead in leads_to_followup:
            reminder_message += f"- {lead['name']} ({lead['lead_status']}): Follow up due at {lead['next_followup']}\n"
        logger.info(reminder_message)
    else:
        logger.info("No leads need follow-up at this time.")

# HTML Templates as strings
HTML_HEAD = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Keith Cole Systems - Lead Management</title>
    <link href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css" rel="stylesheet">
    <style>
        .container { padding-top: 2rem; }
        .lead-card { margin-bottom: 1rem; }
        .alert { margin-top: 1rem; }
    </style>
</head>
<body class="bg-dark text-light">
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
        <div class="container">
            <a class="navbar-brand" href="/">Keith Cole Systems - Lead Management</a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav ms-auto">
                    <li class="nav-item">
                        <a class="nav-link" href="/">Dashboard</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/add-lead">Add Lead</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/report">View Report</a>
                    </li>
                </ul>
            </div>
        </div>
    </nav>
    <div class="container">
"""

HTML_FOOTER = """
    </div>
    <footer class="mt-5 py-3 text-center text-muted">
        <div class="container">
            <small>&copy; 2025 Keith Cole Systems LLC. All rights reserved.</small>
        </div>
    </footer>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

# Routes
@app.route("/", methods=["GET"])
def index():
    """Dashboard page showing all leads"""
    leads = get_all_leads()
    close_ratios = get_source_close_ratios()
    
    return render_template_string(
        HTML_HEAD + 
        """
        <h1 class="mb-4">Lead Dashboard</h1>
        
        <div class="row mb-4">
            <div class="col-md-3">
                <div class="card bg-dark border-secondary">
                    <div class="card-body">
                        <h5 class="card-title">Total Leads</h5>
                        <h2 class="card-text">{{ lead_count }}</h2>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card bg-dark border-secondary">
                    <div class="card-body">
                        <h5 class="card-title">Overall Close Ratio</h5>
                        <h2 class="card-text">{{ close_ratios.overall|round(2) }}%</h2>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card bg-dark border-secondary">
                    <div class="card-body">
                        <h5 class="card-title">Media Alpha</h5>
                        <h2 class="card-text">{{ close_ratios.media_alpha|round(2) }}%</h2>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card bg-dark border-secondary">
                    <div class="card-body">
                        <h5 class="card-title">Smart Financial</h5>
                        <h2 class="card-text">{{ close_ratios.smart_financial|round(2) }}%</h2>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="row mb-4">
            <div class="col-md-12">
                <div class="card bg-dark border-secondary">
                    <div class="card-body">
                        <h5 class="card-title">Actions</h5>
                        <a href="/add-lead" class="btn btn-primary">Add New Lead</a>
                    </div>
                </div>
            </div>
        </div>
        
        <h3 class="mb-3">All Leads</h3>
        {% if leads %}
            {% for lead in leads %}
            <div class="card lead-card bg-dark border-secondary">
                <div class="card-body">
                    <div class="d-flex justify-content-between align-items-center">
                        <h5 class="card-title">{{ lead.name }}</h5>
                        <span class="badge {% if lead.status == 'Closed' %}bg-success{% elif lead.status == 'Lost' %}bg-danger{% else %}bg-warning{% endif %}">{{ lead.status }}</span>
                    </div>
                    <h6 class="card-subtitle mb-2 text-muted">Source: {{ lead.source }}</h6>
                    <p class="card-text">
                        <span class="badge {% if lead.lead_status == 'Hot' %}bg-danger{% elif lead.lead_status == 'Warm' %}bg-warning{% else %}bg-info{% endif %}">{{ lead.lead_status }}</span>
                        <small class="text-muted ms-2">Contact: {{ lead.contact_method }}</small>
                    </p>
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <small class="text-muted">Follow-up: {{ lead.next_followup }}</small>
                            {% if lead.quoted_price %}
                            <small class="ms-3 badge bg-info">Quoted: ${{ lead.quoted_price }}</small>
                            {% endif %}
                        </div>
                        <div class="btn-group">
                        {% if lead.status == 'Active' %}
                            <a href="/update-status/{{ lead.id }}/Closed" class="btn btn-sm btn-success">Mark Closed</a>
                            <a href="/update-status/{{ lead.id }}/Lost" class="btn btn-sm btn-danger">Mark Lost</a>
                        {% endif %}
                        </div>
                    </div>
                </div>
            </div>
            {% endfor %}
        {% else %}
            <div class="alert alert-info">No leads found. Get started by adding a new lead!</div>
        {% endif %}
        """ + HTML_FOOTER,
        leads=leads,
        lead_count=len(leads),
        close_ratios=close_ratios
    )

@app.route("/add-lead", methods=["GET"])
def add_lead_form():
    """Form to add a new lead"""
    return render_template_string(
        HTML_HEAD + 
        """
        <h1 class="mb-4">Add New Lead</h1>
        <form action="/add-lead" method="POST" class="card bg-dark border-secondary p-4">
            <div class="mb-3">
                <label for="name" class="form-label">Name</label>
                <input type="text" class="form-control bg-dark text-light" id="name" name="name" required>
            </div>
            <div class="mb-3">
                <label for="source" class="form-label">Source</label>
                <select class="form-select bg-dark text-light" id="source" name="source" required>
                    <option value="" selected disabled>Select a source</option>
                    <option value="Smart Financial">Smart Financial</option>
                    <option value="Media Alpha">Media Alpha</option>
                    <option value="Website">Website</option>
                    <option value="Referral">Referral</option>
                    <option value="Social Media">Social Media</option>
                    <option value="Email">Email</option>
                    <option value="Phone">Phone</option>
                    <option value="Other">Other</option>
                </select>
            </div>
            <div class="mb-3">
                <label for="contact_method" class="form-label">Contact Method</label>
                <input type="text" class="form-control bg-dark text-light" id="contact_method" name="contact_method" required>
            </div>
            <div class="mb-3">
                <label for="quote_status" class="form-label">Quote Status</label>
                <select class="form-select bg-dark text-light" id="quote_status" name="quote_status" required>
                    <option value="" selected disabled>Select quote status</option>
                    <option value="Requested">Requested</option>
                    <option value="Sent">Sent</option>
                    <option value="Negotiating">Negotiating</option>
                    <option value="Accepted">Accepted</option>
                    <option value="Declined">Declined</option>
                </select>
            </div>
            <div class="mb-3">
                <label for="lead_status" class="form-label">Lead Status</label>
                <select class="form-select bg-dark text-light" id="lead_status" name="lead_status" required>
                    <option value="" selected disabled>Select lead status</option>
                    <option value="Hot">Hot</option>
                    <option value="Warm">Warm</option>
                    <option value="Cold">Cold</option>
                </select>
            </div>
            <div class="mb-3">
                <label for="quoted_price" class="form-label">Quoted Price ($)</label>
                <input type="number" step="0.01" min="0" class="form-control bg-dark text-light" id="quoted_price" name="quoted_price" placeholder="Enter quoted price">
                <div class="form-text text-muted">Optional: Enter quoted price for recommended home coverage</div>
            </div>
            <button type="submit" class="btn btn-primary">Submit</button>
            <a href="/" class="btn btn-secondary mt-2">Cancel</a>
        </form>
        """ + HTML_FOOTER
    )

@app.route("/add-lead", methods=["POST"])
def create_lead():
    """Handle form submission to create a new lead"""
    # Create lead record
    now = datetime.now()
    now_str = now.strftime('%Y-%m-%d %H:%M:%S')
    next_followup = calculate_next_followup(request.form['lead_status'])
    next_followup_str = next_followup.strftime('%Y-%m-%d %H:%M:%S')
    
    # Get and validate the quoted price
    quoted_price = None
    if request.form.get('quoted_price'):
        try:
            quoted_price = float(request.form['quoted_price'])
        except ValueError:
            # If conversion fails, leave as None
            pass
    
    lead_data = {
        'id': generate_lead_id(),
        'name': request.form['name'],
        'source': request.form['source'],
        'contact_method': request.form['contact_method'],
        'quote_status': request.form['quote_status'],
        'lead_status': request.form['lead_status'],
        'quoted_price': quoted_price,  # Add quoted price
        'created_at': now_str,
        'next_followup': next_followup_str,
        'status': "Active"
    }
    
    # Save lead to database
    success = save_lead(lead_data)
    
    # Redirect to dashboard
    return redirect('/', code=303)

@app.route("/update-status/<lead_id>/<new_status>", methods=["GET"])
def update_lead_status_route(lead_id, new_status):
    """Update lead status (Closed/Lost)"""
    success = update_lead_status(lead_id, new_status)
    
    # Redirect to dashboard
    return redirect('/', code=303)

@app.route("/report", methods=["GET"])
def view_report():
    """View generated reports"""
    # Generate current report data
    close_ratios = get_source_close_ratios()
    
    # Get yesterday's leads
    yesterday = datetime.now() - timedelta(days=1)
    yesterday_start = datetime(yesterday.year, yesterday.month, yesterday.day, 0, 0, 0)
    yesterday_end = datetime(yesterday.year, yesterday.month, yesterday.day, 23, 59, 59)
    
    yesterday_leads = Lead.query.filter(
        Lead.created_at >= yesterday_start,
        Lead.created_at <= yesterday_end
    ).all()
    yesterday_count = len(yesterday_leads)
    
    # Get today's leads
    today = datetime.now()
    today_start = datetime(today.year, today.month, today.day, 0, 0, 0)
    today_end = datetime(today.year, today.month, today.day, 23, 59, 59)
    
    today_leads = Lead.query.filter(
        Lead.created_at >= today_start,
        Lead.created_at <= today_end
    ).all()
    today_count = len(today_leads)
    
    # Build status breakdown
    status_counts = {}
    lead_status_counts = {}
    
    try:
        status_result = db.session.query(Lead.status, db.func.count(Lead.id)).group_by(Lead.status).all()
        for status, count in status_result:
            status_counts[status] = count
            
        lead_status_result = db.session.query(Lead.lead_status, db.func.count(Lead.id)).group_by(Lead.lead_status).all()
        for status, count in lead_status_result:
            lead_status_counts[status] = count
    except Exception as e:
        logger.error(f"Error getting status counts: {str(e)}")
    
    return render_template_string(
        HTML_HEAD + 
        """
        <h1 class="mb-4">Lead Reports</h1>
        
        <div class="row mb-4">
            <div class="col-md-3">
                <div class="card bg-dark border-secondary">
                    <div class="card-body">
                        <h5 class="card-title">Today's Leads</h5>
                        <h2 class="card-text">{{ today_count }}</h2>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card bg-dark border-secondary">
                    <div class="card-body">
                        <h5 class="card-title">Yesterday's Leads</h5>
                        <h2 class="card-text">{{ yesterday_count }}</h2>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card bg-dark border-secondary">
                    <div class="card-body">
                        <h5 class="card-title">Overall Close Ratio</h5>
                        <h2 class="card-text">{{ close_ratios.overall|round(2) }}%</h2>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card bg-dark border-secondary">
                    <div class="card-body">
                        <h5 class="card-title">Media Alpha</h5>
                        <h2 class="card-text">{{ close_ratios.media_alpha|round(2) }}%</h2>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="row mb-4">
            <div class="col-md-6">
                <div class="card bg-dark border-secondary">
                    <div class="card-body">
                        <h5 class="card-title">Smart Financial</h5>
                        <h2 class="card-text">{{ close_ratios.smart_financial|round(2) }}%</h2>
                    </div>
                </div>
            </div>
            <div class="col-md-6">
                <div class="card bg-dark border-secondary">
                    <div class="card-body">
                        <h5 class="card-title">Other Sources</h5>
                        <h2 class="card-text">{{ close_ratios.other|round(2) }}%</h2>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="row mb-4">
            <div class="col-md-6">
                <div class="card bg-dark border-secondary">
                    <div class="card-header">Lead Status</div>
                    <div class="card-body">
                        <table class="table table-dark">
                            <thead>
                                <tr>
                                    <th>Status</th>
                                    <th>Count</th>
                                </tr>
                            </thead>
                            <tbody>
                                {% for status, count in status_counts.items() %}
                                <tr>
                                    <td>{{ status }}</td>
                                    <td>{{ count }}</td>
                                </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
            <div class="col-md-6">
                <div class="card bg-dark border-secondary">
                    <div class="card-header">Lead Temperature</div>
                    <div class="card-body">
                        <table class="table table-dark">
                            <thead>
                                <tr>
                                    <th>Temperature</th>
                                    <th>Count</th>
                                </tr>
                            </thead>
                            <tbody>
                                {% for status, count in lead_status_counts.items() %}
                                <tr>
                                    <td>{{ status }}</td>
                                    <td>{{ count }}</td>
                                </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
        """ + HTML_FOOTER,
        today_count=today_count,
        yesterday_count=yesterday_count,
        close_ratios=close_ratios,
        status_counts=status_counts,
        lead_status_counts=lead_status_counts
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
