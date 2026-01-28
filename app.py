import io
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from flask_mail import Mail, Message
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from xhtml2pdf import pisa  # PDF Library
from models import db, HotelOrder, User
import os
from flask import session  
import random              

app = Flask(__name__)
app.config['SECRET_KEY'] = 'sai_neelkanth_ultimate_2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///neelkanth_final.db'

# --- EMAIL CONFIGURATION ---
app.config.update(
    MAIL_SERVER='smtp.gmail.com', MAIL_PORT=465, MAIL_USE_TLS=False,MAIL_USE_SSL=True,
    MAIL_USERNAME='saineelkhant01@gmail.com',
    MAIL_PASSWORD='xgwgeonbjdqfsjcc', 
    MAIL_DEFAULT_SENDER=('Sai Neelkhant', 'saineelkhant01@gmail.com')
)

db.init_app(app)
mail = Mail(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- PRICING LOGIC ---
PRICES = {'200ml': 6.0, '500ml': 8.0, '1 Litre': 10.0}

# --- PDF GENERATOR FUNCTION ---
def create_pdf(html):
    result = io.BytesIO()
    pisa_status = pisa.CreatePDF(io.BytesIO(html.encode("utf-8")), dest=result)
    if pisa_status.err: return None
    result.seek(0)
    return result

# --- ROUTES ---

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Change: HTML ab 'email' bhej raha hai, 'username' nahi
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=email).first()
        
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('admin_dashboard' if user.role == 'admin' else 'order_page'))
        
        flash('Invalid Credentials! Please try again.')
    return render_template('login.html')

# --- MODIFIED REGISTER ROUTE (OTP Logic) ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # 1. Form se data lein
        email = request.form.get('email')
        hotel_name = request.form.get('hotel_name')
        owner_name = request.form.get('owner_name')
        phone = request.form.get('phone')
        password = request.form.get('password')

        # 2. Check karein user pehle se hai ya nahi
        if User.query.filter_by(username=email).first():
            flash('Email already registered! Please Login.')
            return redirect(url_for('register'))

        # 3. OTP Generate karein
        otp = random.randint(1000, 9999)

        # 4. Data ko TEMPORARY (Session) mein save karein (DB me nahi)
        session['temp_user'] = {
            'hotel_name': hotel_name,
            'owner_name': owner_name,
            'phone': phone,
            'email': email,
            'password': password 
        }
        session['otp'] = otp 

        # 5. Email Bhejein
        try:
            msg = Message("Verify Your Account - Sai Neelkanth", recipients=[email])
            msg.body = f"Hello,\n\nYour OTP for registration is: {otp}\n\nPlease enter this to complete your signup."
            mail.send(msg)
            flash('OTP sent to your email! Please verify.', 'info')
            return redirect(url_for('verify_otp')) # OTP page par bhej rahe hain
        except Exception as e:
            flash(f"Error sending email: {e}", 'danger')
            return redirect(url_for('register'))

    return render_template('register.html')
# --- IS CODE KO REGISTER FUNCTION KE NEECHE PASTE KAREIN ---

@app.route('/verify_otp', methods=['GET', 'POST'])
def verify_otp():
    # Check karein ki session mein data hai ya nahi
    if 'temp_user' not in session or 'otp' not in session:
        flash("Session expired. Please register again.")
        return redirect(url_for('register'))

    if request.method == 'POST':
        user_otp = request.form.get('otp')
        generated_otp = str(session['otp']) 

        if user_otp == generated_otp:
            # --- OTP MATCHED: Ab Database mein save karein ---
            data = session['temp_user']
            
            hashed = generate_password_hash(data['password'], method='pbkdf2:sha256')
            
            new_user = User(
                username=data['email'],
                password=hashed,
                hotel_name=data['hotel_name'],
                owner_name=data['owner_name'],
                phone=data['phone']
            )
            
            db.session.add(new_user)
            db.session.commit()

            # Session saaf karein
            session.pop('temp_user', None)
            session.pop('otp', None)

            flash('Registration Successful! You can now Login.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Invalid OTP! Please try again.', 'danger')

    return render_template('verify_otp.html')
@app.route('/order')
@login_required
def order_page():
    return render_template('index.html')

