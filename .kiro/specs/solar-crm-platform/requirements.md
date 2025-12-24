# Requirements Document

## Introduction

The Solar CRM Platform is a comprehensive customer relationship management system designed specifically for Sunrise Power's solar business. The system will act as a central backend intelligence layer that seamlessly integrates with the existing website frontend WITHOUT requiring any frontend changes or replacement. The current website UI, chatbot interface, EmailJS forms, and user experience will remain completely unchanged. The CRM system will operate invisibly in the background, automatically capturing, processing, and managing all customer interactions from multiple touchpoints. The platform will transform unstructured customer interactions into actionable business intelligence through a separate admin dashboard while preserving the exact current frontend experience for website visitors.

## Glossary

- **CRM_System**: The Django-based customer relationship management platform that operates as a backend service with admin dashboard using identical UI styling as the frontend
- **Frontend_Website**: The existing HTML/CSS/JavaScript website that remains completely unchanged
- **Admin_Dashboard**: The CRM administrative interface that uses the same design, styling, and visual elements as the Frontend_Website
- **UI_Consistency**: The requirement that both frontend and admin interfaces share identical visual design, colors, fonts, and styling
- **EmailJS_Service**: The existing email service integration used for contact and service request forms
- **Chatbot_System**: The existing Cohere AI-powered chatbot named "Surya" on the website
- **Lead_Record**: A potential customer entry in the system with contact information and interaction history
- **Customer_Record**: A converted lead who has purchased or contracted services
- **Service_Request**: A support ticket or maintenance request from existing customers
- **Solar_Calculator**: A frontend tool for estimating solar installation costs and savings
- **AMC_Contract**: Annual Maintenance Contract for installed solar systems
- **Installation_Project**: A solar installation project from quotation to completion
- **Lead_Prioritization**: Rule-based system for ranking leads based on qualification criteria and engagement data
- **Duplicate_Detection**: System capability to identify and merge similar customer records
- **API_Endpoint**: RESTful web service interface for frontend-backend communication

## Requirements

### Requirement 1

**User Story:** As a business owner, I want a centralized CRM portal with the same visual design as my website, so that I can have unified visibility into my business operations through a familiar interface.

#### Acceptance Criteria

1. WHEN the Admin_Dashboard is accessed THEN the CRM_System SHALL display a unified dashboard using identical styling, colors, fonts, and design elements as the Frontend_Website
2. WHEN a user manually enters customer data in the Admin_Dashboard THEN the interface SHALL maintain UI_Consistency with the existing website design
3. WHEN walk-in customers or phone enquiries are entered THEN the CRM_System SHALL store the interaction with appropriate source tags
4. WHEN an enquiry is converted to a customer THEN the CRM_System SHALL preserve all enquiry history and tags in the Customer_Record
5. WHEN the Frontend_Website is accessed by visitors THEN the website SHALL function exactly as it currently does with no visible changes

### Requirement 2

**User Story:** As a business owner, I want automatic email-to-lead integration, so that all EmailJS-generated emails are captured and processed without manual intervention.

#### Acceptance Criteria

1. WHEN an EmailJS email is generated from the website THEN the CRM_System SHALL automatically parse and log the email content
2. WHEN a quotation request email is received THEN the CRM_System SHALL create or update a Lead_Record with the request details
3. WHEN a service request email is received THEN the CRM_System SHALL create a Service_Request ticket in the system
4. WHEN email content is processed THEN the CRM_System SHALL store the original email content as part of the lead or service record
5. WHEN email parsing fails THEN the CRM_System SHALL log the error and notify administrators for manual review

### Requirement 3

**User Story:** As a business owner, I want chatbot interactions integrated with the CRM, so that customer conversations are automatically captured and converted to leads.

#### Acceptance Criteria

1. WHEN the Chatbot_System captures user details THEN the system SHALL submit the information to CRM_System via API_Endpoint
2. WHEN chatbot interactions indicate purchase intent THEN the CRM_System SHALL create a new Lead_Record with conversation context
3. WHEN existing customers interact with the chatbot THEN the CRM_System SHALL update their existing Customer_Record with new interaction data
4. WHEN chatbot conversation data is received THEN the CRM_System SHALL extract and store user intent and preferences
5. WHEN API_Endpoint receives chatbot data THEN the system SHALL validate and process the information targeting completion within 5 seconds under normal load

