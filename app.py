from flask import Flask, request, jsonify, session, Response
from models import db, User
from flask_bcrypt import Bcrypt
from pose_estimation import start_pose_estimation_lifting
from lunges import start_pose_estimation_lunges
from half_jumping_jacks import start_pose_estimation_jacks
from double_leg_lift import start_pose_estimation_leg_lift
import threading
from flask_cors import CORS

# Initialize Flask app
app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = 'cairocoders-ednalan'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///UsersDataBase.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = True

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


@app.route('/video_feed')
def video_feed():
    key = request.args.get('key')  # Get the 'key' parameter from the query string
    stop_event.clear()
    
    if key == 'lifting':
        return Response(start_pose_estimation_lifting(stop_event),
                        mimetype='multipart/x-mixed-replace; boundary=frame')
    elif key == 'lunges':
        return Response(start_pose_estimation_lunges(stop_event),
                        mimetype='multipart/x-mixed-replace; boundary=frame')
    elif key == 'jumping_jacks':
        return Response(start_pose_estimation_jacks(stop_event),
                        mimetype='multipart/x-mixed-replace; boundary=frame')
    elif key == 'double_leg_lift':
        return Response(start_pose_estimation_leg_lift(stop_event),
                        mimetype='multipart/x-mixed-replace; boundary=frame')
    else:
        return Response("Invalid key", status=400)

@app.route('/stop_video_feed', methods=['POST'])
def stop_video_feed():
    stop_event.set()
    return 'Video feed stopped', 200

if __name__ == '__main__':
    app.run(debug=True)
