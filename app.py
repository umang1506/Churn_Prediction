import os
import io
import secrets
import uuid
import pandas as pd
import numpy as np
import joblib
import hashlib
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, g
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'churn_shield_secret_key_2024')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///churnshield.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'uploads')
app.config['SCANNED_FOLDER'] = os.path.join(os.getcwd(), 'scanned_datasets')

# Ensure directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['SCANNED_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'
CORS(app)

# --- MODELS ---

class Organization(db.Model):
    """Multi-tenant: Each company (Flipkart, Amazon, Zomato) is an Organization."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)  # e.g. "Flipkart", "Zomato"
    slug = db.Column(db.String(60), unique=True, nullable=False)  # e.g. "flipkart"
    industry = db.Column(db.String(60))  # e-commerce, food-delivery, etc.
    plan = db.Column(db.String(20), default='free')  # free, pro, enterprise
    api_calls_limit = db.Column(db.Integer, default=1000)  # monthly limit
    api_calls_used = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    users = db.relationship('User', backref='organization', lazy=True)
    api_keys = db.relationship('ApiKey', backref='organization', lazy=True)

class ApiKey(db.Model):
    """API keys for programmatic access by company admins."""
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(64), unique=True, nullable=False, default=lambda: 'cs_' + secrets.token_hex(24))
    name = db.Column(db.String(100), default='Default Key')  # label
    org_id = db.Column(db.Integer, db.ForeignKey('organization.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_used = db.Column(db.DateTime)

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone_number = db.Column(db.String(20), nullable=True)
    password = db.Column(db.String(60), nullable=False)
    org_id = db.Column(db.Integer, db.ForeignKey('organization.id'), nullable=True)
    role = db.Column(db.String(20), default='admin')  # admin, member
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    datasets = db.relationship('Dataset', backref='owner', lazy=True)

class Dataset(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    file_hash = db.Column(db.String(64), nullable=False) # SHA256
    row_count = db.Column(db.Integer)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    predictions = db.relationship('Prediction', backref='source_dataset', lazy=True)

class Prediction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    dataset_id = db.Column(db.Integer, db.ForeignKey('dataset.id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    customer_id = db.Column(db.String(50))
    churn_probability = db.Column(db.Float)
    risk_level = db.Column(db.String(20)) # High, Medium, Low
    loyalty_score = db.Column(db.Float)
    revenue_loss = db.Column(db.Float)
    retention_prob = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class OrderLink(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    url = db.Column(db.String(500), nullable=False)
    platform = db.Column(db.String(50))
    status = db.Column(db.String(20), default='pending') # pending, scanned, failed
    scanned_at = db.Column(db.DateTime)

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(100))
    message = db.Column(db.Text)
    type = db.Column(db.String(20)) # success, info, warning
    read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- ROUTES ---

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        password = request.form.get('password')
        
        user_exists = User.query.filter_by(email=email).first()
        if user_exists:
            flash('Email already registered.', 'danger')
            return redirect(url_for('signup'))
        
        hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
        new_user = User(full_name=full_name, email=email, password=hashed_pw)
        db.session.add(new_user)
        db.session.commit()
        flash('Account created! You can now log in.', 'success')
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False
        
        user = User.query.filter_by(email=email).first()
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user, remember=remember)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        else:
            flash('Login unsuccessful. Please check email and password.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    # Dynamic calculations for the logged-in user
    user_datasets = Dataset.query.filter_by(user_id=current_user.id).order_by(Dataset.uploaded_at.desc()).all()
    recent_predictions = Prediction.query.filter_by(user_id=current_user.id).order_by(Prediction.created_at.desc()).limit(10).all()
    
    # Calculate stats
    total_customers = db.session.query(db.func.count(db.distinct(Prediction.customer_id))).filter(Prediction.user_id == current_user.id).scalar() or 0
    high_risk_count = Prediction.query.filter_by(user_id=current_user.id, risk_level='High').count()
    revenue_at_risk = db.session.query(db.func.sum(Prediction.revenue_loss)).filter(Prediction.user_id == current_user.id, Prediction.risk_level == 'High').scalar() or 0
    
    return render_template('dashboard.html', 
                          datasets=user_datasets, 
                          predictions=recent_predictions,
                          total_customers=total_customers,
                          high_risk_count=high_risk_count,
                          revenue_at_risk=revenue_at_risk)

@app.route('/analytics')
@login_required
def analytics():
    # Fetch all predictions for the user
    all_preds = Prediction.query.filter_by(user_id=current_user.id).all()
    
    # Calculate distributions
    high = Prediction.query.filter_by(user_id=current_user.id, risk_level='High').count()
    medium = Prediction.query.filter_by(user_id=current_user.id, risk_level='Medium').count()
    low = Prediction.query.filter_by(user_id=current_user.id, risk_level='Low').count()
    total = len(all_preds) or 1 # Avoid division by zero
    
    # Timeline data (count by day)
    from sqlalchemy import func
    timeline_query = db.session.query(
        func.date(Prediction.created_at).label('date'),
        func.count(Prediction.id).label('count')
    ).filter(Prediction.user_id == current_user.id).group_by(func.date(Prediction.created_at)).all()
    
    timeline = [{'date': str(t.date), 'count': t.count} for t in timeline_query]
    
    return render_template('analytics.html', 
                          high=high, medium=medium, low=low, total=total,
                          high_pct=round((high/total)*100, 1),
                          med_pct=round((medium/total)*100, 1),
                          low_pct=round((low/total)*100, 1),
                          timeline=timeline)

@app.route('/customers')
@login_required
def customers():
    all_customers = Prediction.query.filter_by(user_id=current_user.id).order_by(Prediction.created_at.desc()).all()
    return render_template('customers.html', customers=all_customers)

@app.route('/settings')
@login_required
def settings():
    return render_template('settings.html')

@app.route('/api/upload-dataset', methods=['POST'])
@login_required
def upload_dataset():
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No selected file'}), 400
    
    if file:
        filename = file.filename
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Calculate row count and SHA256
        if filename.endswith('.csv'):
            df = pd.read_csv(filepath)
        elif filename.endswith(('.xls', '.xlsx')):
            df = pd.read_excel(filepath)
        else:
            return jsonify({'success': False, 'error': 'Unsupported file format'}), 400
            
        with open(filepath, 'rb') as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()
            
        new_dataset = Dataset(
            user_id=current_user.id,
            filename=filename,
            file_path=filepath,
            file_hash=file_hash,
            row_count=len(df)
        )
        db.session.add(new_dataset)
        
        # Log Notification
        notif = Notification(user_id=current_user.id, title="Dataset Uploaded", message=f"File {filename} ({len(df)} profiles) ready for prediction.", type="success")
        db.session.add(notif)
        db.session.commit()
        return jsonify({'success': True, 'dataset_id': new_dataset.id})

@app.route('/api/delete-dataset/<int:dataset_id>', methods=['DELETE'])
@login_required
def delete_dataset(dataset_id):
    try:
        dataset = Dataset.query.get(dataset_id)
        if not dataset or dataset.user_id != current_user.id:
            return jsonify({'success': False, 'error': 'Unauthorized or dataset not found'}), 403
        
        # Delete associated predictions first
        Prediction.query.filter_by(dataset_id=dataset_id).delete()
        
        # Delete the dataset itself
        db.session.delete(dataset)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Dataset and associated predictions deleted.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/notifications', methods=['GET'])
@login_required
def get_notifications():
    notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).limit(10).all()
    notif_list = [{
        'id': n.id,
        'title': n.title,
        'message': n.message,
        'type': n.type,
        'created_at': n.created_at.strftime('%H:%M'),
        'read': n.read
    } for n in notifications]
    return jsonify(notif_list)

@app.route('/api/mark-read', methods=['POST'])
@login_required
def mark_read():
    Notification.query.filter_by(user_id=current_user.id, read=False).update({'read': True})
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/reset-account', methods=['POST'])
@login_required
def reset_account():
    try:
        # Delete all predictions, datasets, and links for this user
        Prediction.query.filter_by(user_id=current_user.id).delete()
        Dataset.query.filter_by(user_id=current_user.id).delete()
        OrderLink.query.filter_by(user_id=current_user.id).delete()
        Notification.query.filter_by(user_id=current_user.id).delete()
        
        # Add fresh start notification
        notif = Notification(user_id=current_user.id, title="Account Reset", message="All records cleared successfully.", type="info")
        db.session.add(notif)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Account data reset successfully!'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/scan-link', methods=['POST'])
@login_required
def scan_link():
    from order_scanner import OrderScanner
    url = request.json.get('url')
    if not url:
        return jsonify({'success': False, 'error': 'No URL provided'}), 400
    
    scanner = OrderScanner(app.config['SCANNED_FOLDER'])
    result = scanner.scan_complete_orders(url, user_id=current_user.id)
    
    if result['success']:
        # Create dataset entry
        with open(result['file_path'], 'rb') as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()
            
        new_dataset = Dataset(
            user_id=current_user.id,
            filename=os.path.basename(result['file_path']),
            file_path=result['file_path'],
            file_hash=file_hash,
            row_count=result['row_count']
        )
        db.session.add(new_dataset)
        db.session.commit() # Commit to get ID
        
        # --- AUTOMATIC PREDICTION (BUYHATKE STYLE) ---
        # Call the internal predict logic here for instant results
        # Re-using logic from Predict endpoint
        try:
            model_path = os.path.join(os.getcwd(), 'models', 'churn_model.pkl')
            model_data = joblib.load(model_path)
            model = model_data['model']
            feature_names = model_data.get('feature_names')
            
            df = pd.read_csv(result['file_path'])
            from feature_extractor import FeatureExtractor
            extractor = FeatureExtractor()
            features = extractor.extract_features(df, seed=int(file_hash[:8], 16))
            X = features[feature_names]
            probs = model.predict_proba(X)[:, 1]
            
            # Save results
            for cid, prob in zip(features.index, probs):
                risk = "High" if prob > 0.7 else ("Medium" if prob > 0.4 else "Low")
                pred = Prediction(
                    dataset_id=new_dataset.id,
                    user_id=current_user.id,
                    customer_id=str(cid),
                    churn_probability=float(prob),
                    risk_level=risk,
                    loyalty_score=float(1 - prob),
                    revenue_loss=float(prob * 100),
                    retention_prob=float(1 - prob)
                )
                db.session.add(pred)
            db.session.commit()
            result['prediction_count'] = len(features)
            
            # Log Notification (BuyHatke style scan+predict)
            notif = Notification(user_id=current_user.id, title=f"{result['platform']} Scan Complete", message=f"Extracted {result['row_count']} orders and predicted churn for {len(features)} customers instantly.", type="success")
            db.session.add(notif)
            db.session.commit()
            
        except Exception as pred_err:
            print(f"AUTO-PREDICT ERROR: {pred_err}")
            
    return jsonify(result)

@app.route('/api/predict', methods=['POST'])
@login_required
def predict():
    try:
        dataset_id = request.json.get('dataset_id')
        dataset = Dataset.query.get(dataset_id)
        if not dataset or dataset.user_id != current_user.id:
            return jsonify({'success': False, 'error': 'Unauthorized or invalid dataset'}), 403
        
        # Load model
        model_path = os.path.join(os.getcwd(), 'models', 'churn_model.pkl')
        if not os.path.exists(model_path):
            return jsonify({'success': False, 'error': 'Model weights not found. Run train_model.py first.'}), 500
            
        model_data = joblib.load(model_path)
        model = model_data['model']
        feature_names_expected = model_data.get('feature_names', ['recency', 'frequency', 'total_spend', 'avg_order_value', 'lifetime', 'cancellation_ratio', 'return_ratio', 'total_quantity'])
        
        # Load data and extract features
        from feature_extractor import FeatureExtractor
        if dataset.file_path.endswith('.csv'):
            df = pd.read_csv(dataset.file_path)
        else:
            df = pd.read_excel(dataset.file_path)
            
        extractor = FeatureExtractor()
        # Derive a stable seed from the file hash for consistent synthetic data if needed
        hash_seed = int(dataset.file_hash[:8], 16)
        features = extractor.extract_features(df, seed=hash_seed)
        
        # Align features with model expectations
        X = features[feature_names_expected]
        
        # Predict using stable trained model
        probs = model.predict_proba(X)[:, 1]
        
        # Clear previous predictions for this dataset to avoid duplicates
        Prediction.query.filter_by(dataset_id=dataset.id).delete()
        
        # Use bulk insert for high performance with large datasets
        prediction_objects = []
        results = []
        for cid, prob in zip(features.index, probs):
            risk = "High" if prob > 0.7 else ("Medium" if prob > 0.4 else "Low")
            pred = Prediction(
                dataset_id=dataset.id,
                user_id=current_user.id,
                customer_id=str(cid),
                churn_probability=float(prob),
                risk_level=risk,
                loyalty_score=float(1 - prob),
                revenue_loss=float(prob * 100),
                retention_prob=float(1 - prob)
            )
            prediction_objects.append(pred)
            results.append({
                'customer_id': str(cid),
                'churn_probability': float(prob),
                'risk_level': risk
            })
            
        db.session.bulk_save_objects(prediction_objects)
        db.session.commit()
        
        # Log Notification
        notif = Notification(user_id=current_user.id, title="Churn Cycle Finished", message=f"Prediction successful for {len(results)} profiles via manual dataset run.", type="info")
        db.session.add(notif)
        db.session.commit()
        
        return jsonify({'success': True, 'predictions': results})
        
    except Exception as e:
        db.session.rollback()
        import traceback
        error_msg = str(e)
        print(f"PREDICTION ERROR: {error_msg}\n{traceback.format_exc()}")
        return jsonify({'success': False, 'error': f"Prediction failed: {error_msg}. Check data format!"}), 500

@app.route('/api/send-email', methods=['POST'])
@login_required
def send_email():
    from email_service import EmailService
    data = request.json
    es = EmailService()
    
    result = es.send_retention_email(
        from_email=data.get('from_email', os.getenv('SMTP_USER', 'noreply@churnshield.ai')),
        to_email=data.get('to_email'),
        subject=data.get('subject'),
        message=data.get('message')
    )
    
    if result['success']:
        notif = Notification(user_id=current_user.id, title="Campaign Sent", message=f"Retention email successfully delivered to {data.get('to_email')}.", type="success")
        db.session.add(notif)
        db.session.commit()
        
    return jsonify(result)

@app.route('/api/update-settings', methods=['POST'])
@login_required
def update_settings():
    try:
        email = request.form.get('email')
        phone = request.form.get('phone')
        password = request.form.get('password')
        
        # Check if email is already used by someone else
        if email != current_user.email:
            existing = User.query.filter_by(email=email).first()
            if existing:
                return jsonify({'success': False, 'error': 'Email already in use.'}), 400
            current_user.email = email
            
        current_user.phone_number = phone
        if password:
            current_user.password = bcrypt.generate_password_hash(password).decode('utf-8')
            
        db.session.commit()
        return jsonify({'success': True, 'message': 'Profile updated successfully!'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/retention')
@login_required
def retention():
    return render_template('retention.html')

# =====================================================
# PUBLIC SaaS API (v1) — For Flipkart, Amazon, Zomato
# =====================================================

def require_api_key(f):
    """Decorator: authenticate via X-API-Key header."""
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            return jsonify({'error': 'Missing X-API-Key header'}), 401
        key_obj = ApiKey.query.filter_by(key=api_key, is_active=True).first()
        if not key_obj:
            return jsonify({'error': 'Invalid or revoked API key'}), 401
        org = Organization.query.get(key_obj.org_id)
        if org and org.api_calls_used >= org.api_calls_limit:
            return jsonify({'error': 'Monthly API call limit reached. Upgrade your plan.'}), 429
        # Track usage
        key_obj.last_used = datetime.utcnow()
        if org:
            org.api_calls_used += 1
        db.session.commit()
        g.api_key = key_obj
        g.api_org = org
        g.api_user_id = key_obj.user_id
        return f(*args, **kwargs)
    return decorated

@app.route('/api/v1/predict', methods=['POST'])
@require_api_key
def api_v1_predict_file():
    """
    PUBLIC API: Upload a CSV/Excel file and get churn predictions.
    Usage:
        curl -X POST https://churnshield.ai/api/v1/predict \
            -H "X-API-Key: cs_your_api_key_here" \
            -F "file=@customers.csv"
    """
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded. Send a CSV/Excel as form-data with key "file".'}), 400
        file = request.files['file']
        filename = file.filename
        
        # Read the file
        if filename.endswith('.csv'):
            df = pd.read_csv(file)
        elif filename.endswith(('.xls', '.xlsx')):
            df = pd.read_excel(file)
        else:
            return jsonify({'error': 'Unsupported format. Send .csv, .xls, or .xlsx'}), 400
        
        results = _run_prediction_on_df(df, g.api_user_id)
        return jsonify({
            'success': True,
            'organization': g.api_org.name if g.api_org else 'Unknown',
            'total_customers': len(results),
            'predictions': results
        })
    except Exception as e:
        return jsonify({'error': f'Prediction failed: {str(e)}'}), 500

@app.route('/api/v1/predict-json', methods=['POST'])
@require_api_key
def api_v1_predict_json():
    """
    PUBLIC API: Send customer data as JSON and get churn predictions.
    Usage:
        curl -X POST https://churnshield.ai/api/v1/predict-json \
            -H "X-API-Key: cs_your_api_key_here" \
            -H "Content-Type: application/json" \
            -d '{"customers": [{"customer_id": "C001", "tenure": 12, "total_charges": 500}, ...]}'
    """
    try:
        data = request.json
        if not data or 'customers' not in data:
            return jsonify({'error': 'Send JSON with a "customers" array.'}), 400
        
        df = pd.DataFrame(data['customers'])
        results = _run_prediction_on_df(df, g.api_user_id)
        return jsonify({
            'success': True,
            'organization': g.api_org.name if g.api_org else 'Unknown',
            'total_customers': len(results),
            'predictions': results
        })
    except Exception as e:
        return jsonify({'error': f'Prediction failed: {str(e)}'}), 500

@app.route('/api/v1/keys', methods=['GET'])
@login_required
def api_v1_list_keys():
    """List all API keys for the current user's organization."""
    keys = ApiKey.query.filter_by(user_id=current_user.id).all()
    return jsonify([{
        'id': k.id,
        'key': k.key[:12] + '...' + k.key[-4:],  # masked
        'name': k.name,
        'is_active': k.is_active,
        'created_at': k.created_at.strftime('%Y-%m-%d'),
        'last_used': k.last_used.strftime('%Y-%m-%d %H:%M') if k.last_used else 'Never'
    } for k in keys])

