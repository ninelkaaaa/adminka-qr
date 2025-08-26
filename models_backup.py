from app import db
from sqlalchemy.ext.associationproxy import association_proxy
from datetime import datetime

# Define association tables with extend_existing=True
user_categories = db.Table('user_categories',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('category_id', db.Integer, db.ForeignKey('category.id'), primary_key=True),
    extend_existing=True  # Add this parameter
)

key_category = db.Table('key_category',
    db.Column('key_id', db.Integer, db.ForeignKey('key.id'), primary_key=True),
    db.Column('category_id', db.Integer, db.ForeignKey('category.id'), primary_key=True),
    extend_existing=True  # Add this parameter
)

class Role(db.Model):
    __tablename__ = 'role'

    id   = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.String(50), nullable=False)

    def __repr__(self):
        return f'<Role {self.role}>'


class Users(db.Model):
    __tablename__ = 'users'

    id       = db.Column(db.Integer, primary_key=True)
    fio      = db.Column(db.Text, nullable=False)
    number   = db.Column(db.String(20), nullable=False)
    password = db.Column(db.Text, nullable=False)
    role_id  = db.Column(db.Integer, db.ForeignKey('role.id'))
    admin    = db.Column(db.Boolean, default=False)

    # Define relationships
    categories = db.relationship('Category', secondary=user_categories, backref='users')

    def __repr__(self):
        return f'<User {self.fio}>'


class Category(db.Model):
    __tablename__ = 'category'

    id       = db.Column(db.Integer, primary_key=True)
    user_id  = db.Column(db.Integer, db.ForeignKey('users.id'))
    category = db.Column(db.String(100), nullable=False)

    def __repr__(self):
        return f'<Category {self.category}>'


class Key(db.Model):
    __tablename__ = 'key'

    id      = db.Column(db.Integer, primary_key=True)
    cab     = db.Column(db.String(50))
    corpus  = db.Column(db.String(10))
    status  = db.Column(db.Boolean, default=True, nullable=False)

    # Define relationships
    categories = db.relationship('Category', secondary=key_category, backref='keys')

    def __repr__(self):
        return f'<Key {self.corpus}.{self.cab}>'


class KeyHistory(db.Model):
    __tablename__ = 'key_history'

    id        = db.Column(db.Integer, primary_key=True)
    user_id   = db.Column(db.Integer, db.ForeignKey('users.id'))
    key_id    = db.Column(db.Integer, db.ForeignKey('key.id'))
    action    = db.Column(db.String(50), nullable=False)
    action_time = db.Column(db.DateTime, default=db.func.current_timestamp())
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp(), nullable=False)

    # Define relationships
    user = db.relationship('Users', backref='key_history')
    used_key = db.relationship('Key', backref='history')

    def __repr__(self):
        return f'<KeyHistory {self.id}>'


class TransferRequest(db.Model):
    __tablename__ = 'transfer_request'

    id            = db.Column(db.Integer, primary_key=True)
    key_id        = db.Column(db.Integer, db.ForeignKey('key.id'), nullable=False)
    status        = db.Column(db.String(20), default='pending', nullable=False)
    timestamp     = db.Column(db.DateTime, default=db.func.current_timestamp())
    to_user_id    = db.Column(db.Integer, db.ForeignKey('users.id'))
    from_user_id  = db.Column(db.Integer, db.ForeignKey('users.id'))

    # Define relationships
    key = db.relationship('Key')
    to_user = db.relationship('Users', foreign_keys=[to_user_id])
    from_user = db.relationship('Users', foreign_keys=[from_user_id])

    def __repr__(self):
        return f'<TransferRequest {self.id}>'
