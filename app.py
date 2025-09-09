import os
import smtplib
import string
import secrets
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from werkzeug.utils import secure_filename
from sqlalchemy import create_engine, text
import logging
from datetime import datetime

# Logging setup
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

# Initialize Flask app
app = Flask(__name__, static_folder='static')

# Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///nestfix.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'supersecretkey'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'docx', 'doc', 'jpg', 'jpeg', 'png'}

# Create SQLAlchemy instance
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Database engine
engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'], connect_args={'timeout': 10})

# Executing the PRAGMA statement
with engine.connect() as connection:
    connection.execute(text("PRAGMA journal_mode=WAL;"))

# Define models
class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

    def __repr__(self):
        return f'<Customer {self.name}>'

class Professional(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    phone = db.Column(db.String(15), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    languages = db.Column(db.String(200), nullable=False)
    skills = db.Column(db.String(200), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    pincode = db.Column(db.String(10), nullable=False)
    document_filename = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(20), default="Pending")
    password = db.Column(db.String(100), nullable=True)

    def __repr__(self):
        return f'<Professional {self.name}>'
    
class Service(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(300), nullable=False)
    price = db.Column(db.Float, nullable=False)
    time_required = db.Column(db.Float, nullable=False)
    image_url = db.Column(db.String(300), nullable=True)

    def __repr__(self):
        return f'<Service {self.name}>'    

# New ServiceRequest model
class ServiceRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    service_id = db.Column(db.Integer, db.ForeignKey('service.id'), nullable=False)
    date = db.Column(db.String(50))
    time = db.Column(db.String(50))
    status = db.Column(db.String(50), default='Pending')  # 'Pending', 'In Progress', 'Completed'
    professional_id = db.Column(db.Integer, nullable=True)  # If assigned
    review = db.Column(db.String(200), nullable=True)   

# Create database tables if they do not exist
with app.app_context():
    db.create_all()

# Helper functions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def send_email(subject, recipient, body):
    sender_email = "nestfix.iitm@gmail.com"  # Replace with your actual email
    sender_password = "ycxb ozia xkht kpor"  # Replace with your actual password or App Password

    message = MIMEMultipart()
    message['From'] = sender_email
    message['To'] = recipient
    message['Subject'] = subject
    message.attach(MIMEText(body, 'plain'))

    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, recipient, message.as_string())
        print(f"Email sent to {recipient}")
    except Exception as e:
        print(f"Failed to send email: {e}")

def generate_random_password(length=10):
    return ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(length))

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        customer = Customer.query.filter_by(email=email).first()
        if customer and customer.password == password:
            session['customer_id'] = customer.id
            session['customer_name'] = customer.name
            return redirect(url_for('customer_dashboard'))
        
        admin_username = "admin@gmail.com"
        admin_password = "admin123"
        if email == admin_username and password == admin_password:
            return redirect(url_for('admin_dashboard'))
        
        professional = Professional.query.filter_by(email=email).first()
        if professional and professional.password == password:
            session['professional_id'] = professional.id
            session['professional_name'] = professional.name
            return redirect(url_for('prof_dashboard'))
        
        flash("Invalid email or password. Please try again.")
        return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        if password == confirm_password:
            existing_user = Customer.query.filter_by(email=email).first()
            if existing_user:
                flash("Email already registered. Please login or use a different email.", "danger")
                return redirect(url_for('signup'))

            new_customer = Customer(name=name, email=email, password=password)
            db.session.add(new_customer)
            db.session.commit()

            flash("Signup successful! Please log in.", "success")
            return redirect(url_for('login'))
        else:
            flash("Passwords do not match. Please try again.", "danger")
    
    return render_template('signup.html')

@app.route('/hire', methods=['GET', 'POST'])
def hire():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        age = request.form['age']
        gender = request.form['gender']
        languages = request.form['languages']
        skills = request.form['skills']
        city = request.form['city']
        pincode = request.form['pincode']
        document = request.files['document']

        existing_professional = Professional.query.filter_by(email=email).first()
        if existing_professional:
            flash("Email already registered. Please use a different email or log in if you already have an account.", "danger")
            return redirect(url_for('hire'))

        if document and allowed_file(document.filename):
            filename = secure_filename(document.filename)
            document_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            document.save(document_path)

            new_professional = Professional(
                name=name,
                email=email,
                phone=phone,
                age=int(age),
                gender=gender,
                languages=languages,
                skills=skills,
                city=city,
                pincode=pincode,
                document_filename=filename,
                status="Pending"
            )
            db.session.add(new_professional)
            db.session.commit()

            flash("Your professional account has been created and is pending verification.", "success")
            return redirect(url_for('index'))
        else:
            flash("Invalid file format. Please upload a valid document.", "danger")

    return render_template('hire.html')

@app.route('/admin')
def admin_dashboard():
    return render_template('admin_dashboard.html')

@app.route('/customer_dashboard')
def customer_dashboard():
    if 'customer_name' in session:
        customer_name = session['customer_name']
        return render_template('customer_dashboard.html', customer_name=customer_name)
    else:
        return redirect(url_for('login'))

@app.route('/prof_dashboard')
def prof_dashboard():
    if 'professional_name' in session:
        professional_name = session['professional_name']
        return render_template('prof_dashboard.html', professional_name=professional_name)
    else:
        return redirect(url_for('login'))

@app.route('/verify_profiles')
def verify_profiles():
    professionals = Professional.query.filter_by(status="Pending").all()
    return render_template('verification.html', professionals=professionals)

@app.route('/approve/<int:id>', methods=['POST'])
def approve_professional(id):
    professional = Professional.query.get(id)
    if professional:
        random_password = generate_random_password()
        professional.status = "Approved"
        professional.password = random_password
        db.session.commit()

        # Send the login details to the professional
        send_email("CYour NestFix Account Approved", professional.email, f"Your NestFix account has been approved. Your password is: {random_password}")
        
        flash(f"Professional {professional.name} has been approved.", "success")
    else:
        flash("Professional not found.", "danger")

    return redirect(url_for('verify_profiles'))

@app.route('/reject/<int:id>', methods=['POST'])
def reject_professional(id):
    professional = Professional.query.get(id)
    if professional:
        db.session.delete(professional)
        db.session.commit()
        flash(f"Professional {professional.name} has been rejected.", "danger")
    else:
        flash("Professional not found.", "danger")

    return redirect(url_for('verify_profiles'))


if __name__ == '__main__':
    app.run(debug=True)
