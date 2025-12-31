# Solar CRM Platform

A comprehensive customer relationship management system designed specifically for Sunrise Power's solar business. The system operates as an invisible backend intelligence layer that seamlessly integrates with the existing website frontend without requiring any frontend changes.

## Project Structure

```
solar-crm-platform/
├── frontend/                 # Existing website files (unchanged)
│   ├── Index.html
│   ├── services.html
│   ├── Products.html
│   ├── Projects.html
│   ├── About.html
│   ├── styles.css
│   ├── chat.css
│   ├── chat.js
│   ├── sendemail.js
│   └── Assets/
├── backend/                  # Django CRM application
│   ├── venv/                # Virtual environment
│   ├── solar_crm/           # Django project (to be created)
│   ├── apps/                # Django applications (to be created)
│   ├── requirements.txt
│   ├── .env
│   └── .env.example
├── .kiro/                   # Kiro specifications
└── README.md
```

## Quick Start

### Prerequisites

- Python 3.8 or higher
- PostgreSQL 12 or higher
- Redis (optional, for caching and background tasks)

### Development Setup

1. **Navigate to backend directory:**
   ```bash
   cd backend
   ```

2. **Create and activate virtual environment:**
   ```bash
   # Windows
   python -m venv venv
   venv\Scripts\activate
   
   # macOS/Linux
   python -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your database credentials and settings
   ```

5. **Set up database:**
   ```bash
   # Create PostgreSQL database
   createdb solar_crm
   
   # Run migrations (after Django project is created)
   python manage.py migrate
   ```

6. **Run development server:**
   ```bash
   python manage.py runserver
   ```

## Features

- **Invisible Integration**: Captures data from existing website without changing user experience
- **Lead Management**: Automatic lead creation from chatbot, forms, and calculator interactions
- **Customer Tracking**: Complete customer lifecycle management from lead to installation
- **Service Requests**: Automated service ticket creation from EmailJS forms
- **Analytics Dashboard**: Real-time business intelligence with website-consistent styling
- **Duplicate Detection**: Intelligent record merging with confidence scoring
- **AMC Management**: Contract tracking and renewal notifications
- **Financial Tracking**: Payment milestones and invoice management

## Architecture

The system follows a dual-interface approach:
- **Frontend**: Existing website remains completely unchanged
- **Backend**: Django-based CRM with admin dashboard using identical website styling
- **Integration**: API endpoints capture data invisibly from frontend interactions

## Development Status

This project is currently in development. See `.kiro/specs/solar-crm-platform/tasks.md` for implementation progress.

## Documentation

- Requirements: `.kiro/specs/solar-crm-platform/requirements.md`
- Design: `.kiro/specs/solar-crm-platform/design.md`
- Tasks: `.kiro/specs/solar-crm-platform/tasks.md`