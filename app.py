from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
import logging
import os
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here-bluecore-2024'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=8)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Valid credentials
VALID_USERS = {
    'directmarketing': 'Lampsplus!1901',
    'easupport': 'easupport!1092'
}

def login_required(f):
    """Decorator to check if user is logged in"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            if request.method == 'GET' and request.path == '/':
                return redirect(url_for('login'))
            elif request.path.startswith('/api/'):
                return jsonify({'success': False, 'error': 'Unauthorized'}), 401
            else:
                return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.after_request
def set_cache_headers(response):
    """Set cache control headers to prevent back button access to protected pages"""
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

# Redshift connection parameters
DB_CONFIG = {
    'database': 'express',
    'host': 'ea-non-prod.cxw4zfxatj9b.us-west-1.redshift.amazonaws.com',
    'port': '5439',
    'user': 'easuper',
    'password': 'LAMRedPWD@2024'
}





@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username in VALID_USERS and VALID_USERS[username] == password:
            session.permanent = True
            session['user'] = username
            logger.info(f"User '{username}' logged in successfully")
            return redirect(url_for('index'))
        else:
            logger.warning(f"Failed login attempt for user '{username}'")
            return render_template('login.html', error='Invalid username or password')
    
    return render_template('login.html')

@app.route('/logout', methods=['GET', 'POST'])
def logout():
    """Handle user logout"""
    username = session.get('user', 'Unknown')
    session.clear()
    logger.info(f"User '{username}' logged out")
    return redirect(url_for('login'))

def get_db_connection():
    """Create and return a database connection"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        logger.error(f"Database connection error: {str(e)}")
        raise



@app.route('/')
@login_required
def index():
    """Render the main page"""
    return render_template('index.html', username=session.get('user'))

