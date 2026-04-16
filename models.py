from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    erstellt_am = db.Column(db.DateTime, default=datetime.utcnow)
    is_komiteeleitung = db.Column(db.Boolean, default=False, nullable=False)

    wortmeldungen = db.relationship(
        'Wortmeldung', backref='autor', lazy='dynamic',
        cascade='all, delete-orphan'
    )
    rueckmeldungen = db.relationship(
        'Rueckmeldung', backref='autor', lazy='dynamic',
        cascade='all, delete-orphan'
    )
    auflagen = db.relationship(
        'Auflage', backref='user', lazy='dynamic',
        cascade='all, delete-orphan'
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'


class Wortmeldung(db.Model):
    __tablename__ = 'wortmeldungen'

    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    kategorie = db.Column(db.String(50), nullable=False, default='vorfall')  # vorfall, rueckfall, mitteilung_auflage, geheimnis, beziehungsklaerung
    status = db.Column(db.String(50), nullable=False, default='offen')  # offen, erledigt, zurueckgestellt, geloescht
    datum_uhrzeit = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    treffen_id = db.Column(db.Integer, db.ForeignKey('treffen.id'), nullable=True)  # Optional, falls Wortmeldung keinem Treffen zugeordnet

    rueckmeldungen = db.relationship(
        'Rueckmeldung', backref='wortmeldung', lazy='dynamic',
        cascade='all, delete-orphan'
    )

    def __repr__(self):
        return f'<Wortmeldung {self.id} von User {self.user_id}>'


class Rueckmeldung(db.Model):
    __tablename__ = 'rueckmeldungen'

    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    datum_uhrzeit = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    wortmeldung_id = db.Column(db.Integer, db.ForeignKey('wortmeldungen.id'), nullable=False)
    def __repr__(self):
        return f'<Rueckmeldung {self.id} zu Wortmeldung {self.wortmeldung_id}>'

class Auflage(db.Model):
    __tablename__ = 'auflagen'

    id = db.Column(db.Integer, primary_key=True)
    beschreibung = db.Column(db.Text, nullable=False)
    grund = db.Column(db.Text, nullable=False)
    ziel = db.Column(db.Text, nullable=False)
    zeitraum_start = db.Column(db.Date, nullable=False)
    zeitraum_ende = db.Column(db.Date, nullable=True)
    erfahrungen = db.Column(db.Text, nullable=True)
    erstellt_am = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    rueckfaelle = db.relationship(
        'Rueckfall', backref='auflage', lazy='dynamic',
        cascade='all, delete-orphan'
    )

    def __repr__(self):
        return f'<Auflage {self.id} von User {self.user_id}>'


class Rueckfall(db.Model):
    __tablename__ = 'rueckfaelle'

    id = db.Column(db.Integer, primary_key=True)
    beschreibung = db.Column(db.Text, nullable=False)
    gefuehle = db.Column(db.Text, nullable=False)
    situation = db.Column(db.Text, nullable=False)
    lernpunkte = db.Column(db.Text, nullable=True)
    positives_verhalten = db.Column(db.Text, nullable=True)
    datum_uhrzeit = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    auflage_id = db.Column(db.Integer, db.ForeignKey('auflagen.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    def __repr__(self):
        return f'<Rueckfall {self.id} zu Auflage {self.auflage_id}>'

class Treffen(db.Model):
    __tablename__ = 'treffen'

    id = db.Column(db.Integer, primary_key=True)
    datum = db.Column(db.Date, nullable=False)
    uhrzeit = db.Column(db.Time, nullable=False)
    ort = db.Column(db.String(200), nullable=False)
    beschreibung = db.Column(db.Text, nullable=True)
    erstellt_am = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    wortmeldungen = db.relationship(
        'Wortmeldung', backref='treffen', lazy='dynamic',
        cascade='all, delete-orphan'
    )

    def __repr__(self):
        return f'<Treffen {self.id} am {self.datum}>'
