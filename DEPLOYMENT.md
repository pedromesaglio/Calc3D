# Guía de Despliegue a Producción - Calc3D

Esta guía te ayudará a desplegar Calc3D en producción con todas las funcionalidades de pagos y suscripciones.

## Requisitos Previos

- Servidor con Python 3.10+
- Dominio con HTTPS configurado (requerido para webhooks)
- Cuenta de Stripe y/o Mercado Pago
- Git instalado

## 1. Preparación del Servidor

### Clonar el repositorio

```bash
cd /var/www
git clone https://github.com/tu-usuario/calc3d.git
cd calc3d
```

### Crear entorno virtual

```bash
python3 -m venv venv
source venv/bin/activate
```

### Instalar dependencias

```bash
pip install -r requirements.txt
```

## 2. Configuración de Variables de Entorno

Copia el archivo de ejemplo y configúralo:

```bash
cp .env.example .env
nano .env
```

### Variables Críticas

```bash
# IMPORTANTE: Cambiar a production
ENVIRONMENT=production

# Tu dominio real
BASE_URL=https://tu-dominio.com

# Stripe (Producción)
STRIPE_SECRET_KEY=sk_live_tu_clave_real
STRIPE_PUBLISHABLE_KEY=pk_live_tu_clave_publica
STRIPE_WEBHOOK_SECRET=whsec_tu_secreto_webhook
STRIPE_PRICE_ID_PRO=price_id_de_plan_pro
STRIPE_PRICE_ID_BUSINESS=price_id_de_plan_business

# Mercado Pago (Producción - opcional)
MERCADOPAGO_ACCESS_TOKEN=APP-tu_access_token_real
MERCADOPAGO_PUBLIC_KEY=APP-tu_public_key
MERCADOPAGO_WEBHOOK_SECRET=tu_secreto_webhook

# Rate Limiting
RATE_LIMIT_PER_MINUTE=100
RATE_LIMIT_PER_HOUR=1000

# Logging
LOG_LEVEL=INFO
LOG_FILE=/var/log/calc3d/app.log
```

## 3. Configurar Stripe

### 3.1. Crear Productos y Precios

1. Ve a https://dashboard.stripe.com/products
2. Crea dos productos:
   - **Calc3D Pro** - $9.99/mes
   - **Calc3D Business** - $29.99/mes
3. Copia los **Price IDs** (empiezan con `price_...`)
4. Pégalos en `.env` como `STRIPE_PRICE_ID_PRO` y `STRIPE_PRICE_ID_BUSINESS`

### 3.2. Configurar Webhooks

1. Ve a https://dashboard.stripe.com/webhooks
2. Click en "Add endpoint"
3. URL del endpoint: `https://tu-dominio.com/webhooks/stripe`
4. Selecciona estos eventos:
   - `checkout.session.completed`
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.payment_succeeded`
   - `invoice.payment_failed`
5. Copia el **Signing secret** (empieza con `whsec_...`)
6. Pégalo en `.env` como `STRIPE_WEBHOOK_SECRET`

## 4. Configurar Mercado Pago (Opcional)

### 4.1. Obtener Credenciales

1. Ve a https://www.mercadopago.com.ar/developers/panel
2. Cambia a modo **Producción**
3. Copia el **Access Token**
4. Pégalo en `.env` como `MERCADOPAGO_ACCESS_TOKEN`

### 4.2. Configurar Webhooks

1. En el panel de desarrolladores, ve a "Webhooks"
2. URL: `https://tu-dominio.com/webhooks/mercadopago`
3. Eventos: Selecciona todos los de `payment` y `subscription`

## 5. Configurar NGINX

Crea el archivo `/etc/nginx/sites-available/calc3d`:

```nginx
server {
    listen 80;
    server_name tu-dominio.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name tu-dominio.com;

    ssl_certificate /etc/letsencrypt/live/tu-dominio.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/tu-dominio.com/privkey.pem;

    # Límites de tamaño
    client_max_body_size 10M;

    # Logs
    access_log /var/log/nginx/calc3d-access.log;
    error_log /var/log/nginx/calc3d-error.log;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Servir archivos estáticos si los hay
    location /static/ {
        alias /var/www/calc3d/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
```

Habilita el sitio:

```bash
sudo ln -s /etc/nginx/sites-available/calc3d /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## 6. Configurar SSL con Let's Encrypt

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d tu-dominio.com
```

## 7. Configurar Systemd Service

