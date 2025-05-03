from services import db
from datetime import datetime


class Role(db.Model):
    __tablename__ = 'role'

    id   = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.String(50), nullable=False)

    users = db.relationship('Users', back_populates='role')


class Users(db.Model):
    __tablename__ = 'users'

    id       = db.Column(db.Integer, primary_key=True)
    fio      = db.Column(db.Text, nullable=False)
    number   = db.Column(db.String(20), nullable=False)
    password = db.Column(db.Text, nullable=False)
    role_id  = db.Column(db.Integer, db.ForeignKey('role.id'))
    admin    = db.Column(db.Boolean, default=False)

    role       = db.relationship('Role', back_populates='users')
    categories = db.relationship('Category', back_populates='user')
    history    = db.relationship('KeyHistory', back_populates='user', cascade='all, delete-orphan')


class Category(db.Model):
    __tablename__ = 'category'

    id       = db.Column(db.Integer, primary_key=True)
    user_id  = db.Column(db.Integer, db.ForeignKey('users.id'))
    category = db.Column(db.String(100), nullable=False)

    user = db.relationship('Users', back_populates='categories')


class Key(db.Model):
    __tablename__ = 'key'

    id      = db.Column(db.Integer, primary_key=True)
    cab     = db.Column(db.Integer, nullable=False)
    corpus  = db.Column(db.String(10), nullable=False)

    histories = db.relationship(
        'KeyHistory',
        back_populates='key',
        cascade='all, delete-orphan'
    )


class KeyHistory(db.Model):
    __tablename__ = 'key_history'

    id        = db.Column(db.Integer, primary_key=True)
    user_id   = db.Column(db.Integer, db.ForeignKey('users.id'))
    key_id    = db.Column(db.Integer, db.ForeignKey('key.id'))
    action    = db.Column(db.String(50))
    timestamp = db.Column(db.DateTime, default=db.func.now())

    user = db.relationship('Users', back_populates='history')
    key  = db.relationship('Key', back_populates='histories')


class TransferRequest(db.Model):
    __tablename__ = 'transfer_request'

    id            = db.Column(db.Integer, primary_key=True)
    from_user_id  = db.Column(db.Integer, nullable=False)
    to_user_id    = db.Column(db.Integer, nullable=False)
    key_id        = db.Column(db.Integer, nullable=False)
    status        = db.Column(db.String(20), default='pending')  # 'pending', 'approved', 'denied'
    timestamp     = db.Column(db.DateTime, default=datetime.utcnow)
