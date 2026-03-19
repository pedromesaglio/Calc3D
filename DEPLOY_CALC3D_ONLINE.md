# 🚀 Deployment de Calc3D en calc3d.online

Guía específica para tu dominio y proyecto.

---

## 📋 Tu Configuración

- **Dominio**: calc3d.online
- **Aplicación**: Calc3D (FastAPI + SQLite)
- **Hosting**: Hostinger (tipo por confirmar)

---

## Paso 1: Verificar tipo de hosting contratado

### En hPanel de Hostinger:

1. Ve a https://hpanel.hostinger.com
2. Inicia sesión
3. Busca tu dominio `calc3d.online`
4. Verifica qué tipo de hosting tienes:

```
┌─────────────────────────────────────────┐
│ SI VES ESTO → TIENES ESTO              │
├─────────────────────────────────────────┤
│ "hPanel" + "File Manager"               │
│ → Shared Hosting (Web Hosting)         │
│                                          │
│ "VPS" + IP address + "SSH Access"      │
│ → VPS Hosting ✅ IDEAL                  │
│                                          │
│ "Cloud Hosting" + SSH limitado          │
│ → Cloud Hosting ✅ FUNCIONA             │
│                                          │
│ Solo "Dominios" sin hosting             │
│ → Solo dominio (necesitas hosting)      │
└─────────────────────────────────────────┘
```

---

## ⚠️ SI TIENES SHARED HOSTING (Web Hosting)

**PROBLEMA**: Shared hosting de Hostinger NO soporta FastAPI bien.

**SOLUCIÓN A**: Migrar a VPS
1. En hPanel, ve a "Hosting" → "Upgrade"
2. Selecciona VPS KVM 1 (~$4/mes)
3. Sigue con "Paso 2A: VPS" más abajo

**SOLUCIÓN B**: Usar otro servicio para la app
1. Mantén dominio en Hostinger
2. Usa Railway/Render/Heroku para la app (gratis/barato)
3. Apunta dominio a ese servicio

**¿Cuál prefieres?** Te explico la que elijas.

---

## ✅ SI TIENES VPS o CLOUD HOSTING

¡Perfecto! Continúa con los siguientes pasos.

---

## Paso 2A: Configurar VPS (Si tienes VPS)

### 2.1 Obtener datos de acceso

En hPanel:
1. Ve a "VPS" → Tu VPS
2. Anota estos datos:
   ```
   IP del servidor: ___.___.___.___ (ejemplo: 45.12.123.45)
   Usuario root: root
   Contraseña: ________________ (la que configuraste)
   ```

### 2.2 Conectar por SSH

**Desde tu computadora Linux:**

```bash
ssh root@TU_IP_AQUI
# Ejemplo: ssh root@45.12.123.45
```

Te pedirá la contraseña. Ingrésala.

**Si es la primera vez**, verás:
```
The authenticity of host '45.12.123.45' can't be established.
Are you sure you want to continue connecting (yes/no)?
```
Escribe: `yes`

### 2.3 Actualizar sistema

```bash
apt update && apt upgrade -y
```

### 2.4 Instalar dependencias

```bash
apt install -y python3.11 python3.11-venv python3-pip nginx supervisor git curl
```

### 2.5 Crear usuario para la aplicación

```bash
# Crear usuario
adduser calc3d
# Te pedirá contraseña, ingresa una segura

# Dar permisos sudo
usermod -aG sudo calc3d

# Cambiar a ese usuario
su - calc3d
```

---

## Paso 3: Subir la aplicación al servidor

### Opción A: Usando Git (Recomendado)

**En tu computadora local:**

```bash
cd /home/pedro/Desktop/calc3d

# Si no tienes git init
git init

# Crear .gitignore (ya existe pero verificar)
cat .gitignore  # Debe incluir: venv/, *.db, .env

# Hacer commit
git add .
git commit -m "Deploy inicial a calc3d.online"

# Subir a GitHub (privado recomendado)
# Primero crea repo en https://github.com/new
# Luego:
git remote add origin https://github.com/TU_USUARIO/calc3d.git
git branch -M main
git push -u origin main
```

**En el servidor (como usuario calc3d):**

```bash
cd ~
git clone https://github.com/TU_USUARIO/calc3d.git
cd calc3d
```

### Opción B: Usando SCP (transferencia directa)

**En tu computadora local:**