Crea `/etc/systemd/system/calc3d.service`:

```ini
[Unit]
Description=Calc3D - Calculadora de Impresión 3D
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/var/www/calc3d
Environment="PATH=/var/www/calc3d/venv/bin"
ExecStart=/var/www/calc3d/venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000 --workers 4
Restart=always
RestartSec=10

# Logging
StandardOutput=append:/var/log/calc3d/systemd.log
StandardError=append:/var/log/calc3d/systemd-error.log

[Install]
WantedBy=multi-user.target
```

Crear directorio de logs:

```bash
sudo mkdir -p /var/log/calc3d
sudo chown www-data:www-data /var/log/calc3d
```

Iniciar el servicio:

```bash
sudo systemctl daemon-reload
sudo systemctl enable calc3d
sudo systemctl start calc3d
sudo systemctl status calc3d
```

## 8. Verificación

### 8.1. Verificar la Aplicación

```bash
curl https://tu-dominio.com
```

### 8.2. Verificar Webhooks de Stripe

1. Ve a https://dashboard.stripe.com/webhooks
2. Selecciona tu webhook
3. Click en "Send test webhook"
4. Elige evento `checkout.session.completed`
5. Verifica que responda con código 200

### 8.3. Verificar Logs

```bash
tail -f /var/log/calc3d/app.log
tail -f /var/log/calc3d/systemd.log
```

## 9. Mantenimiento

### Actualizar la Aplicación

```bash
cd /var/www/calc3d
git pull
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart calc3d
```

### Backup de Base de Datos

```bash
# Crear backup
cp calc3d.db calc3d.db.backup-$(date +%Y%m%d-%H%M%S)

# Backup automático diario (cron)
crontab -e
# Agregar:
0 2 * * * cp /var/www/calc3d/calc3d.db /var/backups/calc3d-$(date +\%Y\%m\%d).db
```

### Monitoreo de Logs

```bash
# Ver errores recientes
grep ERROR /var/log/calc3d/app.log | tail -20

# Ver webhooks recientes
grep webhook /var/log/calc3d/app.log | tail -20

# Ver rate limiting
grep "Rate limit" /var/log/calc3d/app.log | tail -20
```

## 10. Troubleshooting

### Problema: Webhooks no funcionan

**Solución:**
1. Verifica que HTTPS esté configurado correctamente
2. Revisa los logs: `grep webhook /var/log/calc3d/app.log`
3. Verifica que el webhook secret sea correcto en `.env`
4. Prueba manualmente: `curl -X POST https://tu-dominio.com/webhooks/stripe`

### Problema: Pagos no se procesan

**Solución:**
1. Verifica que uses claves de **producción** (no test)
2. Revisa que los Price IDs sean correctos
3. Verifica logs de Stripe: https://dashboard.stripe.com/logs

### Problema: Rate limiting muy restrictivo

**Solución:**
Ajusta en `.env`:
```bash
RATE_LIMIT_PER_MINUTE=200
RATE_LIMIT_PER_HOUR=5000
```

Luego reinicia:
```bash
sudo systemctl restart calc3d
```

## 11. Seguridad

### Checklist de Seguridad

- [ ] HTTPS configurado y funcionando
- [ ] Variables de entorno protegidas (`.env` con permisos 600)
- [ ] Claves de producción (no test) en uso
- [ ] Webhooks verificando firmas correctamente
- [ ] Rate limiting habilitado
- [ ] Logs monitoreándose regularmente
- [ ] Backups automáticos configurados
- [ ] Firewall configurado (solo puertos 80, 443 abiertos)

### Proteger .env

```bash
chmod 600 .env
chown www-data:www-data .env
```

## 12. Monitoreo y Alertas (Opcional)

### Configurar Uptime Robot

1. Ve a https://uptimerobot.com
2. Agrega monitor HTTP(s)
3. URL: `https://tu-dominio.com/pricing`
4. Configura alertas por email

### Configurar Sentry (Errores)

```bash
pip install sentry-sdk
```

Agrega en `main.py`:
```python
import sentry_sdk
sentry_sdk.init(dsn="tu_dsn_de_sentry")
```

---

## Soporte

Si tienes problemas durante el despliegue:

1. Revisa los logs: `/var/log/calc3d/`
2. Verifica configuración: `grep ERROR /var/log/calc3d/app.log`
3. Contacta soporte

¡Tu aplicación está lista para producción! 🚀
