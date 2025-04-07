# Keith Cole Systems - Lead Management

A robust lead management application built for insurance professionals to track, manage, and optimize their leads pipeline. Built with Flask and PostgreSQL.

## Features

- **Lead Tracking**: Capture and manage leads from various sources (Media Alpha, Smart Financial, etc.)
- **Follow-up Scheduling**: Automated follow-up scheduling based on lead temperature (Hot: 3hrs, Warm: 24hrs, Cold: 72hrs)
- **Lead Status Management**: Mark leads as Active, Closed, or Lost
- **Quote Management**: Track quoted prices for home insurance coverage
- **Source Analytics**: Track closing ratios specifically for different lead sources
- **Daily Reports**: View detailed reports on lead activity and conversion rates
- **Responsive Design**: Works on desktop and mobile

## Setup

1. Ensure Python 3.7+ and PostgreSQL are installed
2. Set up the required environment variables:
   - `DATABASE_URL`: PostgreSQL connection string
   - `FLASK_SECRET_KEY`: Secret key for session management
3. Install dependencies: `pip install -r requirements.txt`
4. Run with: `gunicorn --bind 0.0.0.0:5000 main:app`

## Database Schema

The application uses a PostgreSQL database with the following schema:

```sql
CREATE TABLE leads (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    source VARCHAR(50) NOT NULL,
    contact_method VARCHAR(50) NOT NULL,
    quote_status VARCHAR(50) NOT NULL,
    lead_status VARCHAR(20) NOT NULL,
    quoted_price FLOAT,
    created_at TIMESTAMP NOT NULL,
    next_followup TIMESTAMP NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'Active'
);# Lead-Management