```bash
cd /home/pedro/Desktop
scp -r calc3d calc3d@TU_IP:/home/calc3d/
# Ejemplo: scp -r calc3d calc3d@45.12.123.45:/home/calc3d/
```

---

## Paso 4: Configurar la aplicación

### 4.1 Crear entorno virtual

```bash
cd ~/calc3d
python3.11 -m venv venv
source venv/bin/activate
```

### 4.2 Instalar dependencias

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4.3 Crear archivo .env

```bash
nano .env
```

**Pega este contenido** (ajusta los valores):

```env
# Entorno
ENVIRONMENT=production
BASE_URL=https://calc3d.online

# Base de datos
DATABASE_PATH=/home/calc3d/calc3d/calc3d.db

# Stripe (si tienes cuenta)
STRIPE_SECRET_KEY=sk_live_TU_CLAVE_AQUI
STRIPE_PUBLISHABLE_KEY=pk_live_TU_CLAVE_AQUI
STRIPE_WEBHOOK_SECRET=whsec_TU_SECRET_AQUI
STRIPE_PRICE_ID_PRO=price_TU_ID_PRO
STRIPE_PRICE_ID_BUSINESS=price_TU_ID_BUSINESS

# Mercado Pago (si tienes cuenta)
MERCADOPAGO_ACCESS_TOKEN=APP_USR-TU_TOKEN_AQUI
MERCADOPAGO_PUBLIC_KEY=APP_USR-TU_PUBLIC_KEY
MERCADOPAGO_WEBHOOK_SECRET=TU_SECRET_AQUI

# Seguridad
PBKDF2_ITERATIONS=260000
SESSION_TIMEOUT_HOURS=24

# Rate Limiting
RATE_LIMIT_PER_MINUTE=100
RATE_LIMIT_PER_HOUR=1000

# Logging
LOG_LEVEL=INFO
LOG_FILE=/home/calc3d/calc3d/logs/calc3d.log
```

**Guarda con**: `Ctrl+O`, Enter, `Ctrl+X`

### 4.4 Crear directorio de logs

```bash
mkdir -p ~/calc3d/logs
```

### 4.5 Inicializar base de datos

```bash
python -c "from app.db import init_db; init_db()"
```

### 4.6 Probar la aplicación

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

En tu navegador: `http://TU_IP:8000`

Si ves la aplicación, ¡funciona! Presiona `Ctrl+C` para detener.

---

## Paso 5: Configurar Nginx

### 5.1 Crear configuración

```bash
sudo nano /etc/nginx/sites-available/calc3d
```

**Pega esto:**

```nginx
server {
    listen 80;
    server_name calc3d.online www.calc3d.online;

    client_max_body_size 20M;

    # Logs
    access_log /var/log/nginx/calc3d_access.log;
    error_log /var/log/nginx/calc3d_error.log;

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
}
```

**Guarda**: `Ctrl+O`, Enter, `Ctrl+X`

### 5.2 Activar sitio

```bash
sudo ln -s /etc/nginx/sites-available/calc3d /etc/nginx/sites-enabled/
sudo nginx -t  # Verificar sintaxis
sudo systemctl restart nginx
```

---

## Paso 6: Configurar Supervisor (mantener app corriendo)

### 6.1 Crear configuración

```bash
sudo nano /etc/supervisor/conf.d/calc3d.conf
```

**Pega:**

```ini
[program:calc3d]
directory=/home/calc3d/calc3d
command=/home/calc3d/calc3d/venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000 --workers 2
user=calc3d
autostart=true
autorestart=true
stderr_logfile=/var/log/calc3d.err.log
stdout_logfile=/var/log/calc3d.out.log
environment=PATH="/home/calc3d/calc3d/venv/bin"
```

**Guarda**: `Ctrl+O`, Enter, `Ctrl+X`

### 6.2 Activar

```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start calc3d
sudo supervisorctl status calc3d
```

Deberías ver: `calc3d RUNNING`

---

## Paso 7: Configurar DNS del dominio

### 7.1 En hPanel de Hostinger

1. Ve a **Dominios** → `calc3d.online`
2. Click en **DNS / Name Servers**
3. Busca **DNS Records**

### 7.2 Configurar registros A

**Agregar o editar estos registros:**

| Tipo | Nombre | Apunta a       | TTL  |
|------|--------|----------------|------|
| A    | @      | TU_IP_DEL_VPS  | 3600 |
| A    | www    | TU_IP_DEL_VPS  | 3600 |