@app.route('/api/v1/keys/create', methods=['POST'])
@login_required
def api_v1_create_key():
    """Generate a new API key for the current user."""
    # Auto-create org if user doesn't have one
    if not current_user.org_id:
        org_name = request.json.get('organization', current_user.full_name + "'s Org")
        slug = org_name.lower().replace(' ', '-').replace("'", '')[:60]
        existing = Organization.query.filter_by(slug=slug).first()
        if existing:
            org = existing
        else:
            org = Organization(name=org_name, slug=slug)
            db.session.add(org)
            db.session.flush()
        current_user.org_id = org.id
    
    new_key = ApiKey(
        name=request.json.get('name', 'API Key'),
        org_id=current_user.org_id,
        user_id=current_user.id
    )
    db.session.add(new_key)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'api_key': new_key.key,  # Show FULL key only on creation
        'message': 'Save this key securely. It will not be shown again in full.'
    })

@app.route('/api/v1/keys/<int:key_id>/revoke', methods=['POST'])
@login_required
def api_v1_revoke_key(key_id):
    """Revoke an API key."""
    key = ApiKey.query.get(key_id)
    if not key or key.user_id != current_user.id:
        return jsonify({'error': 'Key not found'}), 404
    key.is_active = False
    db.session.commit()
    return jsonify({'success': True, 'message': 'API key revoked.'})

