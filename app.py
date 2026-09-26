import os
import sqlite3
from datetime import datetime
from functools import wraps
from urllib.parse import quote

from flask import Flask, flash, g, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE = os.path.join(BASE_DIR, "restaurante.db")
# Keep deployment dependency-free while still honoring the documented .env file.
env_file = os.path.join(BASE_DIR, ".env")
if os.path.exists(env_file):
    with open(env_file, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get("SECRET_KEY", "cambia-esta-clave-en-produccion"),
    DATABASE=os.environ.get("DATABASE_PATH", DATABASE),
    ADMIN_USER=os.environ.get("ADMIN_USER", "admin"),
    ADMIN_PASSWORD=os.environ.get("ADMIN_PASSWORD", ""),
)

# Each menu item has a stable local filename. Replacing one of these files
# updates the public menu without changing the database or templates.
PRODUCT_IMAGE_FILES = {
    "Sopa de pollo": "sopa-pollo.jpg",
    "Sopa de casa": "sopa-casa.jpg",
    "Sopa criolla": "sopa-criolla.jpg",
    "Menestrón": "menestron.jpg",
    "Caldo de mote": "caldo-mote.jpg",
    "Sopa de morón": "sopa-moron.jpg",
    "Tequeño": "tequeno.jpg",
    "Papa rellena": "papa-rellena.jpg",
    "Ensalada de palta": "ensalada-palta.jpg",
    "Huevo a la rusa": "huevo-rusa.jpg",
    "Higadito": "higadito.jpg",
    "Papa a la huancaína": "papa-huancaina.jpg",
    "Ocopa": "ocopa.jpg",
    "Crema de rocoto": "crema-rocoto.jpg",
    "Lomo saltado": "lomo-saltado.jpg",
    "Puré con pollo al horno": "pure-pollo-horno.jpg",
    "Carapulcra de pollo": "carapulcra-pollo.jpg",
    "Pollo a la plancha": "pollo-plancha.jpg",
    "Tacu tacu con lomito": "tacu-tacu-lomito.jpg",
    "Tallarín rojo de pollo": "tallarin-rojo-pollo.jpg",
    "Tallarín verde con bistec": "tallarin-verde-bistec.jpg",
    "Lomito saltado": "lomito-saltado.jpg",
    "Seco de carne con frejoles": "seco-carne-frejoles.jpg",
    "Chuleta con papas": "chuleta-papas.jpg",
    "Lenteja con pescado": "lenteja-pescado.jpg",
    "Olluquito": "olluquito.jpg",
    "Estofado de pollo": "estofado-pollo.jpg",
    "Estofado de carne": "estofado-carne.jpg",
    "Alitas broaster con ensalada rusa": "alitas-broaster-ensalada-rusa.jpg",
    "Lentejita partida con pollo frito": "lentejita-pollo-frito.jpg",
    "Pollada": "pollada.jpg",
    "Pollo broaster": "pollo-broaster.jpg",
    "Tacacho con cecina y chorizo": "tacacho-cecina.jpg",
    "Juane": "juane.jpg",
    "Chaufa amazónico": "chaufa-amazonico.jpg",
    "Patacones rellenos": "patacones-rellenos.jpg",
}


def product_image(product_name, database_image=""):
    """Return the stable local image path for a menu product."""
    filename = PRODUCT_IMAGE_FILES.get(product_name)
    if filename:
        return url_for("static", filename=f"img/platos/{filename}")
    return database_image or url_for("static", filename="img/platos/ceviche-clasico.jpg")


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def query(sql, params=(), one=False):
    cur = get_db().execute(sql, params)
    rows = cur.fetchall()
    cur.close()
    return (rows[0] if rows else None) if one else rows


def site_value(key, default=""):
    restaurant = query("SELECT * FROM restaurants ORDER BY id LIMIT 1", one=True)
    mapping = {
        "whatsapp": "whatsapp", "phone": "phone", "phone_delivery": "phone_delivery",
        "address": "address", "maps_url": "google_maps", "hours": "hours",
    }
    if restaurant and key in mapping:
        return restaurant[mapping[key]] or default
    row = query("SELECT value FROM settings WHERE key=?", (key,), one=True)
    return row["value"] if row else default


