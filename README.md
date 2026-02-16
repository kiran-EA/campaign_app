# Campaign Data Update Application

A web-based application to replace the manual Google Sheet workflow for entering Bluecore campaign data directly into Redshift database.

## Features

- **Insert Mode**: Add new campaign data with automatic BC_ID selection from available campaigns
- **Update Mode**: Modify existing campaign data by BC_ID
- **Auto-derivation**: Campaign Type and Source Flag automatically derived from Source_ID
- **Validation**: 
  - Prevents duplicate BC_ID entries
  - Validates Source_ID format (must start with 'ec' or 'ep')
  - Required field validation
- **User-friendly Interface**: Bootstrap-based responsive design with calendar date picker

## Prerequisites

- Docker and Docker Compose installed
- Network access to Redshift database: `ea-non-prod.cxw4zfxatj9b.us-west-1.redshift.amazonaws.com:5439`

## Quick Start

### Option 1: Using Docker Compose (Recommended)

1. **Build and run the application:**
   ```bash
   cd bluecore_campaign_app
   docker-compose up --build
   ```

2. **Access the application:**
   Open your browser and navigate to: `http://localhost:5000`

3. **Stop the application:**
   ```bash
   docker-compose down
   ```

### Option 2: Using Docker Only

1. **Build the Docker image:**
   ```bash
   cd bluecore_campaign_app
   docker build -t bluecore-campaign-app .
   ```

2. **Run the container:**
   ```bash
   docker run -d -p 5000:5000 --name bluecore_app bluecore-campaign-app
   ```

3. **Access the application:**
   Open your browser and navigate to: `http://localhost:5000`

4. **Stop the container:**
   ```bash
   docker stop bluecore_app
   docker rm bluecore_app
   ```

### Option 3: Running Locally (Without Docker)

1. **Install Python dependencies:**
   ```bash
   cd bluecore_campaign_app
   pip install -r requirements.txt
   ```

2. **Run the application:**
   ```bash
   python app.py
   ```

3. **Access the application:**
   Open your browser and navigate to: `http://localhost:5000`

## Usage

### Insert New Campaign Data

1. Click on **"Insert New Campaign"** tab (default view)
2. Select a **BC_ID** from the dropdown (only BC_IDs without campaign data are shown)
3. Fill in the required fields:
   - **Deployment Date**: Select date from calendar
   - **General Campaign Name**: Enter campaign name
   - **Email Type**: Enter email type
   - **Promotional Triggered**: Select either "TRIGGERED" or "NON_TRIGGERED"
   - **Source ID**: Enter source ID (must start with 'ec' or 'ep')
4. The system will automatically derive:
   - **Campaign Type**: 'Consumer' (if ec) or 'Pro' (if ep)
   - **Source Flag**: 'ec' or 'ep'
5. Click **"Submit Campaign Data"**

### Update Existing Campaign Data

1. Click on **"Update Existing Campaign"** tab
2. Enter the **BC_ID** you want to update
3. Click **"Load Data"** button
4. The form will populate with existing data
5. Modify any fields as needed
6. Click **"Update Campaign Data"**

## Database Schema

The application interacts with the following Redshift tables:

### Source Table: `LPDATAMART.TBL_D_ISSUE`
- Used to fetch available BC_IDs
- Query: BC_IDs where `GENERAL_CAMPAIGN_NAME IS NULL` and `SOURCE='BLUECORE'`

### Target Table: `REPORTS.TBL_BLUECORE_CAMPAIGN_DATA`
Columns:
- `BC_ID` (Primary identifier)
- `CAMPAIGN_TYPE` (Auto-derived: 'Consumer' or 'Pro')
- `SOURCE_FLAG` (Auto-derived: 'ec' or 'ep')
- `DEPLOYMENT_DATE` (Date field)
- `GENERAL_CAMPAIGN_NAME` (User input)
- `EMAIL_TYPE` (User input)
- `PROMOTIONAL_TRIGGERED` (Dropdown: TRIGGERED/NON_TRIGGERED)
- `SOURCE_ID` (User input, determines Campaign Type and Source Flag)

## Field Derivation Logic

### Campaign Type & Source Flag
- If `Source_ID` starts with **'ec'** → Campaign Type = 'Consumer', Source Flag = 'ec'
- If `Source_ID` starts with **'ep'** → Campaign Type = 'Pro', Source Flag = 'ep'

## API Endpoints

The application exposes the following REST API endpoints:

- `GET /api/get_bc_ids` - Fetch available BC_IDs
- `GET /api/get_campaign_data/<bc_id>` - Get existing campaign data
- `GET /api/check_bc_id/<bc_id>` - Check if BC_ID exists
- `POST /api/submit_campaign` - Insert new campaign data
- `PUT /api/update_campaign` - Update existing campaign data

## Configuration

Database connection settings are in `app.py`:

```python
DB_CONFIG = {
    'database': 'express',
    'host': 'ea-non-prod.cxw4zfxatj9b.us-west-1.redshift.amazonaws.com',
    'port': '5439',
    'user': 'easuper',
    'password': 'LAMRedPWD@2024'
}
```

**Security Note**: For production deployment, move credentials to environment variables:
```bash
export DB_HOST=ea-non-prod.cxw4zfxatj9b.us-west-1.redshift.amazonaws.com
export DB_PORT=5439
export DB_NAME=express
export DB_USER=easuper
export DB_PASSWORD=LAMRedPWD@2024
```

Then update `app.py`:
```python
import os

DB_CONFIG = {
    'database': os.getenv('DB_NAME'),
    'host': os.getenv('DB_HOST'),
    'port': os.getenv('DB_PORT'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD')
}
```

## Troubleshooting

### Cannot connect to Redshift
- Verify network connectivity to the Redshift cluster
- Check if security groups allow inbound connections from your IP
- Ensure database credentials are correct

### BC_IDs not loading
- Check if the query returns data: 
  ```sql
  SELECT DISTINCT ISSUE_KEY AS bc_id 
  FROM LPDATAMART.TBL_D_ISSUE 
  WHERE GENERAL_CAMPAIGN_NAME IS NULL 
  AND SOURCE='BLUECORE';
  ```
- Verify table permissions for the user

### Duplicate BC_ID error
- The BC_ID already exists in `REPORTS.TBL_BLUECORE_CAMPAIGN_DATA`
- Use **Update Mode** instead to modify existing records

## File Structure

```
bluecore_campaign_app/
├── app.py                  # Flask application (backend)
├── templates/
│   └── index.html          # Web interface (frontend)
├── requirements.txt        # Python dependencies
├── Dockerfile              # Docker configuration
├── docker-compose.yml      # Docker Compose configuration
└── README.md              # This file
```

## Technologies Used

- **Backend**: Python Flask
- **Database**: Amazon Redshift (PostgreSQL compatible)
- **Frontend**: HTML5, Bootstrap 5, JavaScript
- **Database Driver**: psycopg2
- **Containerization**: Docker

## Future Enhancements

Potential improvements for future versions:
- User authentication and role-based access control
- Audit logging (track who inserted/updated what and when)
- Bulk import from CSV/Excel
- Export campaign data to CSV
- Advanced search and filtering
- Data validation rules engine
- Email notifications on successful submissions

## Support

For issues or questions, contact your Data Engineering team.

## License

Internal use only - LampsPlus Data Engineering Team
