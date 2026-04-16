import os
from datetime import datetime
from flask import Flask, render_template, redirect, url_for, flash, request, abort, send_file
import io
from fpdf import FPDF
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_wtf.csrf import CSRFProtect
from flask_migrate import Migrate
from models import db, User, Wortmeldung, Rueckmeldung, Auflage, Rueckfall, Treffen


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
        if auflage.user_id != current_user.id and not current_user.is_komiteeleitung:
            abort(403)
        rueckfaelle = auflage.rueckfaelle.order_by(Rueckfall.datum_uhrzeit.desc()).all()
        return render_template('auflage_detail.html', auflage=auflage, rueckfaelle=rueckfaelle)

    @app.route('/auflage/<int:id>/bearbeiten', methods=['GET', 'POST'])
    @login_required
    def auflage_bearbeiten(id):
        auflage = Auflage.query.get_or_404(id)
        if auflage.user_id != current_user.id and not current_user.is_komiteeleitung:
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
        if auflage.user_id != current_user.id and not current_user.is_komiteeleitung:
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
    # Treffen Routes
    # ------------------------------------------------------------------

    @app.route('/treffen')
    @login_required
    def treffen_liste():
        treffen_liste = Treffen.query.order_by(Treffen.datum.desc(), Treffen.uhrzeit.desc()).all()
        return render_template('treffen.html', treffen_liste=treffen_liste)

    @app.route('/treffen/neu', methods=['GET', 'POST'])
    @login_required
    def treffen_neu():
        if request.method == 'POST':
            datum_str = request.form.get('datum', '')
            uhrzeit_str = request.form.get('uhrzeit', '')
            ort = request.form.get('ort', '').strip()
            beschreibung = request.form.get('beschreibung', '').strip()

            error = None
            if not datum_str:
                error = 'Datum ist erforderlich.'
            elif not uhrzeit_str:
                error = 'Uhrzeit ist erforderlich.'
            elif not ort:
                error = 'Ort ist erforderlich.'
            else:
                try:
                    datum = datetime.strptime(datum_str, '%Y-%m-%d').date()
                    uhrzeit = datetime.strptime(uhrzeit_str, '%H:%M').time()
                except ValueError:
                    error = 'Ungültiges Datums- oder Zeitformat.'

            if error:
                flash(error, 'danger')
            else:
                treffen = Treffen(
                    datum=datum,
                    uhrzeit=uhrzeit,
                    ort=ort,
                    beschreibung=beschreibung
                )
                db.session.add(treffen)
                db.session.commit()
                flash('Treffen erfolgreich erstellt.', 'success')
                return redirect(url_for('treffen_liste'))
        return render_template('treffen_neu.html')

    @app.route('/treffen/<int:id>')
    @login_required
    def treffen_detail(id):
        treffen = Treffen.query.get_or_404(id)
        wortmeldungen = treffen.wortmeldungen.order_by(Wortmeldung.datum_uhrzeit.asc()).all()
        return render_template('treffen_detail.html', treffen=treffen, wortmeldungen=wortmeldungen)

    @app.route('/treffen/<int:id>/bearbeiten', methods=['GET', 'POST'])
    @login_required
    def treffen_bearbeiten(id):
        treffen = Treffen.query.get_or_404(id)
        # TODO: Zugriffskontrolle (nur Komiteeleitung)
        if request.method == 'POST':
            datum_str = request.form.get('datum', '')
            uhrzeit_str = request.form.get('uhrzeit', '')
            ort = request.form.get('ort', '').strip()
            beschreibung = request.form.get('beschreibung', '').strip()
            try:
                treffen.datum = datetime.strptime(datum_str, '%Y-%m-%d').date()
                treffen.uhrzeit = datetime.strptime(uhrzeit_str, '%H:%M').time()
            except ValueError:
                flash('Ungültiges Datums- oder Zeitformat.', 'danger')
                return redirect(url_for('treffen_bearbeiten', id=id))
            treffen.ort = ort
            treffen.beschreibung = beschreibung
            db.session.commit()
            flash('Treffen erfolgreich aktualisiert.', 'success')
            return redirect(url_for('treffen_detail', id=id))
        return render_template('treffen_bearbeiten.html', treffen=treffen)

    @app.route('/treffen/<int:id>/loeschen', methods=['POST'])
    @login_required
    def treffen_loeschen(id):
        treffen = Treffen.query.get_or_404(id)
        # TODO: Zugriffskontrolle (nur Komiteeleitung)
        db.session.delete(treffen)
        db.session.commit()
        flash('Treffen erfolgreich gelöscht.', 'success')
        return redirect(url_for('treffen_liste'))

    @app.route('/treffen/<int:treffen_id>/wortmeldung/neu', methods=['GET', 'POST'])
    @login_required
    def wortmeldung_treffen_neu(treffen_id):
        treffen = Treffen.query.get_or_404(treffen_id)
        if request.method == 'POST':
            text = request.form.get('text', '').strip()
            kategorie = request.form.get('kategorie', 'vorfall')
            # Status bleibt 'offen' als Default
            error = None
            if not text:
                error = 'Text der Wortmeldung ist erforderlich.'
            if error:
                flash(error, 'danger')
            else:
                wortmeldung = Wortmeldung(
                    text=text,
                    kategorie=kategorie,
                    status='offen',
                    user_id=current_user.id,
                    treffen_id=treffen_id
                )
                db.session.add(wortmeldung)
                db.session.commit()
                flash('Wortmeldung erfolgreich angemeldet.', 'success')
                return redirect(url_for('treffen_detail', id=treffen_id))
        return render_template('wortmeldung_treffen_neu.html', treffen=treffen)

    # ------------------------------------------------------------------
    # Error handlers
    # ------------------------------------------------------------------

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
        # Nur Eigentümer oder Komiteeleitung darf löschen
        if wm.user_id != current_user.id and not current_user.is_komiteeleitung:
            abort(403)
        db.session.delete(wm)
        db.session.commit()
        flash('Wortmeldung wurde gelöscht.', 'info')
        next_page = request.form.get('next') or url_for('profil', username=current_user.username)
        return redirect(next_page)

    @app.route('/wortmeldung/<int:id>/bearbeiten', methods=['GET', 'POST'])
    @login_required
    def wortmeldung_bearbeiten(id):
        wortmeldung = Wortmeldung.query.get_or_404(id)
        # Zugriffskontrolle: Nur Eigentümer oder Komiteeleitung
        if wortmeldung.user_id != current_user.id and not current_user.is_komiteeleitung:
            abort(403)
        
        if request.method == 'POST':
            # Hier kommt Bearbeitungslogik (für spätere Implementierung)
            flash('Bearbeitungsfunktion noch nicht implementiert.', 'warning')
            next_page = request.form.get('next') or url_for('komiteeleitung')
            return redirect(next_page)
        
        # GET: Zeige Bearbeitungsformular (Platzhalter)
        return render_template('wortmeldung_bearbeiten.html', wortmeldung=wortmeldung)

    @app.route('/wortmeldung/<int:id>/verschieben', methods=['POST'])
    def wortmeldung_verschieben(id):
        wortmeldung = Wortmeldung.query.get_or_404(id)
        treffen_id = request.form.get('treffen_id', type=int)
        
        if treffen_id:
            treffen = Treffen.query.get_or_404(treffen_id)
            wortmeldung.treffen_id = treffen_id
            db.session.commit()
            flash(f'Wortmeldung #{id} wurde zu Treffen am {treffen.datum.strftime("%d.%m.%Y")} verschoben.', 'success')
        else:
            flash('Bitte ein Treffen auswählen.', 'warning')
        
        next_page = request.form.get('next') or url_for('komiteeleitung')
        return redirect(next_page)

    # ------------------------------------------------------------------
    # Rueckmeldungen

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

    # ------------------------------------------------------------------
    # Komiteeleitung Decorator
    # ------------------------------------------------------------------
    def komiteeleitung_required(f):
        from functools import wraps
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('login'))
            if not current_user.is_komiteeleitung:
                flash('Zugriff verweigert: Nur Komiteeleitung darf diese Seite aufrufen.', 'danger')
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return decorated_function

    # ------------------------------------------------------------------
    # Komiteeleitung Routes
    # ------------------------------------------------------------------
    @app.route('/komiteeleitung')
    @login_required
    @komiteeleitung_required
    def komiteeleitung():
        # Alle Treffen für Filter-Links
        alle_treffen = Treffen.query.order_by(Treffen.datum.desc()).all()
        
        # Filter nach Treffen, falls Parameter vorhanden
        treffen_id = request.args.get('treffen_id', type=int)
        query = Wortmeldung.query
        
        if treffen_id:
            query = query.filter_by(treffen_id=treffen_id)
            aktuelles_treffen = Treffen.query.get(treffen_id)
        else:
            aktuelles_treffen = None
        
        wortmeldungen = query.order_by(Wortmeldung.datum_uhrzeit.desc()).all()
        return render_template('komiteeleitung.html', 
                               wortmeldungen=wortmeldungen,
                               alle_treffen=alle_treffen,
                               aktuelles_treffen=aktuelles_treffen,
                               treffen_id=treffen_id)

    @app.route('/wortmeldung/<int:id>/status', methods=['POST'])
    @login_required
    @komiteeleitung_required
    def wortmeldung_status(id):
        wortmeldung = Wortmeldung.query.get_or_404(id)
        new_status = request.form.get('status')
        if new_status in ['offen', 'erledigt', 'zurueckgestellt', 'geloescht']:
            wortmeldung.status = new_status
            db.session.commit()
            flash(f'Status von Wortmeldung #{id} wurde auf "{new_status}" geändert.', 'success')
        else:
            flash('Ungültiger Status.', 'danger')
        next_page = request.form.get('next') or url_for('komiteeleitung')
        return redirect(next_page)

    @app.route('/komiteeleitung/auflagen')
    @login_required
    @komiteeleitung_required
    def komiteeleitung_auflagen():
        alle_auflagen = Auflage.query.order_by(Auflage.erstellt_am.desc()).all()
        return render_template('komiteeleitung_auflagen.html', auflagen=alle_auflagen)

    @app.route('/komiteeleitung/auflage/neu', methods=['GET', 'POST'])
    @login_required
    @komiteeleitung_required
    def komiteeleitung_auflage_neu():
        users = User.query.order_by(User.username).all()
        if request.method == 'POST':
            target_user_id = request.form.get('user_id', type=int)
            beschreibung = request.form.get('beschreibung', '').strip()
            grund = request.form.get('grund', '').strip()
            ziel = request.form.get('ziel', '').strip()
            zeitraum_start_str = request.form.get('zeitraum_start', '')
            zeitraum_ende_str = request.form.get('zeitraum_ende', '')
            erfahrungen = request.form.get('erfahrungen', '').strip()

            error = None
            if not target_user_id:
                error = 'Bitte einen Benutzer auswählen.'
            elif not beschreibung:
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
                    user_id=target_user_id
                )
                db.session.add(auflage)
                db.session.commit()
                flash('Auflage erfolgreich für Benutzer erstellt.', 'success')
                return redirect(url_for('komiteeleitung_auflagen'))
        
        return render_template('komiteeleitung_auflage_neu.html', users=users)

    @app.route('/komiteeleitung/treffen/<int:id>/pdf')
    @login_required
    @komiteeleitung_required
    def treffen_pdf(id):
        treffen = Treffen.query.get_or_404(id)
        wortmeldungen = Wortmeldung.query.filter_by(treffen_id=id).order_by(Wortmeldung.datum_uhrzeit.asc()).all()

        class PDF(FPDF):
            def header(self):
                self.set_font('helvetica', 'B', 15)
                self.cell(0, 10, 'Wortmeldungen Protokoll', ln=True, align='C')
                self.set_font('helvetica', 'I', 10)
                self.cell(0, 10, f'Treffen am {treffen.datum.strftime("%d.%m.%Y")} in {treffen.ort}', ln=True, align='C')
                self.ln(10)

            def footer(self):
                self.set_y(-15)
                self.set_font('helvetica', 'I', 8)
                self.cell(0, 10, f'Seite {self.page_no()}', align='C')

        pdf = PDF()
        pdf.add_page()
        pdf.set_font('helvetica', '', 12)

        if not wortmeldungen:
            pdf.cell(0, 10, 'Keine Wortmeldungen für dieses Treffen vorhanden.', ln=True)
        else:
            for wm in wortmeldungen:
                # Header for each Wortmeldung
                pdf.set_font('helvetica', 'B', 12)
                pdf.set_fill_color(240, 240, 240)
                pdf.cell(0, 10, f'Wortmeldung #{wm.id} - von {wm.autor.username}', ln=True, fill=True)
                
                pdf.set_font('helvetica', 'I', 10)
                pdf.cell(0, 8, f'Kategorie: {wm.kategorie} | Status: {wm.status} | Zeit: {wm.datum_uhrzeit.strftime("%H:%M")}', ln=True)
                
                pdf.set_font('helvetica', '', 11)
                # Multi-cell for the text to handle wrapping
                pdf.multi_cell(0, 8, wm.text)
                
                # Replies (Rückmeldungen)
                replies = wm.rueckmeldungen.order_by(Rueckmeldung.datum_uhrzeit.asc()).all()
                if replies:
                    pdf.ln(2)
                    pdf.set_font('helvetica', 'B', 10)
                    pdf.cell(0, 8, '  Rückmeldungen:', ln=True)
                    pdf.set_font('helvetica', '', 10)
                    for rb in replies:
                        pdf.set_x(20) # Indent replies
                        reply_text = f'- {rb.autor.username} ({rb.datum_uhrzeit.strftime("%H:%M")}): {rb.text}'
                        pdf.multi_cell(0, 6, reply_text)
                
                pdf.ln(5)
                pdf.cell(0, 0, '', 'T', ln=True) # Horizontal line
                pdf.ln(5)

        # Output the PDF to a buffer
        pdf_output = io.BytesIO()
        pdf_bytes = pdf.output()
        pdf_output.write(pdf_bytes)
        pdf_output.seek(0)
        
        filename = f"Protokoll_Treffen_{treffen.datum.strftime('%Y-%m-%d')}.pdf"
        return send_file(
            pdf_output,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )

    return app


app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5002)
