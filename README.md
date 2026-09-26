# Restaurante La Hoyada

Sitio web responsive en español para un restaurante peruano: carta, carrito de pedido, reservas y panel administrativo. Construido con Flask y SQLite sin ORM.

## Puesta en marcha

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python app.py
```

La base `restaurante.db` se crea automáticamente con categorías, productos, un restaurante y configuración inicial. La dirección inicia como **“Dirección por confirmar”** para no publicar una ubicación inventada; actualízala desde el panel cuando corresponda. Abre `http://127.0.0.1:5000`.

## Panel

Entra en `/admin` con los valores de `ADMIN_USER` y `ADMIN_PASSWORD` definidos en `.env`. En el primer inicio se crea un usuario `users` con la contraseña almacenada como hash Werkzeug; no existe ninguna contraseña administrativa fija en el código. Desde el panel se gestionan categorías y productos (crear, editar, eliminar, imagen), disponibilidad, destacados, estados de pedidos/reservas y todos los datos del restaurante.

## Datos de contacto

Teléfonos oficiales: **946 853 037** y **528 5902**. WhatsApp: **+51 946 853 037**. La dirección y el enlace de Google Maps son configurables desde el panel (el proyecto incluye un placeholder para ambos).

## Medios editables

Los archivos visuales están dentro de `static` para que puedas reemplazarlos sin tocar la lógica:

| Archivo | Uso |
| --- | --- |
| `static/video/video_de_cocina.mp4` | Video de fondo del hero de la página principal |
| `static/img/platos/ceviche-clasico.jpg` | Imagen principal y poster del hero |
| `static/img/platos/` | Fotografías locales de cada plato, con nombres descriptivos |
| `static/img/logo-la-hoyada.jpg` | Logo del restaurante |
| `static/img/chef-la-hoyada.jpg` | Historia visual de la chef |
| `static/img/hero.webp` | Respaldo general para compatibilidad con instalaciones antiguas |

Para cambiar el video, reemplaza `static/video/video_de_cocina.mp4` por otro archivo MP4 conservando ese nombre. Para cambiar la imagen de respaldo, reemplaza `static/img/hero.webp` o actualiza el campo **Imagen principal (URL)** desde el panel administrativo. El video usa `autoplay`, `muted`, `loop` y `playsinline` para funcionar correctamente en celulares.

Las fotografías de la carta se sirven localmente desde `static/img/platos/`. Cada plato tiene un nombre de archivo fijo; para cambiar una foto solo reemplaza el archivo manteniendo exactamente el mismo nombre. El menú resuelve la imagen por nombre de producto, por lo que no necesitas modificar `menu.html`, `app.py` ni la base de datos.

Ejemplos:

1. Reemplaza `static/img/platos/lomo-saltado.jpg` por otra fotografía JPG y conserva ese nombre. Al actualizar `/carta`, el plato **Lomo saltado** mostrará la nueva imagen.
2. Reemplaza `static/img/platos/sopa-pollo.jpg` por otra fotografía JPG y conserva ese nombre. La tarjeta **Sopa de pollo** se actualizará automáticamente.

## Rutas principales

- `/` inicio; `/carta` carta; `/pedido` carrito y checkout; `/reserva` formulario.
- `POST /api/cart` agrega productos al carrito y devuelve el contador JSON.
- `POST /pedido` y `POST /reserva` validan los formularios y guardan pedidos/reservas en SQLite.
- `/admin` dashboard protegido por sesión.