### Requirement 4

**User Story:** As a business owner, I want duplicate detection and record merging, so that I maintain clean customer data without redundant entries.

#### Acceptance Criteria

1. WHEN a new Lead_Record is created THEN the CRM_System SHALL check for existing records using email and phone number matching
2. WHEN duplicate records are detected THEN the CRM_System SHALL prevent creation and display existing record options
3. WHEN records are merged THEN the CRM_System SHALL retain complete interaction history from all merged records
4. WHEN merging is performed THEN the CRM_System SHALL maintain data integrity and preserve all timestamps
5. WHEN duplicate detection runs THEN the system SHALL target completion of the check within 3 seconds for optimal user experience

### Requirement 5

**User Story:** As a business owner, I want solar calculator integration, so that customer calculations are saved as pre-lead intelligence for better qualification.

#### Acceptance Criteria

1. WHEN a user completes the Solar_Calculator THEN the frontend SHALL submit results to CRM_System via API_Endpoint
2. WHEN calculator data is received THEN the CRM_System SHALL store the calculation results as pre-lead intelligence
3. WHEN calculator results include contact information THEN the CRM_System SHALL create a Lead_Record with calculation context
4. WHEN lead prioritization is performed THEN the CRM_System SHALL use calculator data for qualification and prioritization using rule-based algorithms
5. WHEN calculator integration fails THEN the system SHALL log the error and continue operation without disrupting user experience

### Requirement 6

**User Story:** As a business owner, I want quotation capture and conversion tracking, so that I can monitor the complete customer journey from enquiry to sale.

#### Acceptance Criteria

1. WHEN a user downloads or emails a quotation THEN the CRM_System SHALL automatically register them as a Lead_Record
2. WHEN quotation activity occurs THEN the CRM_System SHALL track the enquiry to quotation progression
3. WHEN a quotation converts to a sale THEN the CRM_System SHALL update the Lead_Record to Customer_Record status
4. WHEN conversion tracking is updated THEN the CRM_System SHALL maintain complete lifecycle history
5. WHEN quotation data is processed THEN the system SHALL associate it with the correct Lead_Record or Customer_Record

### Requirement 7

**User Story:** As a customer, I want to raise service requests through the website, so that I can get support for my solar installation.

#### Acceptance Criteria

1. WHEN a customer submits a service request form THEN the CRM_System SHALL create a Service_Request ticket
2. WHEN EmailJS processes a service request THEN the CRM_System SHALL automatically log it as a service ticket
3. WHEN a Service_Request is created THEN the CRM_System SHALL assign a unique ticket number and initial status
4. WHEN service ticket status changes THEN the CRM_System SHALL track progress until resolution
5. WHEN service requests are processed THEN the system SHALL link them to existing Customer_Record when possible

### Requirement 8

**User Story:** As a business owner, I want AMC and installation tracking, so that I can manage ongoing customer relationships and project progress.

#### Acceptance Criteria

1. WHEN an AMC_Contract is created THEN the CRM_System SHALL track validity dates and renewal schedules
2. WHEN AMC renewal is due THEN the CRM_System SHALL generate alerts and notifications
3. WHEN an Installation_Project is initiated THEN the CRM_System SHALL track progress through defined stages
4. WHEN installation milestones are reached THEN the CRM_System SHALL update project status and notify stakeholders
5. WHEN AMC or installation data is updated THEN the system SHALL maintain audit trails for all changes

### Requirement 9

**User Story:** As a business owner, I want payment and invoice tracking, so that I can monitor financial aspects of customer relationships.

#### Acceptance Criteria

1. WHEN payment milestones are defined THEN the CRM_System SHALL track payment schedules per Customer_Record
2. WHEN invoices are generated THEN the CRM_System SHALL store invoice records linked to customers
3. WHEN payments are received THEN the CRM_System SHALL update payment status and outstanding balances
4. WHEN financial data is accessed THEN the CRM_System SHALL provide accurate real-time payment information
5. WHEN payment tracking is updated THEN the system SHALL maintain complete financial audit trails

