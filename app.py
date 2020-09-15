import os
from os import getenv
from os.path import join, dirname, splitext
from dotenv import load_dotenv
from flask import Flask, render_template, url_for, request, redirect, session, flash
from mysql.connector import connect
from werkzeug.security import generate_password_hash, check_password_hash
from random import randint

# Create the .env file's path and load it
load_dotenv(join(dirname(__file__), '.env'))

konekcija = connect(
    host = getenv('DB_Host'),
    user = getenv('DB_User'),
    passwd = getenv('DB_Pass'),
    database = getenv('DB_Db')
)
kursor = konekcija.cursor(dictionary = True)
def ulogovan():
	if 'ulogovani_korisnik' in session:
		return True
	else: return False
app = Flask(__name__)
app.secret_key = getenv('Cookie_secret')
#u index ruti koristim VIEW
@app.route('/')
def index():
    if ulogovan():
        sql = 'SELECT * FROM svi_oglasi WHERE svi_oglasi.korisnik_id != %s'
        korisnik_id = (session['ulogovani_korisnik'],)
        kursor.execute(sql, korisnik_id)
        oglasi=kursor.fetchall()
        print(oglasi)
        konekcija.commit()
        return render_template('ulogovan.html', oglasi=oglasi)
    else:
        sql = 'SELECT * FROM svi_oglasi'
        kursor.execute(sql)
        oglasi=kursor.fetchall()
        print(oglasi)
        konekcija.commit()
        return render_template('neulogovan.html', oglasi=oglasi)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")
    elif request.method == "POST":
        forma = request.form
        upit = "SELECT * FROM korisnik WHERE email=%s"
        vrednost = (forma["email"],)
        kursor.execute(upit, vrednost)
        korisnik = kursor.fetchone()
        if check_password_hash(korisnik["lozinka"], forma["lozinka"]):
            session["ulogovani_korisnik"] = str(korisnik['id'])
            return redirect(url_for("index"))
        else:
            return render_template("login.html")

@app.route('/logout')
def logout():
    session.pop('ulogovani_korisnik', None)
    return redirect(url_for('login'))

@app.route('/registracija', methods = ['GET', 'POST'])
def registracija():
    if request.method == 'GET':
        return render_template('registracija.html')

    podaci = request.form
    sql = '''INSERT INTO 
             korisnik (ime, prezime, email, kontakt, korisnicko_ime, mesto, lozinka) 
             VALUES (%s,%s,%s,%s,%s,%s,%s)
          '''
    hes = generate_password_hash(podaci['lozinka'])
    vrednosti = (podaci['ime'], podaci['prezime'], podaci['email'], podaci['kontakt'], podaci['korisnicko_ime'], podaci['mesto'], hes)
    kursor.execute(sql, vrednosti)
    konekcija.commit()

    return redirect(url_for('login'))
#i ovde koristim view
@app.route('/moji_oglasi')
def moji_oglasi():
    if ulogovan():
        sql = '''SELECT *, DAYNAME(datum) AS dan
             FROM svi_oglasi
             WHERE svi_oglasi.korisnik_id = %s 
          '''
        korisnik_id = (session['ulogovani_korisnik'],)
        kursor.execute(sql, korisnik_id)
        oglasi = kursor.fetchall()
        konekcija.commit()
        return render_template('ulogovan_moji_oglasi.html', oglasi =oglasi)
    else:
        return redirect(url_for('login'))
    
#procedura za trazenje mesta i procedura za novi oglas
@app.route('/oglas_novi', methods = ["GET", "POST"])
def oglas_novi():
     if ulogovan:
        if request.method == 'GET':
            return render_template('oglas_novi.html')

        if request.files['slika'].filename != '':
            name = request.files['slika'].filename
            naziv, ext = splitext(name)
            naziv_fajla = naziv + '-' + str(randint(0, 999999)) + ext
            with open(join('static', 'slike', naziv_fajla), 'wb') as file:
                upload = request.files['slika']
                upload.save(file)
            pod = request.form
            inp_arg=str(session['ulogovani_korisnik'],)
            out_arg=""
            print(inp_arg[0])
            kursor.callproc('Nadji_mesto', (inp_arg, out_arg))
            konekcija.commit()
            mesto=out_arg
            val = (pod['naslov'], pod['tekst'], naziv_fajla, session['ulogovani_korisnik'], mesto, pod['kategorija'], int(pod['polovno']), int(pod['cena']))
            kursor.callproc('Novi_oglas', val)
        else:
            flash('Morate uneti sliku')
        konekcija.commit()
        return redirect(url_for('index'))
     else:
        return redirect(url_for('login'))

@app.route('/oglas_izmena/<id>', methods= ["GET", "POST"])
def oglas_izmena(id):
    if ulogovan():
        if request.method == 'GET':
            sql='SELECT * FROM tbl_oglasi WHERE id = %s'
            kursor.execute(sql, (id,))
            oglas=kursor.fetchone()
            konekcija.commit()
            return render_template('oglas_izmena.html', oglas=oglas)
        else:
            sql = 'UPDATE tbl_oglasi SET naslov = %s, tekst = %s, kategorija = %s, polovno = %s, cena = %s'
            pod = ()
            forma = request.form
            pod += (forma['naslov'], forma['tekst'],forma['kategorija'],forma['polovno'], forma['cena'], id,)
            if request.files['slika'].filename != '':
                name = request.files['slika'].filename
                naziv, ext = splitext(name)
                naziv_fajla = naziv + '-' + str(randint(0, 999999)) + ext
                with open(join('static', 'slike', naziv_fajla), 'wb') as file:
                    upload = request.files['slika']
                    upload.save(file)
                sql += ', slika = %s '
                pod += (naziv_fajla,)
            sql += 'WHERE id = %s'
            kursor.execute(sql, pod)
            konekcija.commit()
            return redirect(url_for('index'))
    else:
        return redirect(url_for('login'))
    
#procedura za brisanje
@app.route('/oglas_brisanje/<id>')
def oglas_brisanje(id):
    if ulogovan():
        in_arg=id
        out_arg=""
        kursor.callproc('Brisanje_oglasa',(in_arg, out_arg))
        os.chmod('static/slike/'+out_arg, 0o777)
        try:
            os.remove('static/slike/'+out_arg)
        except: redirect(url_for('index'))
        konekcija.commit()
        return redirect(url_for('index'))
    else:
        return redirect('login')




app.run(debug = True)


