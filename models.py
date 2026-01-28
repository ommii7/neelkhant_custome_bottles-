from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False) # Isme Email save hoga
    password = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(50), default='customer')
    
    # --- YE NYE COLUMNS ADD KAREIN ---
    hotel_name = db.Column(db.String(150))
    owner_name = db.Column(db.String(150))
    phone = db.Column(db.String(20))
    # ---------------------------------

class HotelOrder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    hotel_name = db.Column(db.String(100), nullable=False)
    contact_person = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    bottle_size = db.Column(db.String(20), nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='Processing')
    order_date = db.Column(db.DateTime, default=datetime.utcnow)