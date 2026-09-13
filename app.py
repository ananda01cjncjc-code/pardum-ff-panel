import os, sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, flash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret")
DB = "tournament.db"
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

def db():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    c = db()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS tournaments(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL, entry_fee TEXT DEFAULT 'Free',
      status TEXT DEFAULT 'Open', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS registrations(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      tournament_id INTEGER NOT NULL, player_name TEXT NOT NULL,
      uid TEXT NOT NULL, telegram_id TEXT, status TEXT DEFAULT 'Pending',
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY(tournament_id) REFERENCES tournaments(id)
    );
    """)
    c.commit(); c.close()

@app.route("/")
def home():
    c=db()
    tournaments=c.execute("SELECT * FROM tournaments ORDER BY id DESC").fetchall()
    c.close()
    return render_template("home.html", tournaments=tournaments)

@app.post("/register")
def register():
    tid=request.form["tournament_id"]
    name=request.form["player_name"].strip()
    uid=request.form["uid"].strip()
    tg=request.form.get("telegram_id","").strip()
    if not name or not uid:
        flash("Name aur UID required hai.")
        return redirect(url_for("home"))
    c=db()
    c.execute("INSERT INTO registrations(tournament_id,player_name,uid,telegram_id) VALUES(?,?,?,?)",
              (tid,name,uid,tg))
    c.commit(); c.close()
    flash("Registration submit ho gaya!")
    return redirect(url_for("home"))

@app.route("/admin/login", methods=["GET","POST"])
def login():
    if request.method=="POST":
        if request.form.get("password")==ADMIN_PASSWORD:
            session["admin"]=True
            return redirect(url_for("admin"))
        flash("Wrong password")
    return render_template("login.html")

@app.route("/admin/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

def admin_required():
    return session.get("admin") is True

@app.route("/admin")
def admin():
    if not admin_required(): return redirect(url_for("login"))
    c=db()
    tournaments=c.execute("SELECT * FROM tournaments ORDER BY id DESC").fetchall()
    regs=c.execute("""SELECT registrations.*, tournaments.name tournament_name
                      FROM registrations JOIN tournaments ON tournaments.id=registrations.tournament_id
                      ORDER BY registrations.id DESC""").fetchall()
    c.close()
    return render_template("admin.html", tournaments=tournaments, regs=regs)

@app.post("/admin/tournament")
def add_tournament():
    if not admin_required(): return redirect(url_for("login"))
    c=db()
    c.execute("INSERT INTO tournaments(name,entry_fee,status) VALUES(?,?,?)",
              (request.form["name"], request.form.get("entry_fee","Free"), "Open"))
    c.commit(); c.close()
    return redirect(url_for("admin"))

@app.post("/admin/registration/<int:rid>/<action>")
def registration_action(rid, action):
    if not admin_required(): return redirect(url_for("login"))
    status = "Approved" if action=="approve" else "Rejected"
    c=db(); c.execute("UPDATE registrations SET status=? WHERE id=?", (status,rid))
    c.commit(); c.close()
    return redirect(url_for("admin"))

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",5000)), debug=False)