@app.route('/api/get_bc_ids', methods=['GET'])
@login_required
def get_bc_ids():
    """Fetch available BC_IDs that don't have campaign names"""
    try:
        logger.info("get_bc_ids() called")
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        query = """
            SELECT DISTINCT ISSUE_KEY AS bc_id 
            FROM LPDATAMART.TBL_D_ISSUE a
            WHERE GENERAL_CAMPAIGN_NAME IS NULL 
            AND SOURCE='BLUECORE'
            AND NOT EXISTS(
                SELECT 1 FROM REPORTS.TBL_BLUECORE_CAMPAIGN_DATA b 
                WHERE a.ISSUE_KEY = CAST(CAST(b.bc_id AS BIGINT) AS VARCHAR)
            )
            ORDER BY ISSUE_KEY
        """
        
        logger.info("Executing BC_ID query")
        cur.execute(query)
        bc_ids = cur.fetchall()
        logger.info(f"BC_IDs fetched: {len(bc_ids)} records")
        
        cur.close()
        conn.close()
        
        result = {
            'success': True,
            'data': [row['bc_id'] for row in bc_ids]
        }
        logger.info(f"Returning BC_IDs: {result['data'][:5] if result['data'] else 'None'}")
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error fetching BC_IDs: {type(e).__name__}: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/get_campaign_data/<bc_id>', methods=['GET'])
@login_required
def get_campaign_data(bc_id):
    """Fetch existing campaign data for a BC_ID"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        query = """
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
            WHERE BC_ID = %s
        """
        
        cur.execute(query, (bc_id,))
        result = cur.fetchone()
        
        cur.close()
        conn.close()
        
        if result:
            # Convert date to string for JSON serialization
            if result['deployment_date']:
                result['deployment_date'] = result['deployment_date'].strftime('%Y-%m-%d')
            
            return jsonify({
                'success': True,
                'data': dict(result)
            })
        else:
            return jsonify({
                'success': True,
                'data': None
            })
    except Exception as e:
        logger.error(f"Error fetching campaign data: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/check_bc_id/<bc_id>', methods=['GET'])
@login_required
def check_bc_id(bc_id):
    """Check if BC_ID already exists in the campaign table"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        query = """
            SELECT COUNT(*) 
            FROM REPORTS.TBL_BLUECORE_CAMPAIGN_DATA
            WHERE BC_ID = %s
        """
        
        cur.execute(query, (bc_id,))
        count = cur.fetchone()[0]
        
        cur.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'exists': count > 0
        })
    except Exception as e:
        logger.error(f"Error checking BC_ID: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/submit_campaign', methods=['POST'])
@login_required
def submit_campaign():
    """Insert new campaign data"""
    try:
        data = request.json
        
        # Extract and validate data
        bc_id = data.get('bc_id')
        deployment_date = data.get('deployment_date')
        general_campaign_name = data.get('general_campaign_name')
        email_type = data.get('email_type') or None  # Make optional
        promotional_triggered = data.get('promotional_triggered')
        source_id = data.get('source_id')
        
        # Derive CAMPAIGN_TYPE and SOURCE_FLAG from Source_ID
        source_prefix = source_id[:2].lower() if len(source_id) >= 2 else ''
        
        if source_prefix == 'ec':
            campaign_type = 'Consumer'
            source_flag = 'ec'
        elif source_prefix == 'ep':
            campaign_type = 'Pro'
            source_flag = 'ep'
        else:
            return jsonify({
                'success': False,
                'error': 'Source_ID must start with "ec" or "ep"'
            }), 400
        
        # Check if BC_ID already exists
        conn = get_db_connection()
        cur = conn.cursor()
        
        check_query = """
            SELECT COUNT(*) 
            FROM REPORTS.TBL_BLUECORE_CAMPAIGN_DATA
            WHERE BC_ID = %s
        """
        cur.execute(check_query, (bc_id,))
        if cur.fetchone()[0] > 0:
            cur.close()
            conn.close()
            return jsonify({
                'success': False,
                'error': f'BC_ID {bc_id} already exists. Please use Update function instead.'
            }), 400
        
        # Insert new record
        insert_query = """
            INSERT INTO REPORTS.TBL_BLUECORE_CAMPAIGN_DATA (
                BC_ID,
                CAMPAIGN_TYPE,
                SOURCE_FLAG,
                DEPLOYMENT_DATE,
                GENERAL_CAMPAIGN_NAME,
                EMAIL_TYPE,
                PROMOTIONAL_TRIGGERED,
                SOURCE_ID
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        cur.execute(insert_query, (
            bc_id,
            campaign_type,
            source_flag,
            deployment_date,
            general_campaign_name,
            email_type,
            promotional_triggered,
            source_id
        ))
        
        conn.commit()
        cur.close()
        conn.close()
        
        logger.info(f"Successfully inserted campaign data for BC_ID: {bc_id}")
        
        return jsonify({
            'success': True,
            'message': f'Campaign data for BC_ID {bc_id} inserted successfully!',
            'campaign_type': campaign_type,
            'source_flag': source_flag
        })
        
    except Exception as e:
        logger.error(f"Error submitting campaign: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/update_campaign', methods=['PUT'])
@login_required
def update_campaign():
    """Update existing campaign data"""
    try:
        data = request.json
        
        # Extract and validate data
        bc_id = data.get('bc_id')
        deployment_date = data.get('deployment_date')
        general_campaign_name = data.get('general_campaign_name')
        email_type = data.get('email_type') or None  # Make optional
        promotional_triggered = data.get('promotional_triggered')
        source_id = data.get('source_id')
        
        # Derive CAMPAIGN_TYPE and SOURCE_FLAG from Source_ID
        source_prefix = source_id[:2].lower() if len(source_id) >= 2 else ''
        
        if source_prefix == 'ec':
            campaign_type = 'Consumer'
            source_flag = 'ec'
        elif source_prefix == 'ep':
            campaign_type = 'Pro'
            source_flag = 'ep'
        else:
            return jsonify({
                'success': False,
                'error': 'Source_ID must start with "ec" or "ep"'
            }), 400
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Update record
        update_query = """
            UPDATE REPORTS.TBL_BLUECORE_CAMPAIGN_DATA
            SET 
                CAMPAIGN_TYPE = %s,
                SOURCE_FLAG = %s,
                DEPLOYMENT_DATE = %s,
                GENERAL_CAMPAIGN_NAME = %s,
                EMAIL_TYPE = %s,
                PROMOTIONAL_TRIGGERED = %s,
                SOURCE_ID = %s
            WHERE BC_ID = %s
        """
        
        cur.execute(update_query, (
            campaign_type,
            source_flag,
            deployment_date,
            general_campaign_name,
            email_type,
            promotional_triggered,
            source_id,
            bc_id
        ))
        
        if cur.rowcount == 0:
            conn.rollback()
            cur.close()
            conn.close()
            return jsonify({
                'success': False,
                'error': f'BC_ID {bc_id} not found in the database'
            }), 404
        
        conn.commit()
        cur.close()
        conn.close()
        
        logger.info(f"Successfully updated campaign data for BC_ID: {bc_id}")
        
        return jsonify({
            'success': True,
            'message': f'Campaign data for BC_ID {bc_id} updated successfully!',
            'campaign_type': campaign_type,
            'source_flag': source_flag
        })
        
    except Exception as e:
        logger.error(f"Error updating campaign: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ============================================
# WUNDERKIND API ENDPOINTS
# ============================================

@app.route('/api/get_wunderkind_campaign_ids', methods=['GET'])
@login_required
def get_wunderkind_campaign_ids():
    """Fetch available Campaign IDs that don't have campaign names for Wunderkind"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        query = """
            SELECT DISTINCT ISSUE_KEY AS campaign_id 
            FROM LPDATAMART.TBL_D_ISSUE 
            WHERE GENERAL_CAMPAIGN_NAME IS NULL 
            AND SOURCE='WUNDERKIND'
            ORDER BY ISSUE_KEY
        """
        
        cur.execute(query)
        campaign_ids = cur.fetchall()
        
        cur.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'data': [row['campaign_id'] for row in campaign_ids]
        })
    except Exception as e:
        logger.error(f"Error fetching Campaign IDs: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/get_wunderkind_campaign_name/<campaign_id>', methods=['GET'])
@login_required
def get_wunderkind_campaign_name(campaign_id):
    """Fetch all campaign names from source table for a Campaign ID"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Convert campaign_id to integer for proper matching
        try:
            campaign_id_int = int(campaign_id)
        except ValueError:
            campaign_id_int = campaign_id
        
        query = """
            SELECT DISTINCT CAMPAIG_NAME 
            FROM LAMPSPLUS.ARC_STG_WUNDERKIND_EMAILDATA 
            WHERE CAMPAIGN_ID = %s
        """
        
        cur.execute(query, (campaign_id_int,))
        results = cur.fetchall()
        
        logger.info(f"Query results for campaign_id {campaign_id_int}: {results}")
        
        cur.close()
        conn.close()
        
        if results and len(results) > 0:
            # Handle both possible column name cases
            campaign_names_list = []
            for row in results:
                # Try both column name variations
                name = row.get('campaig_name') or row.get('CAMPAIG_NAME')
                if name:
                    campaign_names_list.append(str(name))
            
            if campaign_names_list:
                campaign_names = ', '.join(campaign_names_list)
                logger.info(f"Returning campaign names: {campaign_names}")
                return jsonify({
                    'success': True,
                    'campaign_name': campaign_names
                })
        
        logger.warning(f"No campaign names found for campaign_id: {campaign_id_int}")
        return jsonify({
            'success': True,
            'campaign_name': None
        })
    except Exception as e:
        logger.error(f"Error fetching campaign name: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/get_wunderkind_campaign_data/<campaign_id>', methods=['GET'])
@login_required
def get_wunderkind_campaign_data(campaign_id):
    """Fetch existing campaign data for a Campaign ID"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        query = """
            SELECT 
                CAMPAIGN_ID,
                CAMPAIGN_TYPE,
                SOURCE_FLAG,
                GENERAL_CAMPAIGN_NAME,
                EMAIL_TYPE,
                PROMOTIONAL_TRIGGERED,
                SOURCE_ID
            FROM REPORTS.TBL_WUNDERKIND_CAMPAIGN_DATA
            WHERE CAMPAIGN_ID = %s
        """
        
        cur.execute(query, (campaign_id,))
        result = cur.fetchone()
        
        cur.close()
        conn.close()
        
        if result:
            return jsonify({
                'success': True,
                'data': dict(result)
            })
        else:
            return jsonify({
                'success': True,
                'data': None
            })
    except Exception as e:
        logger.error(f"Error fetching campaign data: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/check_wunderkind_campaign_id/<campaign_id>', methods=['GET'])
@login_required
def check_wunderkind_campaign_id(campaign_id):
    """Check if Campaign ID already exists in the Wunderkind campaign table"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        query = """
            SELECT COUNT(*) 
            FROM REPORTS.TBL_WUNDERKIND_CAMPAIGN_DATA
            WHERE CAMPAIGN_ID = %s
        """
        
        cur.execute(query, (campaign_id,))
        count = cur.fetchone()[0]
        
        cur.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'exists': count > 0
        })
    except Exception as e:
        logger.error(f"Error checking Campaign ID: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/submit_wunderkind_campaign', methods=['POST'])
@login_required
def submit_wunderkind_campaign():
    """Insert new Wunderkind campaign data"""
    try:
        data = request.json
        
        # Extract and validate data
        campaign_id = data.get('campaign_id')
        general_campaign_name = data.get('general_campaign_name')
        email_type = data.get('email_type') or None  # Make optional
        promotional_triggered = data.get('promotional_triggered')
        source_id = data.get('source_id')
        
        # Derive CAMPAIGN_TYPE and SOURCE_FLAG from Source_ID
        source_prefix = source_id[:2].lower() if len(source_id) >= 2 else ''
        
        if source_prefix == 'ec':
            campaign_type = 'Consumer'
            source_flag = 'ec'
        elif source_prefix == 'ep':
            campaign_type = 'Pro'
            source_flag = 'ep'
        else:
            return jsonify({
                'success': False,
                'error': 'Source_ID must start with "ec" or "ep"'
            }), 400
        
        # Check if Campaign ID already exists
        conn = get_db_connection()
        cur = conn.cursor()
        
        check_query = """
            SELECT COUNT(*) 
            FROM REPORTS.TBL_WUNDERKIND_CAMPAIGN_DATA
            WHERE CAMPAIGN_ID = %s
        """
        cur.execute(check_query, (campaign_id,))
        if cur.fetchone()[0] > 0:
            cur.close()
            conn.close()
            return jsonify({
                'success': False,
                'error': f'Campaign ID {campaign_id} already exists. Please use Update function instead.'
            }), 400
        
        # Insert new record
        insert_query = """
            INSERT INTO REPORTS.TBL_WUNDERKIND_CAMPAIGN_DATA (
                CAMPAIGN_ID,
                CAMPAIGN_TYPE,
                SOURCE_FLAG,
                GENERAL_CAMPAIGN_NAME,
                EMAIL_TYPE,
                PROMOTIONAL_TRIGGERED,
                SOURCE_ID
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        
        cur.execute(insert_query, (
            campaign_id,
            campaign_type,
            source_flag,
            general_campaign_name,
            email_type,
            promotional_triggered,
            source_id
        ))
        
        conn.commit()
        cur.close()
        conn.close()
        
        logger.info(f"Successfully inserted campaign data for Campaign ID: {campaign_id}")
        
        return jsonify({
            'success': True,
            'message': f'Campaign data for Campaign ID {campaign_id} inserted successfully!',
            'campaign_type': campaign_type,
            'source_flag': source_flag
        })
        
    except Exception as e:
        logger.error(f"Error submitting campaign: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/update_wunderkind_campaign', methods=['PUT'])
@login_required
def update_wunderkind_campaign():
    """Update existing Wunderkind campaign data"""
    try:
        data = request.json
        
        # Extract and validate data
        campaign_id = data.get('campaign_id')
        general_campaign_name = data.get('general_campaign_name')
        email_type = data.get('email_type') or None  # Make optional
        promotional_triggered = data.get('promotional_triggered')
        source_id = data.get('source_id')
        
        # Derive CAMPAIGN_TYPE and SOURCE_FLAG from Source_ID
        source_prefix = source_id[:2].lower() if len(source_id) >= 2 else ''
        
        if source_prefix == 'ec':
            campaign_type = 'Consumer'
            source_flag = 'ec'
        elif source_prefix == 'ep':
            campaign_type = 'Pro'
            source_flag = 'ep'
        else:
            return jsonify({
                'success': False,
                'error': 'Source_ID must start with "ec" or "ep"'
            }), 400
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Update record
        update_query = """
            UPDATE REPORTS.TBL_WUNDERKIND_CAMPAIGN_DATA
            SET 
                CAMPAIGN_TYPE = %s,
                SOURCE_FLAG = %s,
                GENERAL_CAMPAIGN_NAME = %s,
                EMAIL_TYPE = %s,
                PROMOTIONAL_TRIGGERED = %s,
                SOURCE_ID = %s
            WHERE CAMPAIGN_ID = %s
        """
        
        cur.execute(update_query, (
            campaign_type,
            source_flag,
            general_campaign_name,
            email_type,
            promotional_triggered,
            source_id,
            campaign_id
        ))
        
        if cur.rowcount == 0:
            conn.rollback()
            cur.close()
            conn.close()
            return jsonify({
                'success': False,
                'error': f'Campaign ID {campaign_id} not found in the database'
            }), 404
        
        conn.commit()
        cur.close()
        conn.close()
        
        logger.info(f"Successfully updated campaign data for Campaign ID: {campaign_id}")
        
        return jsonify({
            'success': True,
            'message': f'Campaign data for Campaign ID {campaign_id} updated successfully!',
            'campaign_type': campaign_type,
            'source_flag': source_flag
        })
        
    except Exception as e:
        logger.error(f"Error updating campaign: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/get_all_campaign_data', methods=['GET'])
@login_required
def get_all_campaign_data():
    """Fetch all records from REPORTS.TBL_BLUECORE_CAMPAIGN_DATA"""
    try:
        logger.info("get_all_campaign_data() called")
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        query = """
            SELECT 
                CAST(CAST(BC_ID AS BIGINT) AS VARCHAR) as bc_id,
                CAMPAIGN_TYPE as campaign_type,
                SOURCE_FLAG as source_flag,
                DEPLOYMENT_DATE as deployment_date,
                GENERAL_CAMPAIGN_NAME as general_campaign_name,
                EMAIL_TYPE as email_type,
                PROMOTIONAL_TRIGGERED as promotional_triggered,
                SOURCE_ID as source_id
            FROM REPORTS.TBL_BLUECORE_CAMPAIGN_DATA
            WHERE BC_ID IS NOT NULL
            ORDER BY BC_ID DESC
        """
        
        logger.info("Executing all campaign data query")
        cur.execute(query)
        results = cur.fetchall()
        logger.info(f"Campaign records fetched: {len(results)} records")
        
        cur.close()
        conn.close()
        
        result = {
            'success': True,
            'data': results,
            'count': len(results)
        }
        logger.info(f"Returning {len(results)} campaign records")
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error fetching campaign data: {type(e).__name__}: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/get_all_wunderkind_campaign_data', methods=['GET'])
@login_required
def get_all_wunderkind_campaign_data():
    """Fetch all records from REPORTS.TBL_WUNDERKIND_CAMPAIGN_DATA"""
    try:
        logger.info("get_all_wunderkind_campaign_data() called")
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        query = """
            SELECT
                CAST(CAST(CAMPAIGN_ID AS BIGINT) AS VARCHAR) as campaign_id,
                CAMPAIGN_TYPE as campaign_type,
                SOURCE_FLAG as source_flag,
                GENERAL_CAMPAIGN_NAME as general_campaign_name,
                EMAIL_TYPE as email_type,
                PROMOTIONAL_TRIGGERED as promotional_triggered,
                SOURCE_ID as source_id
            FROM REPORTS.TBL_WUNDERKIND_CAMPAIGN_DATA
            WHERE CAMPAIGN_ID IS NOT NULL
            ORDER BY CAMPAIGN_ID DESC
        """
        
        logger.info("Executing all Wunderkind campaign data query")
        cur.execute(query)
        results = cur.fetchall()
        logger.info(f"Wunderkind campaign records fetched: {len(results)} records")
        
        cur.close()
        conn.close()
        
        result = {
            'success': True,
            'data': results,
            'count': len(results)
        }
        logger.info(f"Returning {len(results)} Wunderkind campaign records")
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error fetching Wunderkind campaign data: {type(e).__name__}: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
