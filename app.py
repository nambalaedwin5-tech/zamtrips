from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
import sqlite3
from datetime import datetime, timedelta
import csv
import io

app = Flask(__name__)
app.secret_key = "secret123"

USERNAME = "admin"
PASSWORD = "1234"

# ---------- DB ----------
def get_db():
    conn = sqlite3.connect("bookings.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS bookings(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT,
            destination TEXT,
            date TEXT,
            status TEXT
        )
    ''')
    conn.commit()
    conn.close()

# ---------- LOGIN ----------
@app.route('/', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        u = request.form['username'].strip()
        p = request.form['password'].strip()

        if u == USERNAME and p == PASSWORD:
            session['user'] = u
            flash("✅ Login successful")
            return redirect(url_for('dashboard'))
        else:
            flash("❌ Invalid login")

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

def protect():
    if 'user' not in session:
        return False
    return True

# ---------- CREATE ----------
@app.route('/booking')
def booking():
    if not protect(): return redirect('/')
    return render_template('booking.html')

@app.route('/submit-booking', methods=['POST'])
def submit():
    if not protect(): return redirect('/')

    conn = get_db()
    conn.execute(
        "INSERT INTO bookings(name,email,destination,date,status) VALUES(?,?,?,?,?)",
        (
            request.form['name'],
            request.form['email'],
            request.form['destination'],
            request.form['date'],
            "Pending"
        )
    )
    conn.commit()
    conn.close()

    flash("✅ Booking created")
    return redirect('/dashboard')

# ---------- DASHBOARD ----------
@app.route('/dashboard')
def dashboard():
    if not protect(): return redirect('/')

    conn = get_db()

    search = request.args.get('search','')
    status = request.args.get('status','')
    sort = request.args.get('sort','id')

    query = "SELECT * FROM bookings WHERE 1=1"
    params = []

    if search:
        query += " AND (name LIKE ? OR email LIKE ?)"
        params += [f"%{search}%", f"%{search}%"]

    if status:
        query += " AND status=?"
        params.append(status)

    if sort == "date":
        query += " ORDER BY date"
    elif sort == "status":
        query += " ORDER BY status"

    rows = conn.execute(query, params).fetchall()

    today = datetime.today().date()
    upcoming = today + timedelta(days=7)

    bookings = []
    for r in rows:
        d = dict(r)
        booking_date = datetime.strptime(d['date'], "%Y-%m-%d").date()

        if booking_date == today:
            d['highlight'] = "today"
        elif today < booking_date <= upcoming:
            d['highlight'] = "upcoming"
        else:
            d['highlight'] = ""

        bookings.append(d)

    total = conn.execute("SELECT COUNT(*) FROM bookings").fetchone()[0]
    pending = conn.execute("SELECT COUNT(*) FROM bookings WHERE status='Pending'").fetchone()[0]
    confirmed = conn.execute("SELECT COUNT(*) FROM bookings WHERE status='Confirmed'").fetchone()[0]
    cancelled = conn.execute("SELECT COUNT(*) FROM bookings WHERE status='Cancelled'").fetchone()[0]

    conn.close()

    return render_template(
        "view_booking.html",
        bookings=bookings,
        total=total,
        pending=pending,
        confirmed=confirmed,
        cancelled=cancelled
    )

# ---------- STATUS ----------
@app.route('/status/<int:id>/<string:s>')
def status(id, s):
    conn = get_db()
    conn.execute("UPDATE bookings SET status=? WHERE id=?", (s, id))
    conn.commit()
    conn.close()
    flash("✅ Status updated")
    return redirect('/dashboard')

# ---------- DELETE ----------
@app.route('/delete/<int:id>')
def delete(id):
    conn = get_db()
    conn.execute("DELETE FROM bookings WHERE id=?", (id,))
    conn.commit()
    conn.close()
    flash("🗑 Deleted")
    return redirect('/dashboard')

# ---------- EDIT ----------
@app.route('/edit/<int:id>')
def edit(id):
    conn = get_db()
    b = conn.execute("SELECT * FROM bookings WHERE id=?", (id,)).fetchone()
    conn.close()
    return render_template("edit_booking.html", booking=b)

@app.route('/update/<int:id>', methods=['POST'])
def update(id):
    conn = get_db()
    conn.execute("""
        UPDATE bookings
        SET name=?, email=?, destination=?, date=?
        WHERE id=?
    """, (
        request.form['name'],
        request.form['email'],
        request.form['destination'],
        request.form['date'],
        id
    ))
    conn.commit()
    conn.close()
    flash("✏️ Updated")
    return redirect('/dashboard')

# ---------- EXPORT ----------
@app.route('/export')
def export():
    conn = get_db()
    rows = conn.execute("SELECT * FROM bookings").fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID","Name","Email","Destination","Date","Status"])

    for r in rows:
        writer.writerow(r)

    output.seek(0)

    return send_file(
        io.BytesIO(output.getvalue().encode()),
        download_name="bookings.csv",
        as_attachment=True
    )

# ---------- RUN ----------
if __name__ == "__main__":
    init_db()
    app.run(debug=True)