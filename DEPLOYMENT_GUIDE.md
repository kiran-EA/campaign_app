# Deployment and Testing Guide

## Pre-Deployment Checklist

Before deploying, ensure:

1. ✅ Docker is installed and running
2. ✅ Network connectivity to Redshift cluster
3. ✅ Database credentials are valid
4. ✅ Required tables exist in Redshift:
   - `LPDATAMART.TBL_D_ISSUE`
   - `REPORTS.TBL_BLUECORE_CAMPAIGN_DATA`

## Deployment Steps

### Step 1: Transfer Files to Your Server

If testing on your local machine, navigate to the application directory:
```bash
cd /path/to/bluecore_campaign_app
```

### Step 2: Quick Start

**Option A: Using the startup script (Easiest)**
```bash
./start.sh
```

**Option B: Manual Docker Compose**
```bash
docker-compose up --build -d
```

**Option C: Without Docker (Python directly)**
```bash
pip install -r requirements.txt
python app.py
```

### Step 3: Verify Application is Running

1. Check if container is running:
   ```bash
   docker ps | grep bluecore
   ```

2. View application logs:
   ```bash
   docker-compose logs -f
   ```

3. Access the application:
   - Open browser: `http://localhost:5000`
   - You should see the Campaign Data Update page

## Testing Scenarios

### Test 1: Insert New Campaign (Happy Path)

1. Navigate to Insert Mode (default view)
2. Select a BC_ID from dropdown
3. Fill in all fields:
   - Deployment Date: Select today's date
   - General Campaign Name: "Test Campaign 001"
   - Email Type: "Promotional"
   - Promotional Triggered: "TRIGGERED"
   - Source ID: "ec12345"
4. Verify auto-derived fields show:
   - Campaign Type: Consumer
   - Source Flag: ec
5. Click Submit
6. Expected: Success message appears
7. Verify in database:
   ```sql
   SELECT * FROM REPORTS.TBL_BLUECORE_CAMPAIGN_DATA 
   WHERE BC_ID = 'your_selected_bc_id';
   ```

### Test 2: Validation - Invalid Source ID

