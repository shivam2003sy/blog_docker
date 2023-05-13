from flask import Flask
from celery import Celery
from flask_sqlalchemy import SQLAlchemy
from flask_caching import Cache
import jwt
import os 


# model imports
from flask_login import UserMixin
import datetime
import base64
from flask import Flask, request, jsonify, render_template, redirect, url_for, flash, session, abort, send_from_directory


from werkzeug.utils import secure_filename
import os
from time import perf_counter_ns
from flask_mail import Mail
from flask_cors import CORS 
basedir = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
SECRET_KEY = 'mysecretkeyyoucannotguessit'
app.config['SECRET_KEY'] = SECRET_KEY
CORS(app, resources={r"*": {"origins": "https://vloglite-qw6o.vercel.app"}})


# done
mail =None
mail = Mail(app)
# Configure mail settings for Outlook
app.config['MAIL_SERVER']='smtp.office365.com'
app.config['MAIL_PORT'] = 25
app.config['MAIL_USERNAME'] = 'shivam2003sy@outlook.com'
app.config['MAIL_PASSWORD'] = 'vbaaosgmsmjnlxdi'
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False


app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://myuser:mypassword@db:5432/mydb'
# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
db = SQLAlchemy(app)
celery = Celery(app.name, broker='redis://redis:6379/0' , backend='redis://redis:6379/1')
celery.tasks = celery.tasks
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif' , 'csv'}
cache = None
cache = Cache(app)
cache.init_app(app, config={'CACHE_TYPE': 'simple'})


@app.route('/static/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'],
                               filename)



def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS



def delete_image(image_path):
    if os.path.exists(image_path):
        os.remove(image_path)
        app.logger.info("------------------------------image ----------------deleete -------------")
        return 'Image deleted successfully'
    else:
        return 'Image not found'


# utils 
from functools import wraps
from flask import request
from flask import current_app
import jwt


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if "Authorization" in request.headers:
            token = request.headers["Authorization"].split(" ")[1]
        if not token:
            return {
                "message": "Token is missing!",
                "data": None,
                "error": "Unauthorized"
            }, 401
        try:
            data = jwt.decode(token, current_app.config["SECRET_KEY"], algorithms=["HS256"])
            current_user = User.query.filter_by(id=data['id']).first()
            if not current_user:
                return {
                    "message": "User not found",
                    "data": None,
                    "error": "Unauthorized"
                }, 401
        except jwt.DecodeError:
            return {
                "message": "Invalid token",
                "data": None,
                "error": "Unauthorized"
            }, 401
        except jwt.ExpiredSignatureError:
            return {
                "message": "Token has expired",
                "data": None,
                "error": "Unauthorized"
            }, 401
        except Exception as e:
            return {
                "message": "Something went wrong",
                "data": None,
                "error": str(e)
            }, 500
        return f(current_user, *args, **kwargs)
    return decorated




class Post(db.Model):
    id = db.Column(db.Integer , primary_key=True)
    title = db.Column(db.String(10000))
    caption = db.Column(db.String(10000))
    imgpath  = db.Column(db.String(100))
    timestamp = db.Column(db.DateTime)
    no_of_likes = db.Column(db.Integer , default=0)
    user_id = db.Column(db.Integer, db.ForeignKey('profile.id'))
    post_likes = db.relationship('Likes' , backref='Post', lazy='subquery')
    comments = db.relationship('Comments' , backref='Post', lazy='subquery')
    def __repr__(self):
        return str(self.id) + ' - ' + str(self.title)
    def save(self):
        db.session.add( self )
        db.session.commit()
        return self
    def get_by_id(self, id):
        return Post.query.filter_by(id=id).first()
    def to_json(self):
        json_user = {
            'id': self.id,
            'title': self.title,
            'caption': self.caption,
            'imgpath': self.imgpath,
            'timestamp': self.timestamp,
            'no_of_likes': self.no_of_likes,
            # 'user_id': self.user_id,
        }
        return json_user
    

    
    def delete(self):
        db.session.delete(self)
        db.session.commit()
        return self

class Follow(db.Model):
    follower_id = db.Column(db.Integer, db.ForeignKey('user.id'),
                            primary_key=True)
    followed_id = db.Column(db.Integer, db.ForeignKey('user.id'),
                            primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.now)
    def __repr__(self):
        return   str(self.follower_id) + ' - ' + str(self.followed_id)
    def save(self):
        db.session.add(self)
        db.session.commit()
        return self
    def delete(self):
        db.session.delete(self)
        db.session.commit()
        return self
    def to_json(self):
        following = User.query.filter_by(id=self.followed_id).first()
        follower = User.query.filter_by(id=self.follower_id).first()
        json_follow = {
            'follower_id': self.follower_id,
            'followed_id': self.followed_id,
            'timestamp': self.timestamp,
            'follower': follower.user,
            'following': following.user
        }
        return json_follow
class User(UserMixin, db.Model):
    id = db.Column(db.Integer,primary_key=True)
    user = db.Column(db.String(64),unique = True)
    email = db.Column(db.String(120),unique = True)
    password = db.Column(db.String(500))
    last_seen = db.Column(db.DateTime , default=datetime.datetime.now)
    email_verified = db.Column(db.Boolean, default=False)
    Profile = db.relationship('Profile' , backref='User', lazy='subquery' , uselist=False)
    followed = db.relationship('Follow',
                               foreign_keys=[Follow.follower_id],
                               backref=db.backref('follower', lazy='subquery'),
                               lazy='subquery',
                               cascade='all, delete-orphan')
    followers = db.relationship('Follow',
                              foreign_keys=[Follow.followed_id],
                              backref=db.backref('followed', lazy='subquery'),
                              lazy='subquery',
                              cascade='all, delete-orphan')
    def get_by_id(self, id):
        return User.query.filter_by(id=id).first()
    def get_by_username(self, username):
        return User.query.filter_by(user=username).first()
    def get_by_email(self, email):
        return User.query.filter_by(email=email).first()

    def get_all(self):
        return User.query.all()
    def __repr__(self):
        return str(self.id) + ' - ' + str(self.user)
    def save(self):   
        db.session.add( self )
        db.session.commit()
        return self 
    def to_json(self):
        json_user = {
            'id': self.id,
            'user': self.user,
            'email': self.email,
            'last_seen': self.last_seen,
            'email_verified': self.email_verified,
        }
        return json_user
    def from_json(self, json_user):
        self.user = json_user.get('user')
        self.email = json_user.get('email')
        self.password = json_user.get('password')
        self.last_seen = datetime.datetime.now()
        return self
    def verify_password(self, password):
        return self.password == password
    
    def login(self, username, password):
        user = User.query.filter_by(user=username).first()
        if user and user.verify_password(password):
            user.last_seen = datetime.datetime.now()
            user.save()
            return user.to_json()
        return None
    def delete(self):
        db.session.delete(self)
        db.session.commit()
        return self
    def update(self):
        db.session.commit()
        return self
    def check_password(self, password):
        return self.password == password