@app.route('/api/v1/usage', methods=['GET'])
@require_api_key
def api_v1_usage():
    """Check API usage for the current organization."""
    org = g.api_org
    return jsonify({
        'organization': org.name,
        'plan': org.plan,
        'api_calls_used': org.api_calls_used,
        'api_calls_limit': org.api_calls_limit,
        'remaining': org.api_calls_limit - org.api_calls_used
    })

def _run_prediction_on_df(df, user_id):
    """Core prediction logic shared by dashboard and public API."""
    from feature_extractor import FeatureExtractor
    
    model_path = os.path.join(os.getcwd(), 'models', 'churn_model.pkl')
    if not os.path.exists(model_path):
        raise Exception('Model not trained yet.')
    
    model_data = joblib.load(model_path)
    model = model_data['model']
    feature_names = model_data.get('feature_names', [
        'recency', 'frequency', 'total_spend', 'avg_order_value',
        'lifetime', 'cancellation_ratio', 'return_ratio', 'total_quantity'
    ])
    
    extractor = FeatureExtractor()
    features = extractor.extract_features(df, seed=42)
    X = features[feature_names]
    probs = model.predict_proba(X)[:, 1]
    
    results = []
    for cid, prob in zip(features.index, probs):
        risk = 'High' if prob > 0.7 else ('Medium' if prob > 0.4 else 'Low')
        results.append({
            'customer_id': str(cid),
            'churn_probability': round(float(prob), 4),
            'risk_level': risk,
            'loyalty_score': round(float(1 - prob), 4),
            'revenue_at_risk': round(float(prob * 100), 2),
            'recommended_action': {
                'High': '20% discount + priority support',
                'Medium': '10% coupon + engagement email',
                'Low': 'Loyalty points reminder'
            }[risk]
        })
    return results

# --- API DOCS PAGE ---
@app.route('/api/docs')
def api_docs():
    return render_template('api_docs.html')



# --- INITIALIZE DATABASE ---
def init_db():
    with app.app_context():
        db.create_all()
        # Safe migrations
        from sqlalchemy import text, inspect
        inspector = inspect(db.engine)
        user_cols = [c['name'] for c in inspector.get_columns('user')]
        if 'phone_number' not in user_cols:
            print('MIGRATION: Adding phone_number')
            db.session.execute(text('ALTER TABLE user ADD COLUMN phone_number VARCHAR(20)'))
            db.session.commit()
        if 'org_id' not in user_cols:
            print('MIGRATION: Adding org_id')
            db.session.execute(text('ALTER TABLE user ADD COLUMN org_id INTEGER'))
            db.session.commit()
        if 'role' not in user_cols:
            print('MIGRATION: Adding role')
            db.session.execute(text("ALTER TABLE user ADD COLUMN role VARCHAR(20) DEFAULT 'admin'"))
            db.session.commit()

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)
