from flask import Flask, render_template, request, redirect, session
import sqlite3

app = Flask(__name__)
app.secret_key = "12345"

# VERİTABANI BAĞLANTISI
def get_db():
    conn = sqlite3.connect("hospital.db")
    conn.row_factory = sqlite3.Row
    return conn

# VERİTABANI OLUŞTURMA VE ÖRNEK VERİLER
def init_db():
    conn = get_db()

    # Kullanıcılar
    conn.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT
    )
    """)

    # Hastalar
    conn.execute("""
    CREATE TABLE IF NOT EXISTS hastalar(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ad TEXT,
        soyad TEXT
    )
    """)

    # Doktorlar
    conn.execute("""
    CREATE TABLE IF NOT EXISTS doktorlar(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ad TEXT,
        brans TEXT
    )
    """)

    # Randevular
    conn.execute("""
    CREATE TABLE IF NOT EXISTS randevular(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        hasta_id INTEGER,
        doktor_id INTEGER,
        tarih TEXT
    )
    """)

    # Branşlar
    conn.execute("""
    CREATE TABLE IF NOT EXISTS branslar(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ad TEXT
    )
    """)

    # Varsayılan admin
    conn.execute("INSERT OR IGNORE INTO users(username,password) VALUES('admin','senkron2345?')")

    # Örnek Branşlar
    branslar = ['Kardiyoloji','Göz','Dermatoloji','Ortopedi','Nöroloji']
    for b in branslar:
        conn.execute("INSERT OR IGNORE INTO branslar(ad) VALUES(?)", (b,))

    # Örnek Doktorlar
    doktorlar = [
        ('Dr. Ahmet Yılmaz','Kardiyoloji'),
        ('Dr. Elif Demir','Göz'),
        ('Dr. Mehmet Kaya','Dermatoloji'),
        ('Dr. Ayşe Şahin','Ortopedi'),
        ('Dr. Can Özkan','Nöroloji')
    ]
    for ad, br in doktorlar:
        conn.execute("INSERT OR IGNORE INTO doktorlar(ad,brans) VALUES(?,?)", (ad, br))

    # Örnek Hastalar
    hastalar = [
        ('Ali','Demir'),
        ('Ayşe','Yılmaz'),
        ('Mehmet','Kaya'),
        ('Elif','Şahin'),
        ('Can','Özkan')
    ]
    for ad, soyad in hastalar:
        conn.execute("INSERT OR IGNORE INTO hastalar(ad,soyad) VALUES(?,?)", (ad, soyad))

    # Örnek Randevular
    randevular = [
        (1,1,'2026-03-10 10:00'),
        (2,2,'2026-03-10 11:00'),
        (3,3,'2026-03-11 09:30'),
        (4,4,'2026-03-11 10:30'),
        (5,5,'2026-03-12 14:00')
    ]
    for hasta_id, doktor_id, tarih in randevular:
        conn.execute("INSERT OR IGNORE INTO randevular(hasta_id,doktor_id,tarih) VALUES(?,?,?)",
                     (hasta_id, doktor_id, tarih))

    conn.commit()


# ANA SAYFA
@app.route("/")
def index():
    return redirect("/login")


# LOGIN
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db()
        user = conn.execute(
            "SELECT * FROM users WHERE username=? AND password=?",
            (username, password)
        ).fetchone()

        if user:
            session["user"] = username
            return redirect("/dashboard")
        else:
            return render_template("login.html", error="Kullanıcı adı veya şifre hatalı")

    return render_template("login.html")


# DASHBOARD
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/login")

    conn = get_db()

    # Toplam sayılar
    hasta_sayisi = conn.execute("SELECT COUNT(*) FROM hastalar").fetchone()[0]
    doktor_sayisi = conn.execute("SELECT COUNT(*) FROM doktorlar").fetchone()[0]
    brans_sayisi = conn.execute("SELECT COUNT(*) FROM branslar").fetchone()[0]
    randevu_sayisi = conn.execute("SELECT COUNT(*) FROM randevular").fetchone()[0]

    # Branş bazlı randevu sayısı
    branslar = conn.execute("""
        SELECT d.brans, COUNT(r.id) as sayi
        FROM randevular r
        JOIN doktorlar d ON r.doktor_id = d.id
        GROUP BY d.brans
    """).fetchall()
    brans_isimleri = [b["brans"] for b in branslar]
    brans_sayilari = [b["sayi"] for b in branslar]

    # Doktor bazlı randevu sayısı
    doktorlar = conn.execute("""
        SELECT d.ad || ' (' || d.brans || ')' AS ad, COUNT(r.id) as sayi
        FROM randevular r
        JOIN doktorlar d ON r.doktor_id = d.id
        GROUP BY d.id
    """).fetchall()
    doktor_isimleri = [d["ad"] for d in doktorlar]
    doktor_sayilari = [d["sayi"] for d in doktorlar]

    return render_template(
        "dashboard.html",
        hasta_sayisi=hasta_sayisi,
        doktor_sayisi=doktor_sayisi,
        brans_sayisi=brans_sayisi,
        randevu_sayisi=randevu_sayisi,
        brans_isimleri=brans_isimleri,
        brans_sayilari=brans_sayilari,
        doktor_isimleri=doktor_isimleri,
        doktor_sayilari=doktor_sayilari
    )


# HASTA LİSTELEME
@app.route("/hastalar")
def hastalar():
    if "user" not in session:
        return redirect("/login")

    search = request.args.get("search")
    conn = get_db()
    if search:
        hastalar = conn.execute(
            "SELECT * FROM hastalar WHERE ad LIKE ? OR soyad LIKE ?",
            ("%" + search + "%", "%" + search + "%")
        ).fetchall()
    else:
        hastalar = conn.execute("SELECT * FROM hastalar").fetchall()

    return render_template("index.html", hastalar=hastalar)


# HASTA EKLEME
@app.route("/ekle", methods=["GET", "POST"])
def ekle():
    if "user" not in session:
        return redirect("/login")
    if request.method == "POST":
        ad = request.form["ad"]
        soyad = request.form["soyad"]
        conn = get_db()
        conn.execute("INSERT INTO hastalar(ad,soyad) VALUES(?,?)", (ad, soyad))
        conn.commit()
        return redirect("/hastalar")
    return render_template("ekle.html")


# HASTA SİLME
@app.route("/sil/<int:id>")
def sil(id):
    if "user" not in session:
        return redirect("/login")
    conn = get_db()
    conn.execute("DELETE FROM hastalar WHERE id=?", (id,))
    conn.commit()
    return redirect("/hastalar")


# HASTA DÜZENLEME
@app.route("/duzenle/<int:id>", methods=["GET", "POST"])
def duzenle(id):
    if "user" not in session:
        return redirect("/login")
    conn = get_db()
    if request.method == "POST":
        ad = request.form["ad"]
        soyad = request.form["soyad"]
        conn.execute("UPDATE hastalar SET ad=?, soyad=? WHERE id=?", (ad, soyad, id))
        conn.commit()
        return redirect("/hastalar")
    hasta = conn.execute("SELECT * FROM hastalar WHERE id=?", (id,)).fetchone()
    return render_template("duzenle.html", hasta=hasta)


# ŞİFREMİ UNUTTUM
@app.route("/sifremi_unuttum", methods=["GET", "POST"])
def sifremi_unuttum():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        password2 = request.form["password2"]

        if password != password2:
            return render_template("sifremi_unuttum.html", error="Şifreler uyuşmuyor")

        conn = get_db()
        conn.execute("UPDATE users SET password=? WHERE username=?", (password, username))
        conn.commit()
        return render_template("sifremi_unuttum.html", success="Başarı ile şifreniz değiştirildi")

    return render_template("sifremi_unuttum.html")


# BRANŞLAR
@app.route("/branslar", methods=["GET", "POST"])
def branslar():
    if "user" not in session:
        return redirect("/login")
    conn = get_db()
    if request.method == "POST":
        ad = request.form["ad"]
        conn.execute("INSERT INTO branslar(ad) VALUES(?)", (ad,))
        conn.commit()
    branslar = conn.execute("SELECT * FROM branslar").fetchall()
    return render_template("branslar.html", branslar=branslar)


# DOKTOR EKLE
@app.route("/doktor_ekle", methods=["GET", "POST"])
def doktor_ekle():
    if "user" not in session:
        return redirect("/login")
    conn = get_db()
    if request.method == "POST":
        ad = request.form["ad"]
        brans = request.form["brans"]
        conn.execute("INSERT INTO doktorlar(ad,brans) VALUES(?,?)", (ad, brans))
        conn.commit()
        return redirect("/dashboard")
    branslar = conn.execute("SELECT * FROM branslar").fetchall()
    return render_template("doktor_ekle.html", branslar=branslar)


# RANDEVU LİSTELEME
@app.route("/randevular")
def randevular():
    if "user" not in session:
        return redirect("/login")
    conn = get_db()
    randevular = conn.execute("""
        SELECT r.id, h.ad AS hasta_ad, h.soyad AS hasta_soyad,
               d.ad AS doktor_ad, d.brans, r.tarih
        FROM randevular r
        JOIN hastalar h ON r.hasta_id = h.id
        JOIN doktorlar d ON r.doktor_id = d.id
    """).fetchall()
    return render_template("randevular.html", randevular=randevular)


# RANDEVU EKLEME
@app.route("/randevu_ekle", methods=["GET","POST"])
def randevu_ekle():
    if "user" not in session:
        return redirect("/login")
    conn = get_db()
    hastalar = conn.execute("SELECT * FROM hastalar").fetchall()
    doktorlar = conn.execute("SELECT * FROM doktorlar").fetchall()
    if request.method == "POST":
        hasta_id = request.form["hasta_id"]
        doktor_id = request.form["doktor_id"]
        tarih = request.form["tarih"]
        conn.execute(
            "INSERT INTO randevular(hasta_id,doktor_id,tarih) VALUES(?,?,?)",
            (hasta_id, doktor_id, tarih)
        )
        conn.commit()
        return redirect("/randevular")
    return render_template("randevu_ekle.html", hastalar=hastalar, doktorlar=doktorlar)


# RANDEVU SİLME
@app.route("/randevu_sil/<int:id>")
def randevu_sil(id):
    if "user" not in session:
        return redirect("/login")
    conn = get_db()
    conn.execute("DELETE FROM randevular WHERE id=?", (id,))
    conn.commit()
    return redirect("/randevular")


# ÇIKIŞ
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


if __name__ == "__main__":
    init_db()
    app.run(debug=True)