class Profile(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True , nullable=False)
    no_of_posts = db.Column(db.Integer)
    no_of_followers = db.Column(db.Integer)
    no_of_following = db.Column(db.Integer)
    image  = db.Column(db.LargeBinary)
    report_type = db.Column(db.String(100) , default='html')
    post = db.relationship('Post' , backref='Profile', lazy='subquery')
    post_likes = db.relationship('Likes' , backref='Profile', lazy='subquery')
    comments = db.relationship('Comments' , backref='Profile', lazy='subquery')
    def __repr__(self):
        return str(self.id) + ' - ' + str(self.user_id)
    def save(self):   
        db.session.add( self )
        db.session.commit()
        return self
    def image_to_base64(self):
        return base64.b64encode(self.image).decode('utf-8')

    def to_json(self):
        json_user = {
            'user_id': self.user_id,
            'no_of_posts': self.no_of_posts,
            'no_of_followers': self.no_of_followers,
            'no_of_following': self.no_of_following,
            'report_type': self.report_type,
            'image': self.image_to_base64() if self.image else None
        }
        return json_user
    def delete(self):
        db.session.delete(self)
        db.session.commit()
        return self
    def get_by_id(id):
        return Profile.query.filter_by(id=id).first()
    def update(self):
        db.session.commit()
        return self


