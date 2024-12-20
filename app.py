from flask import Flask, render_template, request, redirect, url_for, session
from pymongo import MongoClient
from datetime import datetime
import os
from werkzeug.utils import secure_filename
from bson import ObjectId

app = Flask(__name__)
app.secret_key = 'your_secret_key'

client = MongoClient('mongodb://localhost:27017/')
db = client['facebook_db']
users_collection = db['users']
posts_collection = db['posts']

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        if '@' not in email:
            return "Invalid email address", 400

        user = {
            "name": name,
            "email": email,
            "password": password
        }
        users_collection.insert_one(user)

        session['name'] = name
        return redirect(url_for('create_post'))

    return render_template('index.html')

@app.route('/create_post', methods=['GET', 'POST'])
def create_post():
    name = session.get('name')

    if not name:
        return redirect(url_for('login'))

    if request.method == 'POST':
        post_text = request.form['post-text']
        image_url = None

        if 'post-image' in request.files:
            file = request.files['post-image']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                image_url = url_for('static', filename='uploads/' + filename)

        if post_text:
            post = {
                "user_name": name,
                "text": post_text,
                "timestamp": datetime.utcnow(),
                "image_url": image_url,
                "comments": [],
                "likes": []
            }
            posts_collection.insert_one(post)

        return redirect(url_for('create_post'))

    posts = posts_collection.find()
    return render_template('home.html', name=name, posts=posts)

@app.route('/like/<post_id>', methods=['POST'])
def like_post(post_id):
    name = session.get('name')

    if not name:
        return redirect(url_for('login'))

    post = posts_collection.find_one({"_id": ObjectId(post_id)})

    if post:
        if name in post['likes']:
            posts_collection.update_one(
                {"_id": ObjectId(post_id)},
                {"$pull": {"likes": name}}
            )
        else:
            posts_collection.update_one(
                {"_id": ObjectId(post_id)},
                {"$push": {"likes": name}}
            )

        return redirect(url_for('create_post'))

    return redirect(url_for('index'))

@app.route('/comment/<post_id>', methods=['POST'])
def add_comment(post_id):
    comment_text = request.form['comment-text']
    name = session.get('name')

    if not name:
        return redirect(url_for('login'))

    if comment_text:
        post = posts_collection.find_one({"_id": ObjectId(post_id)})

        if post:
            comment = {
                "text": comment_text,
                "user_name": name,
                "timestamp": datetime.utcnow()
            }

            posts_collection.update_one(
                {"_id": ObjectId(post_id)},
                {"$push": {"comments": comment}}
            )

        return redirect(url_for('create_post'))

    return redirect(url_for('index'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        
        profile_image_url = None
        if 'profile-image' in request.files:
            file = request.files['profile-image']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                profile_image_url = url_for('static', filename='uploads/' + filename)

        user = {
            "name": name,
            "email": email,
            "password": password,
            "profile_image_url": profile_image_url
        }
        
        users_collection.insert_one(user)

        session['name'] = name
        return redirect(url_for('create_post'))

    return render_template('index.html')

@app.route('/profile')
def profile():
    name = session.get('name')
    
    if not name:
        return redirect(url_for('login'))
    
    user = users_collection.find_one({"name": name})
    
    if not user:
        return redirect(url_for('index'))

    return render_template('profile.html', user=user, name=name)

@app.route('/logout')
def logout():
    session.pop('name', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, port=5002)