def init_db():
    db = get_db()
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS restaurants (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
            description TEXT DEFAULT '', phone TEXT DEFAULT '',
            phone_delivery TEXT DEFAULT '', whatsapp TEXT DEFAULT '',
            address TEXT DEFAULT '', google_maps TEXT DEFAULT '',
            hours TEXT DEFAULT '', logo TEXT DEFAULT '', main_image TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'admin',
            active INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE,
            slug TEXT NOT NULL UNIQUE, description TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT, category_id INTEGER NOT NULL,
            name TEXT NOT NULL, description TEXT DEFAULT '', price REAL NOT NULL,
            image TEXT DEFAULT '', available INTEGER NOT NULL DEFAULT 1,
            featured INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY(category_id) REFERENCES categories(id) ON DELETE RESTRICT
        );
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT, customer_name TEXT NOT NULL,
            phone TEXT NOT NULL, address TEXT DEFAULT '', notes TEXT DEFAULT '',
            total REAL NOT NULL, status TEXT NOT NULL DEFAULT 'pendiente',
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT, order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL, quantity INTEGER NOT NULL, price REAL NOT NULL,
            FOREIGN KEY(order_id) REFERENCES orders(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS reservations (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, phone TEXT NOT NULL,
            guests INTEGER NOT NULL, date TEXT NOT NULL, time TEXT NOT NULL,
            notes TEXT DEFAULT '', status TEXT NOT NULL DEFAULT 'pendiente',
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        """
    )
    restaurant = query("SELECT id FROM restaurants LIMIT 1", one=True)
    if not restaurant:
        db.execute(
            """INSERT INTO restaurants
            (name,description,phone,phone_delivery,whatsapp,address,google_maps,hours,logo,main_image)
            VALUES(?,?,?,?,?,?,?,?,?,?)""",
            ("Restaurante La Hoyada", "Cocina peruana tradicional, fresca y llena de sabor para compartir.",
             "946 853 037", "528 5902", "+51946853037",
             "Dirección por confirmar",
             "https://maps.google.com/?q=Restaurante+La+Hoyada",
             "Horario por confirmar", "/static/img/logo-la-hoyada.jpg", "/static/img/hero.webp"),
        )
    db.execute(
        "UPDATE restaurants SET logo=? WHERE logo IS NULL OR logo=''",
        ("/static/img/logo-la-hoyada.jpg",),
    )
    db.execute(
        "UPDATE restaurants SET description=? WHERE description IN (?, ?)",
        (
            "Cocina peruana tradicional, fresca y llena de sabor para compartir.",
            "El sabor que reúne a todos.",
            "Somos un restaurante tradicional.",
        ),
    )
    if app.config["ADMIN_USER"] and app.config["ADMIN_PASSWORD"] and not query(
        "SELECT id FROM users WHERE username=?", (app.config["ADMIN_USER"],), one=True
    ):
        db.execute(
            "INSERT INTO users(username,password_hash,role,active,created_at) VALUES(?,?,?,?,?)",
            (app.config["ADMIN_USER"], generate_password_hash(app.config["ADMIN_PASSWORD"]),
             "admin", 1, datetime.now().isoformat(timespec="seconds")),
        )
    # Keep the catalog editable from the admin panel, but migrate the original
    # starter catalog once to a broader Peruvian menu with dish photography.
    catalog_version = query("SELECT value FROM settings WHERE key='catalog_version'", one=True)
    if not catalog_version or catalog_version["value"] != "peruvian-v2":
        db.execute("DELETE FROM products")
        db.execute("DELETE FROM categories")
        categories = [
            ("Entradas", "entradas", "Para abrir el apetito."),
            ("Ceviches", "ceviches", "Pescados y mariscos con el toque cítrico peruano."),
            ("Platos de fondo", "platos-de-fondo", "Recetas criollas para disfrutar sin apuro."),
            ("Arroces", "arroces", "Arroces peruanos llenos de sabor."),
            ("Bebidas", "bebidas", "Refrescos y bebidas tradicionales."),
        ]
        db.executemany("INSERT INTO categories(name,slug,description) VALUES(?,?,?)", categories)
        ids = {r["slug"]: r["id"] for r in query("SELECT id,slug FROM categories")}
        products = [
            (ids["entradas"], "Causa limeña de pollo", "Causa de papa amarilla, ají amarillo, palta y pollo sazonado.", 24.0, "/static/img/platos/causa-limena.jpg", 1, 1),
            (ids["entradas"], "Anticuchos de corazón", "Brochetas a la parrilla con papa dorada y crema de ají.", 28.0, "/static/img/platos/anticuchos-corazon.jpg", 1, 0),
            (ids["ceviches"], "Ceviche clásico", "Pescado fresco, limón, ají limo, cebolla morada, choclo y camote.", 36.0, "/static/img/platos/ceviche-clasico.jpg", 1, 1),
            (ids["ceviches"], "Ceviche mixto", "Pescado y mariscos frescos en leche de tigre de la casa.", 42.0, "/static/img/platos/ceviche-mixto.jpg", 1, 0),
            (ids["platos-de-fondo"], "Lomo saltado", "Lomo de res, cebolla, tomate, papas doradas y arroz blanco.", 38.0, "/static/img/platos/lomo-saltado.jpg", 1, 1),
            (ids["platos-de-fondo"], "Ají de gallina", "Guiso cremoso de ají amarillo, pollo, papa, arroz y aceituna.", 29.0, "/static/img/platos/aji-de-gallina.jpg", 1, 0),
            (ids["arroces"], "Arroz con mariscos", "Arroz sazonado con mariscos, ajíes peruanos y salsa criolla.", 39.0, "/static/img/platos/arroz-con-mariscos.jpg", 1, 1),
            (ids["arroces"], "Arroz chaufa de la casa", "Arroz salteado al wok con verduras, huevo y proteína a elección.", 27.0, "/static/img/platos/arroz-chaufa.jpg", 1, 0),
            (ids["bebidas"], "Chicha morada 1 L", "Receta casera con maíz morado, piña, canela y clavo.", 10.0, "/static/img/platos/chicha-morada.jpg", 1, 0),
            (ids["bebidas"], "Maracuyá frozen", "Refrescante bebida de maracuyá preparada al momento.", 12.0, "/static/img/platos/maracuya-frozen.jpg", 1, 0),
        ]
        db.executemany(
            "INSERT INTO products(category_id,name,description,price,image,available,featured) VALUES(?,?,?,?,?,?,?)",
            products,
        )
        db.execute("INSERT OR REPLACE INTO settings(key,value) VALUES('catalog_version','peruvian-v3')")
    # Localize the dish photography for installations that already received
    # the previous catalog. This avoids broken hotlinks without replacing
    # products or prices managed by the administrator.
    local_images = {
        "Causa limeña de pollo": "causa-limena.jpg",
        "Anticuchos de corazón": "anticuchos-corazon.jpg",
        "Ceviche clásico": "ceviche-clasico.jpg",
        "Ceviche mixto": "ceviche-mixto.jpg",
        "Lomo saltado": "lomo-saltado.jpg",
        "Ají de gallina": "aji-de-gallina.jpg",
        "Arroz con mariscos": "arroz-con-mariscos.jpg",
        "Arroz chaufa de la casa": "arroz-chaufa.jpg",
        "Chicha morada 1 L": "chicha-morada.jpg",
        "Maracuyá frozen": "maracuya-frozen.jpg",
    }
    for product_name, image_name in local_images.items():
        db.execute(
            "UPDATE products SET image=? WHERE name=? AND (image LIKE 'http%' OR image='')",
            (f"/static/img/platos/{image_name}", product_name),
        )
    # Remove the dessert category and its products from installations that
    # already loaded the previous catalog.
    catalog_version = query("SELECT value FROM settings WHERE key='catalog_version'", one=True)
    if not catalog_version or catalog_version["value"] != "peruvian-v4":
        db.execute(
            "DELETE FROM products WHERE category_id IN "
            "(SELECT id FROM categories WHERE slug='postres')"
        )
        db.execute("DELETE FROM categories WHERE slug='postres'")
        db.execute(
            "INSERT OR REPLACE INTO settings(key,value) VALUES('catalog_version','peruvian-v4')"
        )
    # Replace the starter catalog with the restaurant's requested menu.
    # This migration runs once and leaves the resulting products editable
    # from the administrator dashboard.
    catalog_version = query("SELECT value FROM settings WHERE key='catalog_version'", one=True)
    if not catalog_version or catalog_version["value"] != "peruvian-v5":
        db.execute("DELETE FROM products")
        db.execute("DELETE FROM categories")
        categories = [
            ("Entrada 1", "entrada-1", "Sopas caseras y reconfortantes."),
            ("Entrada 2", "entrada-2", "Entradas peruanas para compartir."),
            ("Segundos criollos", "segundos-criollos", "Almuerzos criollos preparados al momento."),
            ("Platos a la carta", "platos-a-la-carta", "Especialidades peruanas de la casa."),
        ]
        db.executemany(
            "INSERT INTO categories(name,slug,description) VALUES(?,?,?)",
            categories,
        )
        ids = {row["slug"]: row["id"] for row in query("SELECT id,slug FROM categories")}
        products = [
            (ids["entrada-1"], "Sopa de pollo", "Caldo casero con pollo, verduras y fideos.", 12.0, "/static/img/platos/aji-de-gallina.jpg", 1, 0),
            (ids["entrada-1"], "Sopa de casa", "Sopa del día con ingredientes frescos de la casa.", 10.0, "/static/img/platos/sopa-casa.jpg", 1, 0),
            (ids["entrada-1"], "Sopa criolla", "Sopa criolla con carne, cabello de ángel, huevo y leche.", 14.0, "/static/img/platos/sopa-criolla.jpg", 1, 1),
            (ids["entrada-1"], "Menestrón", "Sopa de verduras, fideos, albahaca y queso.", 13.0, "/static/img/platos/menestron.jpg", 1, 0),
            (ids["entrada-1"], "Caldo de mote", "Caldo tradicional con mote y hierbas aromáticas.", 14.0, "/static/img/platos/caldo-mote.jpg", 1, 0),
            (ids["entrada-1"], "Sopa de morón", "Sopa casera de morón con verduras y carne.", 13.0, "/static/img/platos/sopa-moron.jpg", 1, 0),
            (ids["entrada-2"], "Tequeño", "Tequeños dorados rellenos de queso con salsa de la casa.", 10.0, "/static/img/platos/tequeno.jpg", 1, 0),
            (ids["entrada-2"], "Papa rellena", "Papa dorada rellena de carne sazonada.", 12.0, "/static/img/platos/Papa_rellena.jpg", 1, 1),
            (ids["entrada-2"], "Ensalada de palta", "Palta fresca con verduras y vinagreta de la casa.", 10.0, "/static/img/platos/ensalada-palta.jpg", 1, 0),
            (ids["entrada-2"], "Huevo a la rusa", "Huevo, papa y verduras con mayonesa casera.", 10.0, "/static/img/platos/huevo-rusa.jpg", 1, 0),
            (ids["entrada-2"], "Higadito", "Hígado salteado con cebolla y acompañamiento criollo.", 14.0, "/static/img/platos/Higadito.jpg", 1, 0),
            (ids["entrada-2"], "Papa a la huancaína", "Papa sancochada con crema de ají amarillo y queso.", 12.0, "/static/img/platos/papa_huancaina.jpg", 1, 1),
            (ids["entrada-2"], "Ocopa", "Papa con salsa de huacatay, queso y maní.", 12.0, "/static/img/platos/ocopa.jpg", 1, 0),
            (ids["entrada-2"], "Crema de rocoto", "Crema artesanal de rocoto para acompañar tus platos.", 8.0, "/static/img/platos/ceviche-mixto.jpg", 1, 0),
            (ids["segundos-criollos"], "Lomo saltado", "Lomo de res, cebolla, tomate, papas doradas y arroz.", 18.0, "/static/img/platos/lomo-saltado.jpg", 1, 1),
            (ids["segundos-criollos"], "Puré con pollo al horno", "Puré de papa cremoso con pollo al horno.", 17.0, "/static/img/platos/pure-pollo-horno.jpg", 1, 0),
            (ids["segundos-criollos"], "Carapulcra de pollo", "Guiso de papa seca con pollo y ajíes peruanos.", 17.0, "/static/img/platos/carapulcra-pollo.jpg", 1, 0),
            (ids["segundos-criollos"], "Pollo a la plancha", "Pollo a la plancha con ensalada y papas.", 17.0, "/static/img/platos/anticuchos-corazon.jpg", 1, 0),
            (ids["segundos-criollos"], "Tacu tacu con lomito", "Tacu tacu dorado acompañado de lomito saltado.", 19.0, "/static/img/platos/tacu-tacu-lomito.jpg", 1, 1),
            (ids["segundos-criollos"], "Tallarín rojo de pollo", "Tallarines en salsa roja casera con pollo.", 17.0, "/static/img/platos/tallarin-rojo-pollo.jpg", 1, 0),
            (ids["segundos-criollos"], "Tallarín verde con bistec", "Tallarines verdes con bistec y papa dorada.", 19.0, "/static/img/platos/tallarin-verde-bistec.jpg", 1, 0),
            (ids["segundos-criollos"], "Lomito saltado", "Lomito salteado con cebolla, tomate, papas y arroz.", 19.0, "/static/img/platos/lomito-saltado.jpg", 1, 0),
            (ids["segundos-criollos"], "Seco de carne con frejoles", "Seco de carne acompañado de frejoles y arroz.", 18.0, "/static/img/platos/seco-carne-frejoles.jpg", 1, 1),
            (ids["segundos-criollos"], "Chuleta con papas", "Chuleta dorada con papas y ensalada fresca.", 18.0, "/static/img/platos/chuleta-papas.jpg", 1, 0),
            (ids["segundos-criollos"], "Lenteja con pescado", "Lentejas guisadas con pescado frito y arroz.", 18.0, "/static/img/platos/lenteja-pescado.jpg", 1, 0),
            (ids["segundos-criollos"], "Olluquito", "Olluquito guisado con carne y arroz blanco.", 17.0, "/static/img/platos/olluquito.jpg", 1, 0),
            (ids["segundos-criollos"], "Estofado de pollo", "Pollo guisado en salsa casera con papa y arroz.", 17.0, "/static/img/platos/estofado-pollo.jpg", 1, 0),
            (ids["segundos-criollos"], "Estofado de carne", "Carne guisada con verduras, papa y arroz.", 18.0, "/static/img/platos/estofado-carne.jpg", 1, 0),
            (ids["segundos-criollos"], "Alitas broaster con ensalada rusa", "Alitas crocantes con ensalada rusa.", 18.0, "/static/img/platos/alitas-broaster-ensalada-rusa.jpg", 1, 0),
            (ids["segundos-criollos"], "Lentejita partida con pollo frito", "Lentejas guisadas con pollo frito y arroz.", 18.0, "/static/img/platos/lentejita-pollo-frito.jpg", 1, 0),
            (ids["segundos-criollos"], "Pollada", "Pollo marinado y dorado con papas y ensalada.", 18.0, "/static/img/platos/pollada.jpg", 1, 1),
            (ids["platos-a-la-carta"], "Pollada", "Pollo marinado y dorado con papas y ensalada.", 22.0, "/static/img/platos/pollada.jpg", 1, 0),
            (ids["platos-a-la-carta"], "Pollo broaster", "Pollo crocante estilo broaster con papas.", 22.0, "/static/img/platos/pollo-broaster.jpg", 1, 0),
            (ids["platos-a-la-carta"], "Lomo saltado", "Lomo de res salteado con papas, arroz y verduras.", 24.0, "/static/img/platos/lomo-saltado.jpg", 1, 1),
            (ids["platos-a-la-carta"], "Tacacho con cecina y chorizo", "Tacacho amazónico con cecina y chorizo.", 25.0, "/static/img/platos/tacacho-cecina.jpg", 1, 1),
            (ids["platos-a-la-carta"], "Juane", "Arroz sazonado con pollo, huevo y especias amazónicas.", 22.0, "/static/img/platos/juane.jpg", 1, 0),
            (ids["platos-a-la-carta"], "Chaufa amazónico", "Arroz chaufa con sabores e ingredientes de la Amazonía.", 23.0, "/static/img/platos/chaufa-amazonico.jpg", 1, 0),
            (ids["platos-a-la-carta"], "Pollo a la plancha", "Pollo a la plancha con papas y ensalada.", 22.0, "/static/img/platos/pollo-plancha.jpg", 1, 0),
            (ids["platos-a-la-carta"], "Patacones rellenos", "Patacones dorados rellenos con preparación de la casa.", 22.0, "/static/img/platos/Patacones-amazonico.jpg", 1, 0),
        ]
        db.executemany(
            "INSERT INTO products(category_id,name,description,price,image,available,featured) VALUES(?,?,?,?,?,?,?)",
            products,
        )
        db.execute(
            "INSERT OR REPLACE INTO settings(key,value) VALUES('catalog_version','peruvian-v5')"
        )
    defaults = {
        "address": "Dirección por confirmar",
        "maps_url": "https://maps.google.com/?q=Restaurante+La+Hoyada",
        "instagram": "https://instagram.com/",
        "hero_title": "Perú servido en cada plato",
    }
    for key, value in defaults.items():
        db.execute("INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)", (key, value))
    # Never publish the old sample address if a database was created by an
    # earlier version; the real location is entered from the admin panel.
    db.execute(
        "UPDATE settings SET value=? WHERE key='address' AND value LIKE 'Av. La Hoyada%'",
        (defaults["address"],),
    )
    db.execute(
        "UPDATE restaurants SET main_image=? WHERE main_image IS NULL OR main_image='' OR main_image='/static/img/hero.webp'",
        ("/static/img/platos/ceviche-clasico.jpg",),
    )
    db.commit()


@app.context_processor
def inject_globals():
    settings = {r["key"]: r["value"] for r in query("SELECT key,value FROM settings")}
    restaurant = query("SELECT * FROM restaurants ORDER BY id LIMIT 1", one=True)
    if restaurant:
        settings.update({
            "name": restaurant["name"], "description": restaurant["description"],
            "phone": restaurant["phone"], "phone_delivery": restaurant["phone_delivery"],
            "whatsapp": restaurant["whatsapp"], "address": restaurant["address"],
            "maps_url": restaurant["google_maps"], "hours": restaurant["hours"],
            "logo": restaurant["logo"], "main_image": restaurant["main_image"],
        })
    return {
        "site": settings,
        "cart_count": sum(session.get("cart", {}).values()),
        "now": datetime.now(),
        "product_image": product_image,
    }


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = query("SELECT id FROM users WHERE username=? AND role='admin' AND active=1",
                     (session.get("admin_user"),), one=True)
        if not session.get("admin") or not user:
            return redirect(url_for("admin_login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def valid_admin_password(username, password):
    user = query("SELECT password_hash FROM users WHERE username=? AND active=1", (username,), one=True)
    if not user:
        return False
    try:
        return check_password_hash(user["password_hash"], password)
    except (ValueError, TypeError):
        return False


@app.route("/")
def home():
    featured = query("SELECT p.*, c.name category FROM products p JOIN categories c ON c.id=p.category_id WHERE p.available=1 AND p.featured=1")
    carousel_products = query(
        "SELECT p.*, c.name category FROM products p "
        "JOIN categories c ON c.id=p.category_id "
        "WHERE p.available=1 ORDER BY c.id, p.id"
    )
    categories = query("SELECT * FROM categories ORDER BY id")
    return render_template(
        "home.html",
        featured=featured,
        categories=categories,
        carousel_products=carousel_products,
    )


@app.route("/carta")
def menu():
    categories = query("SELECT * FROM categories ORDER BY id")
    products = query("SELECT p.*, c.slug category_slug FROM products p JOIN categories c ON c.id=p.category_id WHERE p.available=1 ORDER BY c.id,p.id")
    return render_template("menu.html", categories=categories, products=products)


@app.post("/api/cart")
def api_cart():
    data = request.get_json(silent=True) or request.form
    try:
        pid, qty = int(data.get("product_id", 0)), int(data.get("quantity", 1))
    except (TypeError, ValueError):
        return jsonify(error="Producto o cantidad inválidos"), 400
    if pid <= 0 or qty == 0 or abs(qty) > 99:
        return jsonify(error="Producto o cantidad inválidos"), 400
    product = query("SELECT id FROM products WHERE id=? AND available=1", (pid,), one=True)
    if not product:
        return jsonify(error="Producto no disponible"), 404
    cart = session.setdefault("cart", {})
    key = str(pid)
    cart[key] = max(0, cart.get(key, 0) + qty)
    if cart[key] == 0:
        cart.pop(key)
    session.modified = True
    return jsonify(ok=True, count=sum(cart.values()))


@app.post("/api/cart/remove")
def api_cart_remove():
    data = request.get_json(silent=True) or request.form
    try:
        pid = int(data.get("product_id", 0))
    except (TypeError, ValueError):
        return jsonify(error="Producto inválido"), 400
    if pid <= 0:
        return jsonify(error="Producto inválido"), 400
    cart = session.setdefault("cart", {})
    cart.pop(str(pid), None)
    session.modified = True
    return jsonify(ok=True, count=sum(cart.values()))


@app.post("/api/cart/clear")
def api_cart_clear():
    session["cart"] = {}
    session.modified = True
    return jsonify(ok=True, count=0)


@app.route("/pedido", methods=["GET", "POST"])
def order():
    cart = session.get("cart", {})
    items = []
    total = 0
    for pid, qty in cart.items():
        product = query("SELECT * FROM products WHERE id=? AND available=1", (pid,), one=True)
        if product and qty > 0:
            line = dict(product)
            line["quantity"] = qty
            line["subtotal"] = qty * product["price"]
            total += line["subtotal"]
            items.append(line)
    if request.method == "POST":
        if not items:
            flash("Agrega al menos un producto a tu pedido.", "error")
            return redirect(url_for("menu"))
        form = request.form
        name, phone, address = form.get("name", "").strip(), form.get("phone", "").strip(), form.get("address", "").strip()
        if not name or not phone or not address or len(name) > 120 or len(phone) > 40 or len(address) > 240:
            flash("Completa correctamente tus datos de contacto.", "error")
            return render_template("order.html", items=items, total=total), 400
        db = get_db()
        cur = db.execute(
            "INSERT INTO orders(customer_name,phone,address,notes,total,created_at) VALUES(?,?,?,?,?,?)",
            (name, phone, address, form.get("notes", "").strip()[:500], total, datetime.now().isoformat(timespec="seconds")),
        )
        for item in items:
            db.execute("INSERT INTO order_items(order_id,product_id,quantity,price) VALUES(?,?,?,?)", (cur.lastrowid, item["id"], item["quantity"], item["price"]))
        db.commit()
        session["cart"] = {}
        summary = "Pedido La Hoyada\nCliente: {}\nTeléfono: {}\nDirección: {}\nItems: {}\nTotal: S/ {:.2f}\nNotas: {}".format(
            name, phone, address,
            ", ".join("{} x {}".format(i["quantity"], i["name"]) for i in items),
            total, form.get("notes", "").strip()[:500],
        )
        whatsapp = site_value("whatsapp").replace("+", "").replace(" ", "")
        return render_template("success.html", title="¡Pedido recibido!", message="Te contactaremos por teléfono para confirmar tu pedido.", whatsapp_link="https://wa.me/{}?text={}".format(whatsapp, quote(summary)))
    return render_template("order.html", items=items, total=total)


@app.route("/reserva", methods=["GET", "POST"])
def reservation():
    if request.method == "POST":
        f = request.form
        try:
            guests = int(f.get("guests", 0))
        except (TypeError, ValueError):
            guests = 0
        if not f.get("name", "").strip() or not f.get("phone", "").strip() or guests < 1 or guests > 30 or not f.get("date") or not f.get("time"):
            flash("Revisa los datos de tu reserva.", "error")
            return render_template("reservation.html"), 400
        get_db().execute(
            "INSERT INTO reservations(name,phone,guests,date,time,notes,created_at) VALUES(?,?,?,?,?,?,?)",
            (f["name"].strip(), f["phone"].strip(), guests, f["date"], f["time"], f.get("notes", "").strip()[:500], datetime.now().isoformat(timespec="seconds")),
        )
        get_db().commit()
        return render_template("success.html", title="Reserva solicitada", message="Recibimos tu reserva. Te llamaremos para confirmarla.")
    return render_template("reservation.html")


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        user, password = request.form.get("username"), request.form.get("password", "")
        if valid_admin_password(user, password):
            session["admin"] = True
            session["admin_user"] = user
            return redirect(request.args.get("next") or url_for("admin_dashboard"))
        flash("Usuario o contraseña incorrectos.", "error")
    return render_template("admin/login.html")


@app.route("/admin/logout")
def admin_logout():
    session.pop("admin", None)
    session.pop("admin_user", None)
    return redirect(url_for("home"))


@app.route("/admin")
@admin_required
def admin_dashboard():
    return render_template("admin/dashboard.html", products=query("SELECT p.*,c.name category FROM products p JOIN categories c ON c.id=p.category_id ORDER BY p.id DESC"), categories=query("SELECT * FROM categories"), orders=query("SELECT * FROM orders ORDER BY id DESC LIMIT 30"), reservations=query("SELECT * FROM reservations ORDER BY id DESC LIMIT 30"))


@app.post("/admin/products")
@admin_required
def admin_product():
    f = request.form
    try:
        category_id, price = int(f.get("category_id", 0)), float(f.get("price", 0))
    except (TypeError, ValueError):
        flash("Categoría o precio inválidos.", "error")
        return redirect(url_for("admin_dashboard"))
    if category_id <= 0 or price <= 0 or not f.get("name", "").strip():
        flash("Completa nombre, categoría y precio válido.", "error")
        return redirect(url_for("admin_dashboard"))
    try:
        get_db().execute("INSERT INTO products(category_id,name,description,price,image,available,featured) VALUES(?,?,?,?,?,?,?)", (category_id, f["name"].strip(), f.get("description", ""), price, f.get("image", "").strip(), int("available" in f), int("featured" in f)))
        get_db().commit()
    except sqlite3.IntegrityError:
        flash("La categoría seleccionada no existe.", "error")
    return redirect(url_for("admin_dashboard"))


@app.post("/admin/products/<int:product_id>/delete")
@admin_required
def delete_product(product_id):
    get_db().execute("DELETE FROM products WHERE id=?", (product_id,))
    get_db().commit()
    return redirect(url_for("admin_dashboard"))


@app.post("/admin/products/<int:product_id>/update")
@admin_required
def update_product(product_id):
    f = request.form
    try:
        get_db().execute(
            """UPDATE products SET category_id=?, name=?, description=?, price=?,
               image=?, available=?, featured=? WHERE id=?""",
            (
                int(f["category_id"]), f["name"].strip(), f.get("description", ""),
                float(f["price"]), f.get("image", ""), int("available" in f),
                int("featured" in f), product_id,
            ),
        )
        get_db().commit()
    except (KeyError, ValueError, sqlite3.IntegrityError):
        flash("Revisa los datos del producto.", "error")
    return redirect(url_for("admin_dashboard"))

@app.post("/admin/categories")
@admin_required
def admin_category():
    name = request.form.get("name", "").strip()
    slug = request.form.get("slug", "").strip().lower().replace(" ", "-")
    if name and slug:
        try:
            get_db().execute("INSERT INTO categories(name,slug,description) VALUES(?,?,?)", (name, slug, request.form.get("description", "")))
            get_db().commit()
        except sqlite3.IntegrityError:
            flash("Esa categoría ya existe.", "error")
    return redirect(url_for("admin_dashboard"))


@app.post("/admin/categories/<int:category_id>/delete")
@admin_required
def delete_category(category_id):
    try:
        get_db().execute("DELETE FROM categories WHERE id=?", (category_id,))
        get_db().commit()
    except sqlite3.IntegrityError:
        flash("No puedes eliminar una categoría con productos.", "error")
    return redirect(url_for("admin_dashboard"))


@app.post("/admin/categories/<int:category_id>/update")
@admin_required
def update_category(category_id):
    name = request.form.get("name", "").strip()
    slug = request.form.get("slug", "").strip().lower().replace(" ", "-")
    if name and slug:
        try:
            get_db().execute(
                "UPDATE categories SET name=?, slug=?, description=? WHERE id=?",
                (name, slug, request.form.get("description", ""), category_id),
            )
            get_db().commit()
        except sqlite3.IntegrityError:
            flash("El nombre o slug ya existe.", "error")
    return redirect(url_for("admin_dashboard"))


@app.post("/admin/products/<int:product_id>/toggle")
@admin_required
def toggle_product(product_id):
    field = "featured" if request.form.get("field") == "featured" else "available"
    get_db().execute(f"UPDATE products SET {field}=1-{field} WHERE id=?", (product_id,))
    get_db().commit()
    return redirect(url_for("admin_dashboard"))


@app.post("/admin/status/<kind>/<int:item_id>")
@admin_required
def update_status(kind, item_id):
    table = "orders" if kind == "order" else "reservations"
    status = request.form.get("status", "pendiente")
    if status not in ("pendiente", "confirmado", "preparando", "listo", "atendido", "cancelado"):
        status = "pendiente"
    get_db().execute(f"UPDATE {table} SET status=? WHERE id=?", (status, item_id))
    get_db().commit()
    return redirect(url_for("admin_dashboard"))


@app.post("/admin/settings")
@admin_required
def admin_settings():
    db = get_db()
    db.execute(
        """UPDATE restaurants SET name=?, description=?, phone=?, phone_delivery=?,
        whatsapp=?, address=?, google_maps=?, hours=?, logo=?, main_image=? WHERE id=1""",
        tuple(request.form.get(k, "").strip() for k in
              ("name", "description", "phone", "phone_delivery", "whatsapp",
               "address", "maps_url", "hours", "logo", "main_image")),
    )
    db.execute("INSERT OR REPLACE INTO settings(key,value) VALUES('hero_title',?)", (request.form.get("hero_title", ""),))
    db.execute("INSERT OR REPLACE INTO settings(key,value) VALUES('instagram',?)", (request.form.get("instagram", ""),))
    db.commit()
    flash("Configuración guardada.", "success")
    return redirect(url_for("admin_dashboard"))


with app.app_context():
    init_db()


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
