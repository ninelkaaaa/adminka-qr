from services import db
from datetime import datetime

# Association table for the many-to-many relationship between Users and Category
user_categories = db.Table('user_categories',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('category_id', db.Integer, db.ForeignKey('category.id'), primary_key=True)
)

class Role(db.Model):
    __tablename__ = 'role'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    users = db.relationship('Users', backref='role', lazy=True)

class Users(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    fio = db.Column(db.String(100), nullable=False)
    number = db.Column(db.String(100), nullable=False, unique=True) # Assuming number is the login
    password = db.Column(db.String(100), nullable=False)
    admin = db.Column(db.Boolean, default=False)
    # link each user to a role
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'), nullable=False)
    key_history = db.relationship('KeyHistory', backref='user', lazy=True)
    key_requests = db.relationship('KeyRequest', backref='requester', lazy=True)
    # Add relationship to categories
    categories = db.relationship('Category', secondary=user_categories, lazy='subquery',
                                 backref=db.backref('users', lazy=True))

class Category(db.Model):
    __tablename__ = 'category'
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(100), nullable=False, unique=True) # Ensure category names are unique

class Key(db.Model):
    __tablename__ = 'key'
    id = db.Column(db.Integer, primary_key=True)
    cab = db.Column(db.Integer, nullable=False)
    corpus = db.Column(db.String(20), nullable=False)
    status = db.Column(db.Boolean, default=True)
    key_history = db.relationship('KeyHistory', backref='key', lazy=True)
    key_requests = db.relationship('KeyRequest', backref='key', lazy=True)

class KeyHistory(db.Model):
    __tablename__ = 'key_history'
    id = db.Column(db.Integer, primary_key=True)
    key_id = db.Column(db.Integer, db.ForeignKey('key.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    action = db.Column(db.String(50), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.now)

class KeyRequest(db.Model):
    __tablename__ = 'key_request'
    id = db.Column(db.Integer, primary_key=True)
    key_id = db.Column(db.Integer, db.ForeignKey('key.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    request_time = db.Column(db.DateTime, nullable=False, default=datetime.now)
    status = db.Column(db.String(20), nullable=False, default='pending')

class TransferRequest(db.Model):
    __tablename__ = 'transfer_requests'
    id = db.Column(db.Integer, primary_key=True)
    from_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    to_user_id   = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    key_id       = db.Column(db.Integer, db.ForeignKey('key.id'), nullable=False)
    status       = db.Column(db.String(20), nullable=False, default='pending')
    timestamp    = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    from_user = db.relationship('Users', foreign_keys=[from_user_id])
    to_user   = db.relationship('Users', foreign_keys=[to_user_id])
    key       = db.relationship('Key',   foreign_keys=[key_id])