### Requirement 10

**User Story:** As a business owner, I want comprehensive dashboard with analytics using the same design as my website, so that I can have real-time visibility into business performance through a familiar and consistent interface.

#### Acceptance Criteria

1. WHEN the Admin_Dashboard is accessed THEN the CRM_System SHALL display real-time enquiry, conversion, and revenue metrics using identical UI styling as the Frontend_Website
2. WHEN analytics are generated THEN the CRM_System SHALL show service workload and performance indicators with UI_Consistency
3. WHEN dashboard data is requested THEN the CRM_System SHALL provide insights using the same color scheme, fonts, and design patterns as the website
4. WHEN performance metrics are calculated THEN the CRM_System SHALL include trending and comparative analysis with consistent visual presentation
5. WHEN the Frontend_Website operates THEN it SHALL continue functioning with identical UI/UX while data flows to the CRM_System invisibly

### Requirement 11

**User Story:** As a business owner, I want rule-based lead prioritization, so that I can focus on high-value prospects and optimize sales efforts.

#### Acceptance Criteria

1. WHEN lead prioritization is performed THEN the CRM_System SHALL analyze calculator data, chatbot engagement, and interaction history using rule-based logic
2. WHEN leads are prioritized THEN the CRM_System SHALL assign priority levels based on qualification criteria
3. WHEN prioritization algorithms run THEN the CRM_System SHALL update lead priorities automatically
4. WHEN lead priorities are calculated THEN the system SHALL provide reasoning and contributing factors
5. WHEN lead data changes THEN the CRM_System SHALL recalculate priorities as needed

### Requirement 14

**User Story:** As a business owner, I want the CRM admin interface to look and feel exactly like my website, so that I have a consistent brand experience across all business tools.

#### Acceptance Criteria

1. WHEN any Admin_Dashboard page loads THEN it SHALL use the exact same CSS styles, color scheme (#fcf8f0 background, #3D2B1F text, #fdd835 accents), and Poppins font as the Frontend_Website
2. WHEN CRM forms and inputs are displayed THEN they SHALL match the styling and design patterns used in the existing website forms
3. WHEN navigation elements are shown in the Admin_Dashboard THEN they SHALL follow the same header/navbar design and layout as the Frontend_Website
4. WHEN data tables and lists are presented THEN they SHALL use consistent styling with the website's card-based design and visual hierarchy
5. WHEN the Admin_Dashboard is accessed THEN users SHALL feel they are using an extension of the same website with identical branding and visual identity

### Requirement 12

**User Story:** As a system administrator, I want modular API-driven architecture, so that the system can scale and integrate with future requirements.

#### Acceptance Criteria

1. WHEN API_Endpoint requests are made THEN the CRM_System SHALL respond with consistent RESTful interfaces
2. WHEN system modules are deployed THEN the CRM_System SHALL maintain loose coupling between components
3. WHEN scaling is required THEN the CRM_System SHALL support horizontal scaling without architectural changes
4. WHEN new integrations are added THEN the system SHALL accommodate them through standardized API_Endpoint interfaces
5. WHEN system architecture is evaluated THEN the CRM_System SHALL demonstrate clear separation of concerns and modularity
### Requirement 13

**User Story:** As a website visitor, I want the exact same user experience as the current website, so that my interaction with Sunrise Power remains familiar and unchanged.

#### Acceptance Criteria

1. WHEN visitors access the Frontend_Website THEN they SHALL see identical HTML, CSS, and JavaScript as the current implementation
2. WHEN the Chatbot_System is used THEN it SHALL function exactly as it currently does with no visible changes to users
3. WHEN EmailJS forms are submitted THEN they SHALL work identically to current behavior from the user perspective
4. WHEN any frontend interaction occurs THEN the CRM_System SHALL capture data invisibly without affecting user experience
5. WHEN the website loads THEN all existing functionality SHALL remain completely unchanged and unaffected