1. Select a BC_ID
2. Fill in all fields
3. Source ID: "xx12345" (invalid - doesn't start with ec or ep)
4. Expected: Error message about Source_ID format

### Test 3: Duplicate BC_ID Prevention

1. Use a BC_ID that was already submitted
2. Fill in all fields
3. Click Submit
4. Expected: Error message stating BC_ID already exists

### Test 4: Update Existing Campaign

1. Switch to "Update Existing Campaign" tab
2. Enter a BC_ID that exists in the database
3. Click "Load Data"
4. Expected: Form populates with existing data
5. Modify General Campaign Name
6. Click "Update Campaign Data"
7. Expected: Success message
8. Verify in database that the update occurred

### Test 5: Update Non-Existent BC_ID

1. Switch to Update mode
2. Enter a BC_ID that doesn't exist
3. Click "Load Data"
4. Expected: Warning message "No campaign data found"

### Test 6: Source ID Change

1. Update mode with existing record
2. Change Source ID from "ec..." to "ep..."
3. Verify auto-derived fields update:
   - Campaign Type: Pro
   - Source Flag: ep
4. Submit update
5. Verify in database

### Test 7: Required Field Validation

1. Insert mode
2. Leave one or more required fields empty
3. Try to submit
4. Expected: Browser validation prevents submission

## Database Verification Queries

### Check Available BC_IDs
```sql
SELECT DISTINCT ISSUE_KEY AS bc_id 
FROM LPDATAMART.TBL_D_ISSUE 
WHERE GENERAL_CAMPAIGN_NAME IS NULL 
AND SOURCE='BLUECORE'
ORDER BY ISSUE_KEY
LIMIT 10;
```

### Check Inserted Data
```sql
SELECT 
    BC_ID,
    CAMPAIGN_TYPE,
    SOURCE_FLAG,
    DEPLOYMENT_DATE,
    GENERAL_CAMPAIGN_NAME,
    EMAIL_TYPE,
    PROMOTIONAL_TRIGGERED,
    SOURCE_ID
FROM REPORTS.TBL_BLUECORE_CAMPAIGN_DATA
ORDER BY DEPLOYMENT_DATE DESC
LIMIT 10;
```

### Verify No Duplicates
```sql
SELECT BC_ID, COUNT(*) as count
FROM REPORTS.TBL_BLUECORE_CAMPAIGN_DATA
GROUP BY BC_ID
HAVING COUNT(*) > 1;
```

## Troubleshooting

### Issue: Application won't start

**Solution 1: Check Docker logs**
```bash
docker-compose logs bluecore-app
```

**Solution 2: Verify port 5000 is not in use**
```bash
# Linux/Mac
lsof -i :5000

# Windows
netstat -ano | findstr :5000
```

**Solution 3: Rebuild containers**
```bash
docker-compose down
docker-compose up --build -d
```

### Issue: Cannot connect to Redshift

**Check network connectivity:**
```bash
telnet ea-non-prod.cxw4zfxatj9b.us-west-1.redshift.amazonaws.com 5439
```

**Test Python connection directly:**
```python
import psycopg2
try:
    conn = psycopg2.connect(
        database="express",
        host="ea-non-prod.cxw4zfxatj9b.us-west-1.redshift.amazonaws.com",
        port="5439",
        user="easuper",
        password="LAMRedPWD@2024"
    )
    print("✓ Connection successful!")
    conn.close()
except Exception as e:
    print(f"✗ Connection failed: {e}")
```

### Issue: BC_IDs not loading in dropdown

**Verify the query returns results:**
```sql
SELECT DISTINCT ISSUE_KEY AS bc_id 
FROM LPDATAMART.TBL_D_ISSUE 
WHERE GENERAL_CAMPAIGN_NAME IS NULL 
AND SOURCE='BLUECORE';
```

If no results, check:
- Table exists and has data
- User has SELECT permissions
- WHERE clause conditions are valid

### Issue: Insert/Update fails silently

**Check application logs:**
```bash
docker-compose logs -f bluecore-app
```

**Common causes:**
- Table doesn't exist
- User lacks INSERT/UPDATE permissions
- Column names mismatch
- Data type incompatibility

## Performance Testing

### Test with Multiple Users

Simulate multiple users by opening the application in different browser tabs/windows.

### Test with Large Datasets

If you have many BC_IDs (1000+), verify:
- Dropdown loads within 3 seconds
- No browser freeze
- Pagination might be needed

## Production Deployment Considerations

### Security Enhancements

1. **Move credentials to environment variables**
2. **Add HTTPS/SSL**
3. **Implement authentication** (LDAP/SSO)
4. **Add rate limiting**
5. **Enable CORS protection**

### Monitoring

1. **Application logs**
   ```bash
   docker-compose logs -f > app.log
   ```

2. **Database query performance**
   - Monitor query execution times
   - Add indexes if needed

3. **User activity tracking**
   - Log all inserts/updates with timestamps
   - Track which users made changes

### Backup Strategy

Before deploying:
1. Backup `REPORTS.TBL_BLUECORE_CAMPAIGN_DATA` table
2. Document rollback procedure
3. Have a restore plan ready

## Rollback Plan

If issues arise in production:

1. **Stop the application:**
   ```bash
   docker-compose down
   ```

2. **Restore previous workflow:**
   - Revert to Google Sheets temporarily
   - Investigate issues in development

3. **Database rollback (if needed):**
   ```sql
   -- Restore from backup
   DELETE FROM REPORTS.TBL_BLUECORE_CAMPAIGN_DATA 
   WHERE DEPLOYMENT_DATE >= '2026-02-11';
   
   -- Then restore from backup file
   ```

## Success Metrics

After deployment, track:
- ✅ Time saved vs Google Sheets workflow
- ✅ Number of data entry errors reduced
- ✅ User satisfaction
- ✅ System uptime/reliability

## Support Contact

For issues or questions:
- Data Engineering Team
- Application Owner: [Your Name]
- Emergency Contact: [Emergency Contact]
