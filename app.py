from flask import Flask, request, jsonify, session, Response
from models import db, User, WorkoutSession, Exercise
from flask_bcrypt import Bcrypt
import threading
from flask_cors import CORS
from datetime import datetime, timedelta
import json

# Initialize Flask app
app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = 'cairocoders-ednalan'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///UsersDataBase.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'None'
app.config['SESSION_COOKIE_SECURE'] = True  # Use in production with HTTPS

# Initialize extensions
bcrypt = Bcrypt(app)
CORS(app, supports_credentials=True)
db.init_app(app)

# Create database tables
with app.app_context():
    db.create_all()

stop_event = threading.Event()

# Routes
@app.route("/")
def hello_world():
    return "<p>Hello, World!</p>"

@app.route("/signup", methods=["POST"])
def signup():
    firstname = request.json["firstname"]
    lastname = request.json["lastname"]
    email = request.json["email"]
    password = request.json["password"]

    user_exists = User.query.filter_by(email=email).first() is not None

    if user_exists:
        return jsonify({"error": "Email already exists"}), 409
    
    hashed_password = bcrypt.generate_password_hash(password)
    new_user = User(firstname=firstname, lastname=lastname, email=email, password=hashed_password)
    db.session.add(new_user)
    db.session.commit()

    session["user_id"] = new_user.id

    return jsonify({
        "id": new_user.id,
        "firstname": new_user.firstname,
        "lastname": new_user.lastname,
        "email": new_user.email,
    })

@app.route("/login", methods=["POST"])
def login_user():
    email = request.json["email"]
    password = request.json["password"]

    user = User.query.filter_by(email=email).first()

    if user is None:
        return jsonify({"error": "Unauthorized Access"}), 401
    
    if not bcrypt.check_password_hash(user.password, password):
        return jsonify({"error": "Unauthorized"}), 401

    session["user_id"] = user.id
    
    return jsonify({
        "id": user.id,
        "firstname": user.firstname,
        "lastname": user.lastname,
        "email": user.email,
    })

@app.route("/logout", methods=["POST"])
def logout_user():
    session.pop("user_id", None)
    return jsonify({"message": "Logged out successfully"})

@app.route("/check-auth", methods=["GET"])
def check_auth():
    user_id = session.get("user_id")
    
    if not user_id:
        return jsonify({"authenticated": False}), 401
        
    user = User.query.filter_by(id=user_id).first()
    
    if not user:
        return jsonify({"authenticated": False}), 401
        
    return jsonify({
        "authenticated": True,
        "user": {
            "id": user.id,
            "firstname": user.firstname,
            "lastname": user.lastname,
            "email": user.email
        }
    })

# Workout Session Endpoints
@app.route("/start-workout", methods=["POST"])
def start_workout():
    user_id = session.get("user_id")
    
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
    
    new_session = WorkoutSession(user_id=user_id)
    db.session.add(new_session)
    db.session.commit()
    
    return jsonify({
        "session_id": new_session.id,
        "start_time": new_session.date.isoformat()
    })

@app.route("/end-workout", methods=["POST"])
def end_workout():
    user_id = session.get("user_id")
    
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
    
    session_id = request.json.get("session_id")
    duration = request.json.get("duration", 0)
    
    workout_session = WorkoutSession.query.filter_by(id=session_id, user_id=user_id).first()
    
    if not workout_session:
        return jsonify({"error": "Session not found"}), 404
    
    workout_session.duration = duration
    db.session.commit()
    
    return jsonify({
        "message": "Workout session ended successfully",
        "session_id": workout_session.id,
        "duration": workout_session.duration
    })

@app.route("/save-exercise", methods=["POST"])
def save_exercise():
    user_id = session.get("user_id")
    
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
    
    session_id = request.json.get("session_id")
    exercise_type = request.json.get("type")
    reps = request.json.get("reps", 0)
    
    # Verify the session belongs to the user
    workout_session = WorkoutSession.query.filter_by(id=session_id, user_id=user_id).first()
    
    if not workout_session:
        return jsonify({"error": "Session not found"}), 404
    
    new_exercise = Exercise(
        session_id=session_id,
        type=exercise_type,
        reps=reps
    )
    
    db.session.add(new_exercise)
    db.session.commit()
    
    return jsonify({
        "exercise_id": new_exercise.id,
        "type": new_exercise.type,
        "reps": new_exercise.reps,
        "created_at": new_exercise.created_at.isoformat()
    })

@app.route("/user-progress", methods=["GET"])
def get_user_progress():
    user_id = session.get("user_id")
    
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
    
    # Get all user workout sessions with exercises
    workout_sessions = WorkoutSession.query.filter_by(user_id=user_id).all()
    
    result = []
    for ws in workout_sessions:
        exercises = Exercise.query.filter_by(session_id=ws.id).all()
        exercise_data = [
            {
                "id": ex.id,
                "type": ex.type,
                "reps": ex.reps,
                "created_at": ex.created_at.isoformat()
            } for ex in exercises
        ]
        
        result.append({
            "session_id": ws.id,
            "date": ws.date.isoformat(),
            "duration": ws.duration,
            "exercises": exercise_data
        })
    
    # Generate exercise recommendations based on progress
    recommendations = generate_recommendations(result)
    
    return jsonify({
        "progress": result,
        "recommendations": recommendations
    })

def generate_recommendations(progress_data):
    """Generate exercise recommendations based on user progress"""
    recommendations = []
    
    if not progress_data:
        recommendations.append("Start with 3 sets of bicep curls with 8-12 reps per set")
        recommendations.append("Try arm lifting exercises 2-3 times per week")
        return recommendations
    
    # Calculate total reps and sessions
    total_sessions = len(progress_data)
    total_reps = sum(sum(ex["reps"] for ex in session["exercises"]) for session in progress_data)
    
    # Basic recommendation algorithm
    if total_sessions < 3:
        recommendations.append("Try to work out more consistently, aim for 3-4 sessions per week")
    
    if total_reps < 50:
        recommendations.append("Increase your rep count gradually. Try adding 2-3 reps per set")
    elif total_reps < 100:
        recommendations.append("Good progress! Try adding more weight to challenge yourself")
    else:
        recommendations.append("Excellent progress! Consider adding variety with different arm exercises")
    
    return recommendations

if __name__ == "__main__":
    app.run(debug=True)