from flask_sqlalchemy import SQLAlchemy
from uuid import uuid4
from datetime import datetime
 
db = SQLAlchemy()
 
def get_uuid():
    return uuid4().hex
 
class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.String(32), primary_key=True, unique=True, default=get_uuid)
    firstname = db.Column(db.String(20), nullable=False)
    lastname = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(150), unique=True)
    password = db.Column(db.Text, nullable=False)
    workouts = db.relationship('WorkoutSession', backref='user', lazy=True)
    
class WorkoutSession(db.Model):
    __tablename__ = "workout_sessions"
    id = db.Column(db.String(32), primary_key=True, unique=True, default=get_uuid)
    user_id = db.Column(db.String(32), db.ForeignKey('users.id'), nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    duration = db.Column(db.Integer, default=0)  # duration in seconds
    exercises = db.relationship('Exercise', backref='workout_session', lazy=True)
    
class Exercise(db.Model):
    __tablename__ = "exercises"
    id = db.Column(db.String(32), primary_key=True, unique=True, default=get_uuid)
    session_id = db.Column(db.String(32), db.ForeignKey('workout_sessions.id'), nullable=False)
    type = db.Column(db.String(50), nullable=False)  # e.g., "lifting", "squats", etc.
    reps = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)