class Likes(db.Model):
    id = db.Column(db.Integer , primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id') , nullable=False) 
    user_id = db.Column(db.Integer, db.ForeignKey('profile.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.now())
    def __repr__(self):
        return str(self.id) + ' - ' + str(self.post_id) + ' - ' + str(self.user_id)
    def to_json(self):
        user = User.query.filter_by(id=self.user_id).first()
        json_user = {
            'id': self.id,
            'post_id': self.post_id,
            'username':user.user,
            'user_id': self.user_id,
            'timestamp': self.timestamp,
        }
        return json_user
    def delete(self):
        db.session.delete(self)
        db.session.commit()
        return self
    def save(self):
        db.session.add(self)
        db.session.commit()
        return self
class Comments(db.Model):
    id = db.Column(db.Integer , primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('profile.id'))
    comment = db.Column(db.String())
    timestamp = db.Column(db.DateTime, default=datetime.datetime.now())
    def __repr__(self):
        return str(self.id) + ' - ' + str(self.post_id) + ' - ' + str(self.user_id) + ' - ' + str(self.comment)
    def to_json(self):
        user = User.query.filter_by(id=self.user_id).first()
        json_user = {
            'id': self.id,
            'post_id': self.post_id,
            'username':user.user,
            'user_id': self.user_id,
            'comment': self.comment,
            'timestamp': self.timestamp,
        }
        return json_user
    def delete(self):
        db.session.delete(self)
        db.session.commit()
        return self
    def save(self):
        db.session.add(self)
        db.session.commit()


# end points of the api
# ----------==================---------------------============================--------------
# create user
@app.route("/api/users/create", methods=["POST"])
def create_user():
    data = request.get_json()
    if not data or not data["username"] or not data["email"] or not data["password"]:
        return {
            "message": "Please provide all user details!",
            "data": None,
            "error": "Bad Request"
        }, 400
    if User().get_by_username(data["username"]):
        return {
            "message": "User already exists!",
            "data": None,
            "error": "Bad Request"
        }, 400
    if User().get_by_email(data["email"]):
        return {
            "message": "User with this email already exists!",
            "data": None,
            "error": "Bad Request"
        }, 400
    new_user = User(
        user=data["username"],
        email=data["email"],
        password=data["password"],
        last_seen=datetime.datetime.now()
    )
    new_user.save()
    user = User().get_by_username(data["username"])
    newprofile = Profile(user_id =user.id , no_of_posts=0 , no_of_followers=0 , no_of_following=0)
    newprofile.save()
    return {
        "message": "Successfully created user!",
        "data": new_user.to_json(),
        "error": None
    }, 201

@app.route("/api/users/login", methods=["POST"])
def login_api():
    try:
        data = request.json
        if not data:
            return {
                "message": "Please provide user details",
                "data": None,
                "error": "Bad request"
            }, 400
        user = User().login(
            data["username"],
            data["password"]
        )
        if user:
            try:
                # token should expire after 24 hrs
                app.logger.info(user["id"])
                user_id_str = str(user["id"])  # convert id to string
                token = jwt.encode(
                    {"id": user_id_str},
                    app.config["SECRET_KEY"],
                    algorithm="HS256"
                )
                user["id"] = token  # assign token to id field
                return {
                    "message": "Successfully fetched auth token",
                    "data": user
                }
            except Exception as e:
                return {
                    "error": "Something went wrong here",
                    "message": str(e)
                }, 500
        return {
            "message": "Error fetching auth token!, invalid email or password",
            "data": None,
            "error": "Unauthorized"
        }, 404
    except Exception as e:
        return {
                "message": "Something went wrong! here is th error",
                "error": str(e),
                "data": None
        }, 500



# get all users
@app.route("/api/all", methods=["GET"], endpoint="get_all_users")
@token_required
def get_all_users(current_user):
    try:
        users = User.query.all()
        if users:
            users = [user.to_json() for user in users]
            return {
                "message": "Users fetched successfully!",
                "data": users,
                "error": None
            }, 200
        return {
            "message": "No users found!",
            "data": None,
            "error": "Not Found"
        }, 404
    except Exception as e:
        return {
            "message": "Something went wrong!",
            "error": str(e),
            "data": None
        }, 500




#  delete User  sucess
@app.route("/api/users/delete", methods=["POST"])
@token_required
def delete_user(current_user):
    try:
        data = request.get_json()
        if not data or not data["password"]:
            return {
                "message": "Please provide password!",
                "data": None,
                "error": "Bad Request"
            }, 400
        user = User().get_by_id(current_user.id)
        if user:
            if user.password != data["password"]:
                return {
                    "message": "Invalid password!",
                    "data": None,
                    "error": "Bad Request"
                }, 400
            Profile.query.filter_by(user_id=current_user.id).delete()
            Post.query.filter_by(user_id=current_user.id).delete()
            Likes.query.filter_by(user_id=current_user.id).delete()
            Comments.query.filter_by(user_id=current_user.id).delete()
            Follow.query.filter_by(followed_id=current_user.id).delete()
            #  decrease the no of followers of the user who is following the current user
            followers = Follow.query.filter_by(followed_id=current_user.id).all()
            for follower in followers:
                profile = Profile.query.filter_by(user_id=follower.follower_id).first()
                profile.no_of_followers -= 1
                profile.save()
            Follow.query.filter_by(follower_id=current_user.id).delete()
            #  decrease the no of following of the user who is followed by the current user
            followings = Follow.query.filter_by(follower_id=current_user.id).all()
            for following in followings:
                profile = Profile.query.filter_by(user_id=following.followed_id).first()
                profile.no_of_following -= 1
                profile.save()

            user.delete()

            return {
                "message": "User deleted successfully!"+str(user.user),
                "data": None,
                "error": None
            }, 200
        return {
            "message": "User not found!",
            "data": None,
            "error": "Not Found"
        }, 404
    except Exception as e:
        return {
            "message": "Something went wrong!",
            "error": str(e),
            "data": None
        }, 500



#  read user and Profile
@app.route("/api/user", methods=["GET"] , endpoint="get_user")
@token_required
def get_user(current_user):
    user  = User.query.filter_by(id=current_user.id).first()
    if user:
        profile  = Profile.query.filter_by(user_id=current_user.id).first()
        if Profile:
            return {
                    "message": "User fetched successfully!",
                    "data": {
                        "user": user.to_json(),
                        "Profile": Profile.to_json(profile)
                    },
                    "error": None
                }, 200
    return {
        "message": "User not found!",
        "data": None,
        "error": "Not Found"
    }, 404


#   get  user by username
@app.route('/api/users/<string:username>', methods=['GET'] , endpoint="get_user_by_username")
@token_required
def get_user_by_username(current_user,username):
    user = User.query.filter_by(user=username).first()
    if user:
        profile  = Profile.query.filter_by(user_id=user.id).first()
        if Profile:
            return {
                    "message": "User fetched successfully!",
                    "data": {
                        "user": user.to_json(),
                        "Profile": Profile.to_json(profile)
                    },
                    "error": None
                }, 200
    return {
        "message": "User not found!",
        "data": None,
        "error": "Not Found"
    }, 404



@app.route("/api/user", methods=["PUT"], endpoint="update_user")
@token_required
def update_user(current_user):
    profile = Profile.query.filter_by(user_id=current_user.id).first()
    user = User.query.filter_by(id=current_user.id).first()
    if user:
        # get form data
        data = request.form 
        if not data:
            return {
                "message": "Please provide user details",
                "data": None,
                "error": "Bad request"
            }, 400
        user.email = data["email"]
        if data['report_type'] == 'html format':
            profile.report_type = 'html'
        elif data['report_type'] == 'pdf format':
            profile.report_type = 'pdf'
        else:
            profile.report_type = 'html'
        # Profile.image = data["image"]
        # handel image and save it to the database
        if request.files:
            image = request.files['image']
            # save image to the database
            profile.image = image.read()
        user.update()
        profile.update()
        return {
            'message':  'User updated successfully!',
            'data': {
                'user': user.to_json(),
                'Profile': Profile.to_json(profile)
            },
            'error': None
        }, 200
    return {
        'message': 'User not found!',
        'data': None,
        'error': 'Not Found'
    }, 404
    


# read Posts sucess
@app.route("/api/posts", methods=["GET"] , endpoint="get_posts")
@token_required
def get_posts(current_user):
    user  =     User.query.filter_by(id=current_user.id).first()
    if user:
        posts  = Post.query.filter_by(user_id=current_user.id).all()
        if posts:
            return {
                    "message": "Posts fetched successfully!",
                    "data": {
                        "posts": [post.to_json() for post in posts]
                    },
                    "error": None
                }, 200
    return {
        "message": "Posts not found!",
        "data": None,
        "error": "Not Found"
    }, 404

# get all  post of username 
@app.route('/api/users/<string:username>/posts', methods=['GET'] , endpoint="get_posts_by_username")
@token_required
def get_posts_by_username(current_user,username):
    user = User.query.filter_by(user=username).first()
    if user:
        posts  = Post.query.filter_by(user_id=user.id).all()
        if posts:
            return {
                    "message": "Posts fetched successfully!",
                    "data": {
                        "posts": [post.to_json() for post in posts]
                    },
                    "error": None
                }, 200
    return {
        "message": "Posts not found!",
        "data": None,
        "error": "Not Found"
    }, 404
 
#single post  sucess
@app.route("/api/posts/<int:post_id>", methods=["GET"] , endpoint="get_post")
@token_required
def get_post(current_user , post_id):
    post  = Post.query.filter_by(id=post_id).first()
    if post:
        postcomment = Comments.query.filter_by(post_id=post_id).all()      
        postliked = Likes.query.filter_by(post_id=post_id).all()
        user  = User.query.filter_by(id=post.user_id).first()
        return {
                    "message": "Post fetched successfully!",
                    "data": {
                        "user": user.to_json(),
                        "post": post.to_json(),
                        "postlikedby": [postlike.to_json() for postlike in postliked],
                        "postcommentedby": [postcomment.to_json() for postcomment in postcomment]
                    },
                    "error": None
                }, 200
    return{
                "message": "Post not found!",
                "data": None,
                "error": "Not Found"

            }

# # create post sucess
@app.route("/api/posts", methods=["POST"] , endpoint="create_post")
@token_required
def create_post(current_user):
    app.logger.info("create post")
    title = request.form['title']
    description = request.form['description']
    app.logger.info(title)
    file = request.files['file']
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save('static/uploads/' + filename)
        app.logger.info("-----------------" + filename)
    if not title:
        return {
            "message": "Please provide post details",
            "data": None,
            "error": "Bad request"
        }, 400
    user = User().get_by_id(current_user.id)
    if user:
        post = Post(
            user_id = user.id,
            title = title,
            caption = description,
            imgpath= filename,
            timestamp= datetime.datetime.now()
        )
        user = Profile().query.filter_by(user_id=current_user.id).first()

        user.no_of_posts = user.no_of_posts + 1
        user.save()
        post.save()
        return {
            "message": "Post created successfully!",
            "data": post.to_json(),
            "error": None
        }, 201

# update post  sucess
@app.route("/api/posts/<int:post_id>", methods=["PUT"] , endpoint="update_post")
@token_required
def update_post(current_user , post_id):
    post  = Post.query.filter_by(id = post_id).first()
    app.logger.info("update post")
    # json data
    data = request.get_json()
    # title = data['title']
    if data['title']:
        title = data['title']
        post.title = title
    if data['description']:
        description = data['description']
        post.caption = description
    post.timestamp = datetime.datetime.now()
    user = User().get_by_id(current_user.id)
    if user:
        post.save()
        return {
            "message": "Post updated successfully!",
            "data": post.to_json(),
            "error": None
        }, 201

# delete post sucess
@app.route("/api/posts/<int:post_id>", methods=["DELETE"] , endpoint="delete_post")
@token_required
def delete_post(current_user , post_id):
    try:
        user = User().get_by_id(current_user.id)
        if user:
            post = Post().get_by_id(post_id)
            if post:
                likes = Likes.query.filter_by(post_id=post_id).all()
                if likes:
                    for postlike in likes:
                        postlike.delete()
                comments = Comments.query.filter_by(post_id=post_id).all()
                if comments:
                    for comment in comments:
                        comment.delete()
                profile = Profile.query.filter_by(user_id=user.id).first()
                profile.no_of_posts = profile.no_of_posts - 1
                profile.save()
                post.delete()
                return {
                    "message": "Post deleted successfully!",
                    "data": None,
                    "error": None
                }, 200
        return {
            "message": "Post not found!",
            "data": None,
            "error": "Not Found"
        }, 404
    except Exception as e:
        return {
            "message": "Something went wrong!",
            "error": str(e),
            "data": None
        }, 500


# like post
@app.route("/api/posts/<int:post_id>/like", methods=["POST"] , endpoint="like_post")
@token_required
def like_post(current_user , post_id):
    try:
        user = User().get_by_id(current_user.id)
        if user:
            post = Post().get_by_id(post_id)
            if post:
                postlike = Likes(
                    user_id = user.id,
                    post_id = post.id,
                )
            duplicate  = Likes.query.filter_by(user_id=user.id , post_id=post.id).first()
            if duplicate:
                duplicate.delete()
                post.no_of_likes = Likes.query.filter_by(post_id=post_id).count()
                post.save()
                return {
                    "message": "Post unliked successfully!",
                    "data": None,
                    "error": None
                }, 201
            else:
                postlike.save()
                post.no_of_likes = Likes.query.filter_by(post_id=post_id).count()
                post.save()
                return {
                    "message": "Post liked successfully!",
                    "data": postlike.to_json(),
                    "error": None
                }, 201
        return {
            "message": "Post not found!",
            "data": None,
            "error": "Not Found"
        }, 404
    except Exception as e:
        return {
            "message": "Something went wrong!",
            "error": str(e),
            "data": None
        }, 500


# comment on post sucess
@app.route("/api/posts/<int:post_id>/comment", methods=["POST"] , endpoint="comment_post")
@token_required
def comment_post(current_user , post_id):
    try:
        data = request.get_json()
        if not data:
            return {
                "message": "Please provide comment details",
                "data": None,
                "error": "Bad request"
            }, 400
        user = User().get_by_id(current_user.id)
        if user:
            post = Post().get_by_id(post_id)
            if post:
                comment = Comments(
                    user_id = user.id,
                    post_id = post.id,
                    comment = data.get("comment"),
                    timestamp = datetime.datetime.now()
                )
                comment.save()
                
                #   all comment on post with username
                comments = Comments.query.filter_by(post_id=post_id).all()
                comments = [comment.to_json() for comment in comments]
                for comment in comments:
                    user  = User().get_by_id(comment['user_id'])
                    comment['user'] = user.to_json()
                return {
                    "message": "Comment added successfully!",
                    "data": comments,
                    "error": None
                }, 201
        return {
            "message": "Post not found!",
            "data": None,
            "error": "Not Found"
        }, 404
    except Exception as e:
        return {
            "message": "Something went wrong!",
            "error": str(e),
            "data": None
        }, 500


# commnet with specific response
@app.route("/api/posts/comment/<int:post_id>", methods=["POST"] , endpoint="comment_res")
@token_required
def comment_res(current_user , post_id):
    try:
        data = request.get_json()
        if not data:
            return {
                "message": "Please provide comment details",
                "data": None,
                "error": "Bad request"
            }, 400
        user = User().get_by_id(current_user.id)
        if user:
            post = Post().get_by_id(post_id)
            if post:
                comment = Comments(
                    user_id = user.id,
                    post_id = post.id,
                    comment = data.get("comment"),
                    timestamp = datetime.datetime.now()
                )
                comment.save()
                return {
                    "message": "Comment added successfully!",
                    "data": comment.to_json(),
                    "error": None
                }, 201
        return {
            "message": "Post not found!",
            "data": None,
            "error": "Not Found"
        }, 404
    except Exception as e:
        return {
            "message": "Something went wrong!",
            "error": str(e),
            "data": None
        }, 500



# delete comment sucess
@app.route("/api/posts/<int:post_id>/comment/<int:comment_id>", methods=["DELETE"] , endpoint="delete_comment")
@token_required
def delete_comment(current_user , post_id , comment_id):
    try:
        user = User().get_by_id(current_user.id)
        if user:
            post = Post().get_by_id(post_id)
            if post:
                comment = Comments.query.filter_by(id=comment_id , user_id=user.id , post_id=post.id).first()
                if comment:
                    comment.delete()
                    return {
                        "message": "Comment deleted successfully!",
                        "data": None,
                        "error": None
                    }, 200
        return {
            "message": "Comment not found!",
            "data": None,
            "error": "Not Found"
        }, 404
    except Exception as e:
        return {
            "message": "Something went wrong!",
            "error": str(e),
            "data": None
        }, 500

# get all comments sucess
@app.route("/api/posts/<int:post_id>/comments", methods=["GET"] , endpoint="get_comments")
@token_required
def get_comments(current_user , post_id):
    try:
        user = User().get_by_id(current_user.id)
        if user:
            post = Post().get_by_id(post_id)
            if post:
                comments = Comments.query.filter_by(post_id=post.id).all()
                if comments:
                    return {
                        "message": "Comments fetched successfully!",
                        "data": [comment.to_json() for comment in comments],
                        "error": None
                    }, 200
                return {
                    "message": "No comments found!",
                    "data": None,
                    "error": "Not Found"
                }, 404
        return {
            "message": "Post not found!",
            "data": None,
            "error": "Not Found"
        }, 404
    except Exception as e:
        return {
            "message": "Something went wrong!",
            "error": str(e),
            "data": None
        }, 500


# get all likes  sucess
@app.route("/api/posts/<int:post_id>/likes", methods=["GET"] , endpoint="get_likes")
@token_required
def get_likes(current_user , post_id):
    try:
        user = User().get_by_id(current_user.id)
        if user:
            post = Post().get_by_id(post_id)
            if post:
                likes = Likes.query.filter_by(post_id=post.id).all()
                if likes:
                    return {
                        "message": "Likes fetched successfully!",
                        "data": [like.to_json() for like in likes],
                        "error": None
                    }, 200
                return {
                    "message": "No likes found!",
                    "data": None,
                    "error": "Not Found"
                }, 404
        return {
            "message": "Post not found!",
            "data": None,
            "error": "Not Found"
        }, 404
    except Exception as e:
        return {
            "message": "Something went wrong!",
            "error": str(e),
            "data": None
        }, 500



# update comment sucess
@app.route("/api/posts/<int:post_id>/comment/<int:comment_id>", methods=["PUT"] , endpoint="update_comment")
@token_required
def update_comment(current_user , post_id , comment_id):
    try:
        data = request.get_json()
        if not data:
            return {
                "message": "Please provide comment details",
                "data": None,
                "error": "Bad request"
            }, 400
        user = User().get_by_id(current_user.id)
        if user:
            post = Post().get_by_id(post_id)
            if post:
                comment = Comments.query.filter_by(id=comment_id , user_id=user.id , post_id=post.id).first()
                if comment:
                    comment.comment = data.get("comment")
                    comment.save()
                    return {
                        "message": "Comment updated successfully!",
                        "data": comment.to_json(),
                        "error": None
                    }, 200
        return {
            "message": "Comment not found!",
            "data": None,
            "error": "Not Found"
        }, 404
    except Exception as e:
        return {
            "message": "Something went wrong!",
            "error": str(e),
            "data": None
        }, 500



# # search users with string 
# @app.route("/api/users/search/<string:search_string>", methods=["GET"] , endpoint="search_users")
# def search_users(search_string):
#     try:
#         users = User.query.filter(User.user.ilike("%"+search_string+"%")).all()
#         if users:
#             return {
#                     "message": "Users fetched successfully!",
#                     "data": [user.to_json() for user in users],
#                     "error": None
#                 }, 200
#         return {
#                 "message": "No users found!",
#                 "data": None,
#                 "error": "Not Found"
#             }, 404
#     except Exception as e:
#         return {
#             "message": "Something went wrong!",
#             "error": str(e),
#             "data": None
#         }, 500



#  get  followers of user form table Follow
@app.route("/api/users/<string:user>/followers", methods=["GET"] , endpoint="get_followers")
@token_required
def get_followers(current_user , user):
    try:
        user = User.query.filter_by(user=user).first()
        if user:
            followers = Follow.query.filter_by(followed_id=user.id).all()
            if followers:
                # get user names of followers
                followers = [User.query.filter_by(id=follower.follower_id).first() for follower in followers]
                return {
                    "message": "Followers fetched successfully!",
                    "data": [follower.to_json() for follower in followers],
                    "error": None
                }, 200
            return {
                "message": "No followers found!",
                "data": None,
                "error": "Not Found"
            }, 404
        return {
            "message": "User not found!",
            "data": None,
            "error": "Not Found"
        }, 404
    except Exception as e:
        return {
            "message": "Something went wrong!",
            "error": str(e),
            "data": None
        }, 500

#  get  followings of user form table Follow
@app.route("/api/users/<string:user>/followings", methods=["GET"] , endpoint="get_followings")
@token_required
def get_followings(current_user , user):
    try:
        user = User.query.filter_by(user=user).first()
        if user:
            followings = Follow.query.filter_by(follower_id=user.id).all() # kis kis ko follow krta h user
            if followings:
                # get user names of folowings
                followings = [User.query.filter_by(id=following.followed_id).first() for following in followings]
                return {
                    "message": "Followings fetched successfully!",
                    "data": [following.to_json() for following in followings],
                    "error": None
                }, 200
            return {
                "message": "No followings found!",
                "data": None,
                "error": "Not Found"
            }, 404
        return {
            "message": "User not found!",
            "data": None,
            "error": "Not Found"
        }, 404
    except Exception as e:
        return {
            "message": "Something went wrong!",
            "error": str(e),
            "data": None
        }, 500

#  follow  or unfollow user 
@app.route("/api/users/<string:user>/follow", methods=["POST"] , endpoint="follow_user")
@token_required
def follow_user(current_user , user):
    try:
        user = User.query.filter_by(user=user).first()
        if user:
            if user.id == current_user.id:
                return {
                    "message": "You can't follow yourself!",
                    "data": None,
                    "error": "Bad request"
                }, 400
            follow = Follow.query.filter_by(follower_id=current_user.id , followed_id=user.id).first()
            if not follow:
                follow = Follow(follower_id=current_user.id , followed_id=user.id)
                follow.save()
                followed = Profile.query.filter_by(user_id=user.id).first()
                followed.no_of_followers += 1
                followed.save()
                follower = Profile.query.filter_by(user_id=current_user.id).first()
                follower.no_of_following += 1
                follower.save()
                return {
                    "message": "User followed successfully!",
                    "data": follow.to_json(),
                    "error": None
                }, 200
            return {
                "message": "User already followed!",
                "data": follow.to_json(),
                "error": None
            }, 200
        
        return {
            "message": "User not found!",
            "data": None,
            "error": "Not Found"
        }, 404
    except Exception as e:
        return {
            "message": "Something went wrong!",
            "error": str(e),
            "data": None
        }, 500

#  unfollow user
@app.route("/api/users/<string:user>/unfollow", methods=["POST"] , endpoint="unfollow_user")
@token_required
def unfollow_user(current_user , user):
    try:
        user = User.query.filter_by(user=user).first()
        if user:
            follow = Follow.query.filter_by(follower_id=current_user.id , followed_id=user.id).first()
            if follow:
                follow.delete()
                followed = Profile.query.filter_by(user_id=user.id).first()
                followed.no_of_followers -= 1
                followed.save()
                follower = Profile.query.filter_by(user_id=current_user.id).first()
                follower.no_of_following -= 1
                follower.save()
                return {
                    "message": "User unfollowed successfully!",
                    "data": follow.to_json(),
                    "error": None
                }, 200
            return {
                "message": "You don't follow this user!",
                "data": None,
                "error": "Bad request"
            }, 400
        return {
            "message": "User not found!",
            "data": None,
            "error": "Not Found"
        }, 404
    except Exception as e:
        return {
            "message": "Something went wrong!",
            "error": str(e),
            "data": None
        }, 500
    




@app.route("/api/feeds", methods=["GET"], endpoint="get_feeds")
@token_required
def get_feeds(current_user):
    start = perf_counter_ns()
    following = get_following_posts(current_user)
    posts = Post.query.filter(Post.user_id.in_(following)).order_by(Post.timestamp.desc()).all()
    if posts:
        posts = [post.to_json() for post in posts]
        for post in posts:
            post_data, user, comments, likes = get_post_details(post['id'])
            post["user"] = user.to_json()
            post["comments"] = [comment.to_json() for comment in comments]
            for comment in post["comments"]:
                comment["user"] = User.query.filter_by(id=comment["user_id"]).first().to_json()
            post["likes"] = [User.query.filter_by(id=like.user_id).first().to_json() for like in likes]

        end = perf_counter_ns()
        print("time taken to fetch posts: ", (end-start)/1000000)
        return {
            "message": "Posts fetched successfully!",
            "data": posts,
            "error": None
        }, 200

    return {
        "message": "No posts found!",
        "data": None,
        "error": "Not Found"
    }, 404
#  celery tasks
@app.route("/api/tasks/<string:name>", methods=["GET"] , endpoint="get_tasks")
def get_tasks(name):
    jobs = sayhello.apply_async(args=[name])
    result = jobs.wait()
    return {
        "message": "Task added to queue!",
        "data":str(jobs) ,
        "result" : result,
        "error": None
    }, 200

# run task print date
@app.route("/api/tasks", methods=["GET"] , endpoint="get_date")
def get_date():
    jobs = print_current_time.apply_async()
    result = jobs.wait()
    return {
        "message": "Task added to queue!",
        "data":str(jobs) ,
        "result" : result,
        "error": None
    }, 200

#  send mail using celery send_mail task
@app.route('/send_email', methods=['POST'])
def trigger_send_email():
    subject = 'testing'
    sender = 'shivam2003sy@outlook.com'
    recipients = ['shivam2003sy@gmail.com', 'ankitayadav80048@gmail.com']
    text_body = 'Plain text'
    html_body = '<h1>I lOVE YOU ANKITA</h1> <h3> will you mary me <h3><img src="https://images.unsplash.com/photo-1606041008023-472dfb5e530f?ixlib=rb-4.0.3&ixid=MnwxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8&auto=format&fit=crop&w=388&q=80" alt="flower">'
    
    # Trigger the Celery task asynchronously
    send_email.apply_async(args=[subject, sender, recipients, text_body, html_body])
    return 'Email task scheduled'


#  blog_to_csv task
@app.route("/api/export/<username>", methods=["GET"] , endpoint="blog_to_csv")
def blog_to_csv(username):
    user = User.query.filter_by(user=username).first()
    if user:
        jobs = blog_to_csv.apply_async(args=[username])
        result = jobs.wait()
        # result  = 'added to queue'
        # trigger when mail sent
        if result:
            return {
                "message": "Task added to queue! you will get a mail soon with the csv file",
                "data":str(jobs) ,
                "result" : result,
                "error": None
            }, 200
        return {
            "message": "Something went wrong!",
            "data": None,
            "error": "Internal server error"
        }, 500
    return {
        "message": "User not found!",
        "data": None,
        "error": "Not Found"
    }, 404

#  csv_to_blog task

@app.route("/api/import", methods=["POST"] , endpoint="csv_to_blog")
@token_required
def csv_to_blog(current_user):
    if request.method == "POST":
        if "file" not in request.files:
            return {
                "message": "No file found!.",
                "data": None,
                "error": "Bad request"
            }, 400
        file = request.files["file"]
        if file.filename == "":
            return {
                "message": "No file found!",
                "data": None,
                "error": "Bad request"
            }, 400
        if file:
            filename = '{}_blog.csv'.format(current_user.user)
            file.save(filename)
            jobs = csv_to_blog.apply_async(args=[filename , current_user.id])
            result = jobs.wait()
            if result:
                return {
                    "message": "Task added to queue!",
                    "data":str(jobs) ,
                    "result" : result,
                    "error": None
                }, 200
            return {
                "message": "Something went wrong!",
                "data": None,
                "error": "Internal server error"
            }, 500
        return {
            "message": "File not supported!",
            "data": None,
            "error": "Bad request"
        }, 400
    return {
        "message": "Bad request!",
        "data": None,
        "error": "Bad request"
    }, 400


#  search user functaionality
@app.route('/api/users', methods=['GET'], endpoint='search_users')
def search_users():
    search_term = request.args.get('search')
    # Perform user search logic here based on the search_term
    # and return the results as JSON response
    # Example:
    start = perf_counter_ns()
    users = get_user(search_term)
    # users = User.query.filter(User.user.like('%' + search_term + '%')).all()
    end = perf_counter_ns()
    print("time taken to search user : ", (end - start) / 1000000)
    return {
        "message": "Users fetched successfully!",
        "data": [user.to_json() for user in users],
        "error": None
    }, 200


#  call task verify email
@app.route('/api/verify', methods=['POST'], endpoint='verify')
@token_required
def verify(current_user):
    user = User.query.filter_by(id=current_user.id).first()
    if user:
        email = user.email
    if email:
        jobs = verify_email.apply_async(args=[email])
        result = jobs.wait()
        if result:
            return {
                "message": "Task added to queue!",
                "data":str(jobs) ,
                "result" : result,
                "error": None
            }, 200
        return {
            "message": "Something went wrong!",
            "data": None,
            "error": "Internal server error"
        }, 500
    return {
        "message": "Email not found!",
        "data": None,
        "error": "Bad request"
    }, 400

# verify email
@app.route('/api/verify/<email>', methods=['GET'], endpoint='verify_email')
def verify_email(email):
    user = User.query.filter_by(email=email).first()
    if user:
        if user.email_verified:
            return {
                "message": "Email already verified!",
                "data": None,
                "error": None
            }, 200
        user.email_verified = True
        db.session.commit()
        return {
            "message": "Email verified successfully!",
            "data": None,
            "error": None
        }, 200
    return {
        "message": "User not found!",
        "data": None,
        "error": "Not Found"
    }, 404




#  get followers of user
@app.route('/api/followers/<username> ', methods=['GET'], endpoint='get_followers_of_user')
@token_required
def get_followers_of_user(current_user,username):
    user = User.query.filter_by(user=username).first()
    if user:
        followers = Follow.query.filter_by(followed_id=user.id).all()
        return {
            "message": "Followers fetched successfully!",
            "data": [follower.to_json() for follower in followers],
            "error": None
        }, 200
    return {
        "message": "User not found!",
        "data": None,
        "error": "Not Found"
    }, 404



# followings of user 
@app.route('/api/followings/<username>', methods=['GET'], endpoint='get_followings_of_user')
@token_required
def get_followings_of_user(current_user,username):
    user = User.query.filter_by(user=username).first()
    if user:
        following = Follow.query.filter_by(follower_id=user.id).all()
        return {
            "message": "Following fetched successfully!",
            "data": [follow.to_json() for follow in following],
            "error": None
        }, 200
    return {
        "message": "User not found!",
        "data": None,
        "error": "Not Found"
    }, 404

# followers of user

@app.route('/api/followers/<username>', methods=['GET'], endpoint='get_followers_of_user2')
@token_required
def get_followers_of_user2(current_user,username):
    user = User.query.filter_by(user=username).first()
    if user:
        followers = Follow.query.filter_by(followed_id=user.id).all()
        return {
            "message": "Followers fetched successfully!",
            "data": [follower.to_json() for follower in followers],
            "error": None
        }, 200
    return {
        "message": "User not found!",
        "data": None,
        "error": "Not Found"
    }, 404





























from flask_mail import Message
from celery.schedules import crontab
@celery.task
def add_together(a, b):
    return a + b


@cache.memoize(10)
def get_user(search_term):
        data = User.query.filter(User.user.ilike("%"+search_term+"%")).all()
        return data

@cache.memoize(timeout=1)
def get_following_posts(current_user):
    following = Follow.query.filter_by(follower_id=current_user.id).all()
    following = [following.followed_id for following in following]
    following.append(current_user.id)
    return following

@cache.memoize(timeout=1)
def get_post_details(post_id):
    post = Post.query.filter_by(id=post_id).first()
    userid = post.user_id
    user = User.query.filter_by(id=userid).first()
    comments = Comments.query.filter_by(post_id=post_id).all()
    likes = Likes.query.filter_by(post_id=post_id).all()
    return post, user, comments, likes

@celery.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    sender.add_periodic_task(
        crontab(hour=0,minute=0),
        monthly_reminder.s(),
    )
    sender.add_periodic_task(
        crontab(hour=0, minute=0),
        daily_reminder.s(),
    )
@celery.task
def sayhello(name):
    print("celesy task")
    return ("Hello {}".format(name))
@celery.task
def send_email(subject, sender, recipients, text_body, html_body):
    with app.app_context():
        msg = Message(subject, sender=sender, recipients=recipients)
        msg.body = text_body
        msg.html = html_body
        mail.send(msg)
    return "Email sent"
@celery.task
def blog_to_csv(username):
    with app.app_context():
        user  = User.query.filter_by(user=username).first()
        posts = Post.query.filter_by(user_id=user.id).all()
        with open('{}_blogs.csv'.format(username), 'w') as f:
            # write the header
            f.write('id,title,caption,imgpath,timestamp,no_of_likes\n')
            # write the data
            for post in posts:
                f.write('{},{},{},{},{},{}\n'.format(post.id, post.title, post.caption, post.imgpath, post.timestamp, post.no_of_likes))
        # send email to user
        msg = Message(subject='Blog to CSV file',sender=app.config['MAIL_USERNAME'],recipients=[user.email])
        msg.body = 'Hi {}, your blog has been converted to a CSV file'.format(user.user)
        msg.html = 'Hi {}, your blog has been converted to a CSV file'.format(user.user)
        msg.attach('{}_blogs.csv'.format(username), 'text/csv', open('{}_blogs.csv'.format(username), 'rb').read())
        mail.send(msg)
    return {
        'status': 'success',
        'message': 'CSV file has been sent to your email'
    }

import csv
import os

import uuid
import random
@celery.task
def csv_to_blog(filename,user_id):
    print(filename)
    with open('{}'.format(filename), 'r') as f:
        reader = csv.reader(f)
        next(reader)
        for row in reader:
            #  uniques id
            total_post = Post.query.all()
            while True:
                id = random.randint(1, 100000)
                for post in total_post:
                    if post.id == id:
                        break
                else:
                    break
            row[0] = id
            row[4] = datetime.datetime.strptime(row[4], '%Y-%m-%d %H:%M:%S.%f')
            post = Post(id=row[0],title=row[1], caption=row[2], imgpath=row[3], timestamp=row[4], no_of_likes=row[5], user_id=user_id)
            profile = Profile.query.filter_by(user_id=user_id).first()
            profile.no_of_posts =  profile.no_of_posts + 1
            profile.update()
            db.session.add(post)
            db.session.commit()
    os.remove(filename)
    return {
            'status': 'success',
            'message': 'CSV file has been uploaded'
        }


@celery.task
def daily_reminder():
    with app.app_context():
        users = User.query.all()
        for user in users:
            # check if user has posted any blog today using timestamp
            posts = Post.query.filter_by(user_id=user.id).all()
            for post in posts:
                if post.timestamp.date() == datetime.date.today():
                    break
            else:
                msg = Message(subject='Not posted today',sender=app.config['MAIL_USERNAME'],recipients=[user.email])
                msg.html = """
                <h1>Hi {}, you have not posted any blog today</h1>
                <p>While you are away, here are some blogs you might like</p>
                """.format(user.user)
                #  get 3 random blogs
                posts = Post.query.all()
                import random
                if len(posts) >  3:
                    random_posts = random.sample(posts, 3)
                    for post in random_posts:
                        msg.html += """
                        <h3>{}</h3>
                        <p>{}</p>
                        <img src="http://localhost:5000/static/uploads/{}" alt="{}" width="200" height="200">
                        <p>posted on {}</p>
                        <p>likes: {}</p>
                        <a href="http://locahost:8080/post/{}">Read more</a>
                        """.format(post.title, post.caption, post.imgpath, post.title, post.timestamp, post.no_of_likes , post.id)
                    mail.send(msg)
                    print('daily reminder sent to {}'.format(user.user))
    return {
        'status': 'success',
        'message': 'Email has been sent to all users',
    }

@celery.task
def monthly_reminder():
    with app.app_context():
        users = User.query.all()
        for user in users:
            msg = Message(subject='Monthly report',sender=app.config['MAIL_USERNAME'],recipients=[user.email])
            #  create a report of all ingagements of the user
            posts = Post.query.filter_by(user_id=user.id).all()
            #  POST CREATED THIS MONTHS
            post_created_this_month = 0
            posts_stats = []
            for post in posts:
                # check if post is created this month
                if post.timestamp.month == datetime.date.today().month and post.timestamp.year == datetime.date.today().year:
                    post_created_this_month += 1
                    post_stats = {
                        'post_id': post.id,
                        'post_title': post.title,
                        'post_caption': post.caption,
                        'post_imgpath': post.imgpath,
                        'post_timestamp': post.timestamp,
                        'post_no_of_likes': post.no_of_likes,
                    }
                    comment = Comments.query.filter_by(post_id=post.id).all()
                    post_stats['no_of_comments'] = len(comment)
                    for c in comment:
                        comments = {
                            'comment_id': c.id,
                            'comment': c.comment,
                            'comment_timestamp': c.timestamp,
                        }

                        for u in users:
                            if u.id == c.user_id:
                                comments['comment_user'] = u.user
                        post_stats['comments'] = (comments)
                    likes = Likes.query.filter_by(post_id=post.id).all()
                    for l in likes:
                        for u in users:
                            if u.id == l.user_id:
                                post_stats['likes'] = u.user
                    posts_stats.append(post_stats)

            #  POST LIKED THIS MONTHS
            post_liked_this_month = 0
            post_you_liked  ={
                'post_id': [],
                'post_title': [],
                'post_caption': [],
            }
            for post in posts:
                likes = Likes.query.filter_by(post_id=post.id).all()
                for like in likes:
                    if like.timestamp.month == datetime.date.today().month and like.timestamp.year == datetime.date.today().year:
                        if like.user_id == user.id:
                            post_liked_this_month += 1
                            post_you_liked['post_id'].append(post.id)
                            post_you_liked['post_title'].append(post.title)
                            post_you_liked['post_caption'].append(post.caption)
                            break

            #  POST COMMENTED THIS MONTHS
            post_commented_this_month = 0
            post_you_commented = {
                'post_id': [],
                'post_title': [],
                'post_caption': [],
            }
            for post in posts:
                comments = Comments.query.filter_by(post_id=post.id).all()
                for comment in comments:
                    if comment.timestamp.month == datetime.date.today().month and comment.timestamp.year == datetime.date.today().year:
                        if comment.user_id == user.id:
                            post_commented_this_month += 1
                            post_you_commented['post_id'].append(post.id)
                            post_you_commented['post_title'].append(post.title)
                            post_you_commented['post_caption'].append(post.caption)
                            break

            # USER FOLLOWED THIS MONTHS
            user_followed_this_month = 0
            user_you_followed = {
                'user_id': [],
                'user': [],
            }
            for u in users:
                if u.id != user.id:
                    followers = Follow.query.filter_by(follower_id=u.id).all()
                    for follower in followers:
                        if follower.timestamp.month == datetime.date.today().month and follower.timestamp.year == datetime.date.today().year:
                            if follower.follower_id == user.id:
                                user_followed_this_month += 1
                                user_you_followed['user_id'].append(u.id)
                                user_you_followed['user'].append(u.user)
                                break

            # YOU followed THIS MONTHS
            following_this_month = 0
            followings ={
                'user_id': [],
                'user': [],

            }
            for u in users:
                if u.id != user.id:
                    followers = Follow.query.filter_by(followed_id=u.id).all()
                    for follower in followers:
                        if follower.timestamp.month == datetime.date.today().month and follower.timestamp.year == datetime.date.today().year:
                            if follower.follower_id == user.id:
                                following_this_month += 1
                                followings['user_id'].append(u.id)
                                followings['user'].append(u.user)
                                break
        print('monthly reminder sent to {}'.format(user.user))
        msg.html = """
        <h1 style="color: #007BFF;">Monthly Report</h1>
        <p>Here is your monthly report:</p>
        <p><strong>Posts created this month:</strong> {}</p>
        <p><strong>Posts liked this month:</strong> {}</p>
        <p><strong>Posts commented this month:</strong> {}</p>
        <p><strong>Users followed this month:</strong> {}</p>
        <p><strong>You followed this month:</strong> {}</p>
        <p><strong>Posts JSON data:</strong> {}</p>
        <p><strong>Users you followed JSON data:</strong> {}</p>
        <p><strong>Followings JSON data:</strong> {}</p>
        <p><strong>Posts you liked JSON data:</strong> {}</p>
        <p><strong>Posts you commented on JSON data:</strong> {}</p>
        """.format(post_created_this_month, post_liked_this_month, post_commented_this_month, user_followed_this_month, following_this_month ,posts_stats ,user_you_followed, followings, post_you_liked, post_you_commented)
        mail.send(msg)
# verify email
@celery.task
def verify_email(email):
    # msg = Message(subject='Verify your email',sender=app.config['MAIL_USERNAME'],recipients=[email])
    #     msg.html = """
    #     <h1>Verify your email</h1>
    #     <p>Click on the link below to verify your email</p>
    #     <a href="http://localhost:8080/verify/{}">Verify</a>
    #     """.format(email)
    #     mail.send(msg)
    #     print('email sent to {}'.format(email))
    send_email.delay(
        subject='Verify your email',
        sender=app.config['MAIL_USERNAME'],
        recipients=[email],
        text_body='Verify your email',
        html_body="""
        <h1>Verify your email</h1>
        <p>Click on the link below to verify your email</p>
        <a href="http://localhost:5000/api/verify/{}">Verify</a>
        """.format(email)
    )
    return {
        'status': 'success',
        'message': 'Email has been sent to {}'.format(email),
    }




@app.route('/')
def hello_world():
    result = add_together.delay(23, 42)
    return f'Hello, World! Result: {result.get()}'




@app.before_first_request
def initialize_database():
    db.create_all()
if __name__ == '__main__':
    app.run(host='0.0.0.0')
