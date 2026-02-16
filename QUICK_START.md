# 🚀 QUICK START GUIDE - Campaign Data Update App

## What This Does

Replaces your Google Sheet workflow with a web-based application that:
- ✅ Directly inserts campaign data into Redshift
- ✅ Auto-fills BC_IDs from available campaigns  
- ✅ Auto-derives Campaign Type and Source Flag from Source_ID
- ✅ Prevents duplicate entries
- ✅ Allows updates to existing records

---

## 🏃‍♂️ Get Started in 3 Steps

### Step 1: Navigate to the Application Directory
```bash
cd bluecore_campaign_app
```

### Step 2: Start the Application
```bash
./start.sh
```
*OR if you prefer manual control:*
```bash
docker-compose up --build -d
```

### Step 3: Open in Browser
```
http://localhost:5000
```

That's it! 🎉

---

## 📋 How to Use

### INSERT NEW CAMPAIGN
1. Select BC_ID from dropdown (only shows campaigns without data)
2. Pick deployment date from calendar
3. Enter campaign name, email type
4. Choose TRIGGERED or NON_TRIGGERED
5. Enter Source ID (must start with 'ec' or 'ep')
   - **ec** → Consumer campaign
   - **ep** → Pro campaign
6. Click Submit

### UPDATE EXISTING CAMPAIGN
1. Click "Update Existing Campaign" tab
2. Type in the BC_ID
3. Click "Load Data"
4. Modify any fields
5. Click "Update Campaign Data"

---

## 🔧 Field Rules

| Field | Type | Rule |
|-------|------|------|
| BC_ID | Dropdown | Auto-populated, must be unique |
| Deployment Date | Date | Calendar picker |
| General Campaign Name | Text | Any characters/numbers |
| Email Type | Text | Any characters/numbers |
| Promotional Triggered | Dropdown | TRIGGERED or NON_TRIGGERED |
| Source ID | Text | **Must start with 'ec' or 'ep'** |

### Auto-Derived Fields
- **Campaign Type** = 'Consumer' if Source_ID starts with 'ec'
- **Campaign Type** = 'Pro' if Source_ID starts with 'ep'
- **Source Flag** = 'ec' or 'ep' (first 2 characters of Source_ID)

---

## ⚠️ Important Notes

1. **No Duplicates**: You cannot insert the same BC_ID twice. Use Update mode instead.
2. **Source ID Format**: Must start with 'ec' or 'ep' or submission will fail
3. **All Fields Required**: The form won't submit if any field is empty
4. **Database**: Writes to `REPORTS.TBL_BLUECORE_CAMPAIGN_DATA`

---

## 🛑 Stop the Application
```bash
docker-compose down
```

---

## 📁 File Structure
```
bluecore_campaign_app/
├── app.py              ← Flask backend
├── templates/
│   └── index.html      ← Web interface
├── requirements.txt    ← Python dependencies
├── Dockerfile          ← Container config
├── docker-compose.yml  ← Docker orchestration
├── start.sh            ← Easy start script
├── README.md           ← Full documentation
└── DEPLOYMENT_GUIDE.md ← Testing & troubleshooting
```

---

## 🆘 Quick Troubleshooting

### App won't start?
```bash
docker ps  # Check if container is running
docker-compose logs -f  # View error logs
```

### Port 5000 already in use?
```bash
# Find what's using port 5000
lsof -i :5000

# Kill that process or change port in docker-compose.yml
```

### Can't connect to Redshift?
- Verify you're on the corporate network/VPN
- Check credentials in `app.py` line 16-21
- Test connectivity: `telnet ea-non-prod.cxw4zfxatj9b.us-west-1.redshift.amazonaws.com 5439`

### BC_IDs not loading?
Make sure this query returns data:
```sql
SELECT DISTINCT ISSUE_KEY 
FROM LPDATAMART.TBL_D_ISSUE 
WHERE GENERAL_CAMPAIGN_NAME IS NULL 
AND SOURCE='BLUECORE';
```

---

## 📚 Need More Help?

- **Full Documentation**: See `README.md`
- **Testing Guide**: See `DEPLOYMENT_GUIDE.md`
- **API Details**: Backend exposes REST APIs at `/api/*` endpoints

---

## 🎯 Benefits Over Google Sheets

| Google Sheets | This App |
|---------------|----------|
| Manual entry → Manual sync → Redshift | Direct entry → Instant Redshift |
| Risk of typos in BC_ID | Dropdown prevents typos |
| Manual CAMPAIGN_TYPE/SOURCE_FLAG | Auto-derived from Source_ID |
| Possible duplicate entries | Validation prevents duplicates |
| No update capability | Easy update mode |
| Requires Google account access | Local web app, no login needed |

---

**Created by**: Data Engineering Team  
**Version**: 1.0  
**Date**: February 2026