# --- 1. PLACE ORDER & TRACKING EMAIL ---
@app.route('/place_order', methods=['POST'])
@login_required
def place_order():
    qty = int(request.form['quantity'])
    size = request.form.get('bottle_size')
    
    # Billing Calculation
    rate = PRICES.get(size, 0)
    total = qty * rate

    # Agar user ne register kiya hai, to hum auto-fill bhi kar sakte hain, 
    # lekin abhi form se hi data le rahe hain.
    new_order = HotelOrder(
        hotel_name=request.form['hotel_name'],
        contact_person=request.form['contact_name'],
        email=current_user.username, # Logged in user ka email
        phone=request.form['phone'],
        quantity=qty,
        bottle_size=size,
        total_amount=total,
        status="Processing"
    )
    db.session.add(new_order)
    db.session.commit()

    # Tracking Email Customer ko bhejein
    try:
        msg = Message(f"Order #{new_order.id} Confirmed - Sai Neelkanth", recipients=[new_order.email])
        msg.body = f"Hello {new_order.contact_person},\n\nYour order for {qty} bottles of {size} is confirmed.\nTotal Amount: Rs. {total}\n\nWe will update you once dispatched."
        mail.send(msg)
    except: pass

    return render_template('success.html', order=new_order)

# --- 2. ADMIN DASHBOARD ---
@app.route('/admin')
@login_required
def admin_dashboard():
    if current_user.role != 'admin': return redirect(url_for('order_page'))
    
    active_orders = HotelOrder.query.filter(HotelOrder.status != 'Completed').all()
    history_orders = HotelOrder.query.filter_by(status='Completed').all()
    
    all_orders = HotelOrder.query.all()
    df = pd.DataFrame([{'amt': o.total_amount} for o in all_orders])
    total_revenue = df['amt'].sum() if not df.empty else 0
    
    return render_template('admin.html', active_orders=active_orders, history_orders=history_orders, total_revenue=total_revenue)

# --- 3. DOWNLOAD BILL ---
@app.route('/download_bill/<int:order_id>')
@login_required
def download_bill(order_id):
    if current_user.role != 'admin': return redirect(url_for('login'))
    
    order = HotelOrder.query.get_or_404(order_id)
    html = render_template('invoice.html', order=order, rate=PRICES.get(order.bottle_size), date=order.order_date.strftime('%d-%m-%Y'))
    pdf = create_pdf(html)
    
    if pdf:
        return send_file(pdf, download_name=f"Invoice_{order.id}.pdf", as_attachment=True)
    return "Error generating PDF"

# --- 4. MARK COMPLETE & SEND INVOICE ---
@app.route('/mark_complete/<int:order_id>')
@login_required
def mark_complete(order_id):
    if current_user.role != 'admin': return redirect(url_for('login'))
    
    order = HotelOrder.query.get_or_404(order_id)
    order.status = 'Completed'
    db.session.commit()
    
    html = render_template('invoice.html', order=order, rate=PRICES.get(order.bottle_size), date=order.order_date.strftime('%d-%m-%Y'))
    pdf = create_pdf(html)
    
    if pdf:
        try:
            msg = Message(f"Invoice - Order #{order.id} Completed", recipients=[order.email])
            msg.body = f"Hello {order.contact_person},\n\nYour order has been successfully delivered. Please find the attached invoice."
            msg.attach(f"Invoice_{order.id}.pdf", "application/pdf", pdf.getvalue())
            mail.send(msg)
            flash('Order Completed & Invoice Sent!')
        except Exception as e:
            flash(f'Order Saved but Email Failed: {e}')
            
    return redirect(url_for('admin_dashboard'))

# --- 5. DELETE ORDER ---
@app.route('/delete_order/<int:order_id>')
@login_required
def delete_order(order_id):
    if current_user.role != 'admin': return redirect(url_for('login'))
    
    order = HotelOrder.query.get_or_404(order_id)
    db.session.delete(order)
    db.session.commit()
    
    flash('Order deleted successfully!', 'danger')
    return redirect(url_for('admin_dashboard'))

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Admin Creation Logic
        if not User.query.filter_by(username='admin').first():
            # Admin ke paas extra fields nahi honge, wo okay hai
            db.session.add(User(username='admin', password=generate_password_hash('harish_ahire989070', method='pbkdf2:sha256'), role='admin'))
            db.session.commit()
            print(">>> Admin Created: admin / harish_ahire989070")
    app.run(debug=True)