Ejemplo:
- Tipo: `A`
- Nombre: `@`
- Apunta a: `45.12.123.45` (tu IP real)
- TTL: `3600`

**Espera 10-30 minutos** para que DNS se propague.

### 7.3 Verificar DNS

```bash
# En tu computadora local
dig calc3d.online
ping calc3d.online
```

Debería responder con tu IP del VPS.

---

## Paso 8: Configurar HTTPS (SSL gratis)

### 8.1 Instalar Certbot

```bash
sudo apt install certbot python3-certbot-nginx -y
```

### 8.2 Obtener certificado

```bash
sudo certbot --nginx -d calc3d.online -d www.calc3d.online
```

Te preguntará:
1. **Email**: Ingresa tu email
2. **Términos**: `Y` (yes)
3. **Newsletter**: `N` (no)
4. **Redirect HTTP → HTTPS**: `2` (yes, redirect)

### 8.3 Verificar

Abre navegador: `https://calc3d.online`

Deberías ver tu aplicación con candado 🔒 (HTTPS seguro)

---

## Paso 9: Configurar Firewall

```bash
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable
```

---

## Paso 10: Configurar Webhooks de Pago

### 10.1 Stripe

1. Ve a https://dashboard.stripe.com/webhooks
2. Click **Add endpoint**
3. **URL**: `https://calc3d.online/webhooks/stripe`
4. **Eventos**:
   - `checkout.session.completed`
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.payment_succeeded`
   - `invoice.payment_failed`
5. Copia **Signing secret** → actualizar `.env`:
   ```bash
   nano ~/calc3d/.env
   # Agregar: STRIPE_WEBHOOK_SECRET=whsec_...
   ```

### 10.2 Mercado Pago

1. Ve a https://www.mercadopago.com.ar/developers/panel/webhooks
2. **URL**: `https://calc3d.online/webhooks/mercadopago`
3. Copia secret → actualizar en `.env`

### 10.3 Reiniciar app

```bash
sudo supervisorctl restart calc3d
```

---

## ✅ Checklist Final

- [ ] VPS configurado y accesible por SSH
- [ ] Aplicación subida al servidor
- [ ] Entorno virtual creado y dependencias instaladas
- [ ] Archivo .env configurado
- [ ] Base de datos inicializada
- [ ] Nginx configurado como reverse proxy
- [ ] Supervisor manteniendo app corriendo
- [ ] DNS apuntando a VPS (calc3d.online → IP)
- [ ] HTTPS configurado con Let's Encrypt
- [ ] Firewall habilitado
- [ ] Webhooks configurados (Stripe/Mercado Pago)
- [ ] App accesible en https://calc3d.online

---

## 🔧 Comandos Útiles

### Ver logs en tiempo real
```bash
# Logs de la aplicación
sudo tail -f /var/log/calc3d.out.log
sudo tail -f /var/log/calc3d.err.log

# Logs de Nginx
sudo tail -f /var/log/nginx/calc3d_access.log
sudo tail -f /var/log/nginx/calc3d_error.log
```

### Reiniciar servicios
```bash
sudo supervisorctl restart calc3d  # Reiniciar app
sudo systemctl restart nginx       # Reiniciar Nginx
sudo supervisorctl status          # Ver estado
```

### Actualizar aplicación
```bash
cd ~/calc3d
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
sudo supervisorctl restart calc3d
```

---

## 🆘 Problemas Comunes

### Error 502 Bad Gateway
```bash
# Verificar que app esté corriendo
sudo supervisorctl status calc3d

# Ver logs
sudo tail -f /var/log/calc3d.err.log
```

### App no inicia
```bash
# Ver logs detallados
sudo supervisorctl tail -f calc3d

# Verificar permisos
ls -la ~/calc3d/calc3d.db
```

### DNS no resuelve
```bash
# Verificar desde servidor
dig calc3d.online

# Esperar propagación (hasta 30 min)
```

---

## 🎉 ¡Listo!

Tu aplicación Calc3D está en línea en:
- **URL**: https://calc3d.online
- **Panel Admin**: https://calc3d.online/admin (si lo configuras)
- **Pricing**: https://calc3d.online/pricing

---

## 📞 Próximos Pasos

1. Crear usuario administrador
2. Configurar cuentas de Stripe/Mercado Pago
3. Configurar backups automáticos
4. Monitorear logs regularmente

¡Felicitaciones por tu deployment! 🚀
