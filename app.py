import os, html
import psycopg2
from flask import Flask, request, jsonify, redirect
from urllib.parse import quote

app = Flask(__name__)
DB_URL = os.environ["DATABASE_URL"]
HAMID_KEY = os.environ.get("HAMID_KEY", "1234")

def db():
    return psycopg2.connect(DB_URL)

def init():
    conn = db()
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS bookings (slot TEXT PRIMARY KEY, name TEXT, phone TEXT)")
    conn.commit()
    cur.close()
    conn.close()

init()

PAGE = """<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>نوبت‌دهی آرایشگاه حمید</title>
<style>
body { font-family: Tahoma, sans-serif; padding: 16px; max-width: 480px; margin: auto; background: #e8f0fe; color: #1d2433; }
button { font-size: 16px; padding: 10px 14px; margin: 4px; border: 1px solid #999; border-radius: 20px; background: #fff; color: #000; }
button.on { background: #1f4e8c; color: #fff; transform: scale(1.1); }
button:disabled { opacity: 0.35; text-decoration: line-through; }
input { font-size: 16px; padding: 10px; width: 100%; box-sizing: border-box; }
.go { background: #b8322f; color: #fff; width: 100%; margin: 20px 0 0; }
h1 { text-align: center; color: #b8322f; }
</style>
</head>
<body>
<h1>آرایشگاه حمید</h1>
<p>اسم شما:</p>
<input id="name">
<p>شماره‌ی موبایل:</p>
<input id="phone" type="tel" inputmode="numeric">
<p>روز:</p>
<div id="days"></div>
<p>ساعت:</p>
<div id="times"></div>
<button class="go" onclick="save()">ثبت نوبت</button>

<script>
var days = [];
var d = new Date();
if (d.getDay() == 5) d.setDate(d.getDate() + 1);
while (true) {
  days.push(d.toLocaleDateString("fa-IR", { weekday: "long", day: "numeric", month: "long" }));
  if (d.getDay() == 4) break;
  d.setDate(d.getDate() + 1);
}

var times = [
  "10:00", "10:30", "11:00", "11:30", "12:00", "12:30", "13:00", "13:30",
  "17:00", "17:30", "18:00", "18:30", "19:00", "19:30", "20:00"
];

var taken = [];
var chosenDay = "";
var chosenTime = "";

function showButtons(list, boxId, picked, onPick, isTaken) {
  var box = document.getElementById(boxId);
  box.innerHTML = "";
  list.forEach(function (item) {
    var b = document.createElement("button");
    b.textContent = item;
    if (item == picked) b.className = "on";
    if (isTaken && isTaken(item)) b.disabled = true;
    b.onclick = function () { onPick(item); };
    box.appendChild(b);
  });
}

function draw() {
  showButtons(days, "days", chosenDay, function (x) {
    chosenDay = x;
    chosenTime = "";
    draw();
  });
  showButtons(times, "times", chosenTime, function (t) {
    chosenTime = t;
    draw();
  }, function (t) {
    return taken.indexOf(chosenDay + " " + t) >= 0;
  });
}

function loadTaken() {
  fetch("/taken")
    .then(function (r) { return r.json(); })
    .then(function (list) { taken = list; draw(); });
}

function save() {
  var name = document.getElementById("name").value.trim();
  var phone = document.getElementById("phone").value.trim();
  if (name == "" || phone.length < 10 || chosenDay == "" || chosenTime == "") {
    alert("اسم، شماره، روز و ساعت را کامل کن");
    return;
  }
  var slot = chosenDay + " " + chosenTime;
  fetch("/book?name=" + encodeURIComponent(name) + "&phone=" + encodeURIComponent(phone) + "&slot=" + encodeURIComponent(slot))
    .then(function (r) { return r.text(); })
    .then(function (msg) {
      alert(msg);
      chosenTime = "";
      loadTaken();
    });
}

draw();
loadTaken();
</script>
</body>
</html>
"""

@app.route("/")
def home():
    return PAGE

@app.route("/taken")
def taken():
    conn = db()
    cur = conn.cursor()
    cur.execute("SELECT slot FROM bookings")
    slots = [r[0] for r in cur.fetchall()]
    cur.close()
    conn.close()
    return jsonify(slots)

@app.route("/book")
def book():
    name = request.args.get("name", "").strip()[:40]
    phone = request.args.get("phone", "").strip()[:15]
    slot = request.args.get("slot", "")
    if name == "" or phone == "" or slot == "":
        return "اطلاعات ناقص است"
    conn = db()
    cur = conn.cursor()
    cur.execute("INSERT INTO bookings (slot, name, phone) VALUES (%s, %s, %s) ON CONFLICT (slot) DO NOTHING", (slot, name, phone))
    done = cur.rowcount
    conn.commit()
    cur.close()
    conn.close()
    if done == 0:
        return "این ساعت پر است"
    return "نوبت شما ثبت شد"

@app.route("/hamid")
def hamid():
    if request.args.get("key") != HAMID_KEY:
        return "دسترسی ندارید"
    conn = db()
    cur = conn.cursor()
    cur.execute("SELECT slot, name, phone FROM bookings ORDER BY slot")
    items = cur.fetchall()
    cur.close()
    conn.close()
    rows = ""
    for slot, name, phone in items:
        slot = html.escape(slot)
        phone = html.escape(phone or "")
        form = "<form method='post' action='/delete' onsubmit=\"return confirm('این نوبت حذف شود؟')\">"
        form += "<input type='hidden' name='key' value='" + html.escape(HAMID_KEY) + "'>"
        form += "<input type='hidden' name='slot' value='" + slot + "'>"
        form += "<button>حذف</button></form>"
        rows += "<tr><td>" + slot + "</td><td>" + html.escape(name or "") + "</td><td><a href='tel:" + phone + "'>" + phone + "</a></td><td>" + form + "</td></tr>"
    if rows == "":
        rows = "<tr><td colspan='4'>هنوز نوبتی ثبت نشده</td></tr>"
    style = "body{font-family:Tahoma;padding:12px;font-size:22px;background:#e8f0fe}"
    style += "table{width:100%;border-collapse:collapse;background:#fff}"
    style += "th,td{border:1px solid #999;padding:12px;text-align:center}"
    style += "th{background:#1f4e8c;color:#fff}"
    style += "a{color:#1f4e8c;text-decoration:none}"
    style += "button{font-size:18px;padding:8px 14px;background:#b8322f;color:#fff;border:0;border-radius:10px}"
    head = "<meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'><style>" + style + "</style>"
    table = "<table><tr><th>روز و ساعت</th><th>اسم</th><th>شماره</th><th></th></tr>" + rows + "</table>"
    return head + "<body dir='rtl'><h2 style='text-align:center'>نوبت‌های ثبت‌شده</h2>" + table

@app.route("/delete", methods=["POST"])
def delete():
    if request.form.get("key") != HAMID_KEY:
        return "دسترسی ندارید"
    slot = request.form.get("slot", "")
    conn = db()
    cur = conn.cursor()
    cur.execute("DELETE FROM bookings WHERE slot = %s", (slot,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect("/hamid?key=" + quote(HAMID_KEY))
