import os
from datetime import datetime
from flask import Flask, render_template, redirect, url_for, flash, request, abort
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_wtf.csrf import CSRFProtect
from flask_migrate import Migrate
from models import db, User, Wortmeldung, Rueckmeldung, Auflage, Rueckfall


def create_app():
    app = Flask(__name__)

    app.config['SECRET_KEY'] = os.environ.get(
        'SECRET_KEY', 'dev-secret-key-bitte-aendern-in-produktion'
    )
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
        'DATABASE_URL', 'sqlite:///wortmeldung.db'
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['WTF_CSRF_ENABLED'] = True

    db.init_app(app)
    migrate = Migrate(app, db)
    CSRFProtect(app)
    login_manager = LoginManager(app)
    login_manager.login_view = 'login'
    login_manager.login_message = 'Bitte melde dich an, um diese Seite zu sehen.'
    login_manager.login_message_category = 'warning'

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    with app.app_context():
        db.create_all()

    # ------------------------------------------------------------------
    # Auth Routes
    # ------------------------------------------------------------------

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if current_user.is_authenticated:
            return redirect(url_for('index'))
        if request.method == 'POST':
            username = request.form.get('username', '').strip()
            email = request.form.get('email', '').strip().lower()
            password = request.form.get('password', '')
            password2 = request.form.get('password2', '')

            error = None
            if not username or len(username) < 3:
                error = 'Benutzername muss mindestens 3 Zeichen lang sein.'
            elif not email or '@' not in email:
                error = 'Bitte gib eine gültige E-Mail-Adresse ein.'
            elif len(password) < 6:
                error = 'Das Passwort muss mindestens 6 Zeichen lang sein.'
            elif password != password2:
                error = 'Die Passwörter stimmen nicht überein.'
            elif User.query.filter_by(username=username).first():
                error = 'Dieser Benutzername ist bereits vergeben.'
            elif User.query.filter_by(email=email).first():
                error = 'Diese E-Mail-Adresse ist bereits registriert.'

            if error:
                flash(error, 'danger')
            else:
                user = User(username=username, email=email)
                user.set_password(password)
                db.session.add(user)
                db.session.commit()
                flash('Registrierung erfolgreich! Bitte melde dich jetzt an.', 'success')
                return redirect(url_for('login'))

        return render_template('register.html')

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for('index'))
        if request.method == 'POST':
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')
            remember = request.form.get('remember') == 'on'

            user = User.query.filter_by(username=username).first()
            if user is None or not user.check_password(password):
                flash('Ungültiger Benutzername oder Passwort.', 'danger')
            else:
                login_user(user, remember=remember)
                next_page = request.args.get('next')
                flash(f'Willkommen zurück, {user.username}!', 'success')
                return redirect(next_page or url_for('index'))

        return render_template('login.html')

    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        return redirect(url_for('index'))

    # ------------------------------------------------------------------
    # Auflagen Routes
    # ------------------------------------------------------------------

    @app.route('/auflagen')
    @login_required
    def auflagen():
        user_auflagen = current_user.auflagen.order_by(Auflage.erstellt_am.desc()).all()
        return render_template('auflagen.html', auflagen=user_auflagen)

    @app.route('/auflage/neu', methods=['GET', 'POST'])
    @login_required
    def auflage_neu():
        if request.method == 'POST':
            beschreibung = request.form.get('beschreibung', '').strip()
            grund = request.form.get('grund', '').strip()
            ziel = request.form.get('ziel', '').strip()
            zeitraum_start_str = request.form.get('zeitraum_start', '')
            zeitraum_ende_str = request.form.get('zeitraum_ende', '')
            erfahrungen = request.form.get('erfahrungen', '').strip()

            error = None
            if not beschreibung:
                error = 'Beschreibung ist erforderlich.'
            elif not grund:
                error = 'Grund ist erforderlich.'
            elif not ziel:
                error = 'Ziel ist erforderlich.'
            elif not zeitraum_start_str:
                error = 'Startdatum ist erforderlich.'
            else:
                try:
                    zeitraum_start = datetime.strptime(zeitraum_start_str, '%Y-%m-%d').date()
                    zeitraum_ende = datetime.strptime(zeitraum_ende_str, '%Y-%m-%d').date() if zeitraum_ende_str else None
                except ValueError:
                    error = 'Ungültiges Datumsformat. Verwende YYYY-MM-DD.'

            if error:
                flash(error, 'danger')
            else:
                auflage = Auflage(
                    beschreibung=beschreibung,
                    grund=grund,
                    ziel=ziel,
                    zeitraum_start=zeitraum_start,
                    zeitraum_ende=zeitraum_ende,
                    erfahrungen=erfahrungen,
                    user_id=current_user.id
                )
                db.session.add(auflage)
                db.session.commit()
                flash('Auflage erfolgreich erstellt.', 'success')
                return redirect(url_for('auflagen'))
        return render_template('auflage_neu.html')

    @app.route('/auflage/<int:id>')
    @login_required
    def auflage_detail(id):
        auflage = Auflage.query.get_or_404(id)
        if auflage.user_id != current_user.id:
            abort(403)
        rueckfaelle = auflage.rueckfaelle.order_by(Rueckfall.datum_uhrzeit.desc()).all()
        return render_template('auflage_detail.html', auflage=auflage, rueckfaelle=rueckfaelle)

    @app.route('/auflage/<int:id>/bearbeiten', methods=['GET', 'POST'])
    @login_required
    def auflage_bearbeiten(id):
        auflage = Auflage.query.get_or_404(id)
        if auflage.user_id != current_user.id:
            abort(403)
        if request.method == 'POST':
            auflage.beschreibung = request.form.get('beschreibung', '').strip()
            auflage.grund = request.form.get('grund', '').strip()
            auflage.ziel = request.form.get('ziel', '').strip()
            start_str = request.form.get('zeitraum_start', '')
            ende_str = request.form.get('zeitraum_ende', '')
            try:
                auflage.zeitraum_start = datetime.strptime(start_str, '%Y-%m-%d').date()
                auflage.zeitraum_ende = datetime.strptime(ende_str, '%Y-%m-%d').date() if ende_str else None
            except ValueError:
                flash('Ungültiges Datumsformat.', 'danger')
                return redirect(url_for('auflage_bearbeiten', id=id))
            auflage.erfahrungen = request.form.get('erfahrungen', '').strip()
            db.session.commit()
            flash('Auflage erfolgreich aktualisiert.', 'success')
            return redirect(url_for('auflage_detail', id=id))
        return render_template('auflage_bearbeiten.html', auflage=auflage)

    @app.route('/auflage/<int:id>/loeschen', methods=['POST'])
    @login_required
    def auflage_loeschen(id):
        auflage = Auflage.query.get_or_404(id)
        if auflage.user_id != current_user.id:
            abort(403)
        db.session.delete(auflage)
        db.session.commit()
        flash('Auflage erfolgreich gelöscht.', 'success')
        return redirect(url_for('auflagen'))

    # ------------------------------------------------------------------
    # Rückfälle Routes
    # ------------------------------------------------------------------

    @app.route('/auflage/<int:auflage_id>/rueckfall/neu', methods=['GET', 'POST'])
    @login_required
    def rueckfall_neu(auflage_id):
        auflage = Auflage.query.get_or_404(auflage_id)
        if auflage.user_id != current_user.id:
            abort(403)
        if request.method == 'POST':
            beschreibung = request.form.get('beschreibung', '').strip()
            gefuehle = request.form.get('gefuehle', '').strip()
            situation = request.form.get('situation', '').strip()
            lernpunkte = request.form.get('lernpunkte', '').strip()
            positives_verhalten = request.form.get('positives_verhalten', '').strip()
            error = None
            if not beschreibung:
                error = 'Beschreibung ist erforderlich.'
            elif not gefuehle:
                error = 'Gefühle sind erforderlich.'
            elif not situation:
                error = 'Situation ist erforderlich.'
            if error:
                flash(error, 'danger')
            else:
                rueckfall = Rueckfall(
                    beschreibung=beschreibung,
                    gefuehle=gefuehle,
                    situation=situation,
                    lernpunkte=lernpunkte,
                    positives_verhalten=positives_verhalten,
                    auflage_id=auflage_id,
                    user_id=current_user.id
                )
                db.session.add(rueckfall)
                db.session.commit()
                flash('Rückfall erfolgreich erfasst.', 'success')
                return redirect(url_for('auflage_detail', id=auflage_id))
        return render_template('rueckfall_neu.html', auflage=auflage)

    @app.route('/rueckfall/<int:id>/bearbeiten', methods=['GET', 'POST'])
    @login_required
    def rueckfall_bearbeiten(id):
        rueckfall = Rueckfall.query.get_or_404(id)
        if rueckfall.user_id != current_user.id:
            abort(403)
        if request.method == 'POST':
            rueckfall.beschreibung = request.form.get('beschreibung', '').strip()
            rueckfall.gefuehle = request.form.get('gefuehle', '').strip()
            rueckfall.situation = request.form.get('situation', '').strip()
            rueckfall.lernpunkte = request.form.get('lernpunkte', '').strip()
            rueckfall.positives_verhalten = request.form.get('positives_verhalten', '').strip()
            db.session.commit()
            flash('Rückfall erfolgreich aktualisiert.', 'success')
            return redirect(url_for('auflage_detail', id=rueckfall.auflage_id))
        return render_template('rueckfall_bearbeiten.html', rueckfall=rueckfall)

    @app.route('/rueckfall/<int:id>/loeschen', methods=['POST'])
    @login_required
    def rueckfall_loeschen(id):
        rueckfall = Rueckfall.query.get_or_404(id)
        if rueckfall.user_id != current_user.id:
            abort(403)
        auflage_id = rueckfall.auflage_id
        db.session.delete(rueckfall)
        db.session.commit()
        flash('Rückfall erfolgreich gelöscht.', 'success')
        return redirect(url_for('auflage_detail', id=auflage_id))

    # ------------------------------------------------------------------
    # Error handlers
    # ------------------------------------------------------------------
        return redirect(url_for('index'))

    # ------------------------------------------------------------------
    # Feed
    # ------------------------------------------------------------------

    @app.route('/')
    def index():
        page = request.args.get('page', 1, type=int)
        wortmeldungen = Wortmeldung.query.order_by(
            Wortmeldung.datum_uhrzeit.desc()
        ).paginate(page=page, per_page=10)
        return render_template('index.html', wortmeldungen=wortmeldungen)

    # ------------------------------------------------------------------
    # Profil
    # ------------------------------------------------------------------

    @app.route('/user/<username>')
    def profil(username):
        user = User.query.filter_by(username=username).first_or_404()
        page = request.args.get('page', 1, type=int)
        wortmeldungen = Wortmeldung.query.filter_by(user_id=user.id).order_by(
            Wortmeldung.datum_uhrzeit.desc()
        ).paginate(page=page, per_page=10)
        return render_template('profile.html', profil_user=user, wortmeldungen=wortmeldungen)

    # ------------------------------------------------------------------
    # Wortmeldungen
    # ------------------------------------------------------------------

    @app.route('/wortmeldung/neu', methods=['GET', 'POST'])
    @login_required
    def wortmeldung_neu():
        if request.method == 'POST':
            text = request.form.get('text', '').strip()
            if not text:
                flash('Die Wortmeldung darf nicht leer sein.', 'danger')
            elif len(text) > 2000:
                flash('Die Wortmeldung darf maximal 2000 Zeichen lang sein.', 'danger')
            else:
                wm = Wortmeldung(text=text, user_id=current_user.id)
                db.session.add(wm)
                db.session.commit()
                flash('Wortmeldung erfolgreich erstellt.', 'success')
                return redirect(url_for('wortmeldung_detail', wm_id=wm.id))
        return render_template('wortmeldung_neu.html')

    @app.route('/wortmeldung/<int:wm_id>')
    def wortmeldung_detail(wm_id):
        wm = Wortmeldung.query.get_or_404(wm_id)
        rueckmeldungen = Rueckmeldung.query.filter_by(
            wortmeldung_id=wm_id
        ).order_by(Rueckmeldung.datum_uhrzeit.asc()).all()
        return render_template('wortmeldung.html', wm=wm, rueckmeldungen=rueckmeldungen)

    @app.route('/wortmeldung/<int:wm_id>/loeschen', methods=['POST'])
    @login_required
    def wortmeldung_loeschen(wm_id):
        wm = Wortmeldung.query.get_or_404(wm_id)
        if wm.user_id != current_user.id:
            abort(403)
        db.session.delete(wm)
        db.session.commit()
        flash('Wortmeldung wurde gelöscht.', 'info')
        return redirect(url_for('profil', username=current_user.username))

    # ------------------------------------------------------------------
    # Rueckmeldungen
    # ------------------------------------------------------------------

    @app.route('/wortmeldung/<int:wm_id>/rueckmeldung', methods=['POST'])
    @login_required
    def rueckmeldung_erstellen(wm_id):
        Wortmeldung.query.get_or_404(wm_id)
        text = request.form.get('text', '').strip()
        if not text:
            flash('Die Rückmeldung darf nicht leer sein.', 'danger')
        elif len(text) > 1000:
            flash('Die Rückmeldung darf maximal 1000 Zeichen lang sein.', 'danger')
        else:
            rb = Rueckmeldung(text=text, user_id=current_user.id, wortmeldung_id=wm_id)
            db.session.add(rb)
            db.session.commit()
            flash('Rückmeldung erfolgreich gespeichert.', 'success')
        return redirect(url_for('wortmeldung_detail', wm_id=wm_id))

    @app.route('/rueckmeldung/<int:rb_id>/loeschen', methods=['POST'])
    @login_required
    def rueckmeldung_loeschen(rb_id):
        rb = Rueckmeldung.query.get_or_404(rb_id)
        wm_id = rb.wortmeldung_id
        if rb.user_id != current_user.id:
            abort(403)
        db.session.delete(rb)
        db.session.commit()
        flash('Rückmeldung wurde gelöscht.', 'info')
        return redirect(url_for('wortmeldung_detail', wm_id=wm_id))

    # ------------------------------------------------------------------
    # Error handlers
    # ------------------------------------------------------------------

    @app.errorhandler(403)
    def forbidden(e):
        return render_template(
            'error.html', code=403,
            message='Zugriff verweigert. Du hast keine Berechtigung für diese Aktion.'
        ), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template(
            'error.html', code=404,
            message='Seite nicht gefunden.'
        ), 404

    return app


app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
