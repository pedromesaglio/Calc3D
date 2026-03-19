# 🚀 Guía Rápida: VPS Hostinger para calc3d.online

Esta guía te lleva paso a paso desde contratar el VPS hasta tener tu app funcionando.

---

## PARTE 1: Contratar VPS en Hostinger

### Paso 1: Ir a la sección de VPS

1. **Inicia sesión** en https://hpanel.hostinger.com
2. En el menú lateral, busca **"VPS"** o ve directamente a:
   https://www.hostinger.com/vps-hosting

### Paso 2: Elegir el plan

**Recomendación: Plan KVM 1**
- 1 vCore CPU
- 4 GB RAM
- 50 GB almacenamiento SSD
- **Precio: ~$4.99/mes** (puede variar según promociones)

✅ **Este plan es MÁS que suficiente para calc3d.online**

### Paso 3: Configurar el VPS

Durante la compra te preguntará:

**Sistema Operativo:**
- Elige: **Ubuntu 22.04 LTS** ⬅️ IMPORTANTE

**Ubicación del servidor:**
- Si tu público es de Argentina/LATAM: **São Paulo, Brasil**
- Si es global: **Ashburn, EE.UU.** o **Amsterdam, Países Bajos**

**Período:**
- 1 mes (para probar)
- 12 meses (más económico)

**Contraseña root:**
- Crea una contraseña SEGURA
- **ANÓTALA** - la vas a necesitar

### Paso 4: Completar pago

- Usa tu método de pago preferido
- **NO necesitas comprar dominio** (ya tienes calc3d.online)

### Paso 5: Esperar provisión

- Tarda **5-10 minutos**
- Te llegará un email cuando esté listo
- Recibirás la **IP del servidor** (ej: 45.123.45.67)

---

## PARTE 2: Acceder al VPS

### Paso 1: Obtener datos de acceso

En hPanel:
1. Ve a **VPS** (menú lateral)
2. Click en tu VPS
3. Verás:
   ```
   IP Address: 123.456.78.90  ⬅️ ANOTA ESTO
   Root Password: [Set/Change]
   SSH Port: 22
   ```

### Paso 2: Conectar por SSH

**Desde tu computadora (terminal Linux):**

```bash
ssh root@TU_IP_AQUI
```

**Ejemplo real:**
```bash
ssh root@123.456.78.90
```

**Primera vez te preguntará:**
```
Are you sure you want to continue connecting (yes/no)?
```
Escribe: `yes` + Enter

**Luego te pedirá contraseña:**
- Pega la contraseña que creaste
- NO SE VE MIENTRAS ESCRIBES (es normal)
- Presiona Enter

**Si todo va bien, verás:**
```
root@vps-12345:~#
```

¡Estás dentro del servidor! 🎉

---

## PARTE 3: Configurar el Servidor

### Paso 1: Actualizar el sistema

```bash
apt update && apt upgrade -y
```

Esto tarda 2-3 minutos. Espera.

### Paso 2: Instalar todo lo necesario

```bash
apt install -y python3.11 python3.11-venv python3-pip nginx supervisor git ufw
```

### Paso 3: Crear usuario para la app

```bash
# Crear usuario
adduser calc3d
```

Te pedirá:
- **Contraseña**: Crea una (ANÓTALA)
- **Full Name**: (puedes dejar en blanco, Enter)
- **Room Number**, etc.: (Enter en todos)
- **Is the information correct?**: `Y`

```bash
# Dar permisos sudo al usuario
usermod -aG sudo calc3d

# Cambiar a ese usuario
su - calc3d
```

Ahora estás como usuario `calc3d@vps...`

---

## PARTE 4: Subir la Aplicación

### Opción A: Con Git (Recomendado)

**Primero, en tu computadora local:**

```bash
cd /home/pedro/Desktop/calc3d

# Iniciar git si no está
git init

# Ver qué archivos hay
git status

# Agregar todos (excepto venv, .db, .env por el .gitignore)
git add .

# Hacer commit
git commit -m "Primera versión de Calc3D para producción"

# Crear repositorio en GitHub
# Ve a: https://github.com/new
# Nombre: calc3d-app
# Privado: ✅ (recomendado)
# Create repository

# Luego conecta tu repo local:
git remote add origin https://github.com/TU_USUARIO/calc3d-app.git
git branch -M main
git push -u origin main
```

**Ahora, en el servidor VPS (como usuario calc3d):**

```bash
cd ~
git clone https://github.com/TU_USUARIO/calc3d-app.git calc3d
cd calc3d
```

### Opción B: Con SCP (más directo pero menos práctico)

**En tu computadora local:**

```bash
# Asegúrate de estar en el directorio padre
cd /home/pedro/Desktop

# Transferir (reemplaza TU_IP)
scp -r calc3d calc3d@TU_IP:/home/calc3d/

# Ejemplo:
scp -r calc3d calc3d@123.456.78.90:/home/calc3d/
```

Te pedirá la contraseña del usuario `calc3d` del servidor.

---

## PARTE 5: Configurar la Aplicación

**En el servidor VPS (como usuario calc3d):**

### Paso 1: Crear entorno virtual

```bash
cd ~/calc3d
python3.11 -m venv venv
source venv/bin/activate
```

Tu prompt debería verse así: `(venv) calc3d@vps...`

### Paso 2: Instalar dependencias

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

Esto tarda 2-3 minutos.

### Paso 3: Crear archivo .env

```bash
nano .env
```

**Pega este contenido** (ajusta según tus necesidades):

```env
# Entorno
ENVIRONMENT=production
BASE_URL=https://calc3d.online

# Base de datos
DATABASE_PATH=/home/calc3d/calc3d/calc3d.db

# Stripe (OPCIONAL - si vas a usar Stripe)
STRIPE_SECRET_KEY=sk_live_XXXXXXXXX
STRIPE_PUBLISHABLE_KEY=pk_live_XXXXXXXXX
STRIPE_WEBHOOK_SECRET=whsec_XXXXXXXXX
STRIPE_PRICE_ID_PRO=price_XXXXXXXXX
STRIPE_PRICE_ID_BUSINESS=price_XXXXXXXXX

# Mercado Pago (OPCIONAL - si vas a usar Mercado Pago)
MERCADOPAGO_ACCESS_TOKEN=APP_USR-XXXXXXXXX
MERCADOPAGO_PUBLIC_KEY=APP_USR-XXXXXXXXX
MERCADOPAGO_WEBHOOK_SECRET=XXXXXXXXX

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

**Guardar:**
- `Ctrl + O` (guardar)
- Enter (confirmar)
- `Ctrl + X` (salir)

### Paso 4: Crear directorio de logs

```bash
mkdir -p logs
```

### Paso 5: Inicializar base de datos

```bash
python -c "from app.db import init_db; init_db()"
```

Deberías ver: `Database initialized successfully!`

### Paso 6: Probar la aplicación

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

**Abrir navegador:**
`http://TU_IP:8000`

Si ves tu app, ¡funciona! ✅

Presiona `Ctrl + C` para detener.

---

## PARTE 6: Configurar Nginx (Proxy Web)

### Paso 1: Crear configuración

```bash
# Volver a usuario root
exit

# Crear archivo de configuración
sudo nano /etc/nginx/sites-available/calc3d
```

**Pega esto:**

```nginx
server {
    listen 80;
    server_name calc3d.online www.calc3d.online;

    client_max_body_size 20M;

    access_log /var/log/nginx/calc3d_access.log;
    error_log /var/log/nginx/calc3d_error.log;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
```

**Guardar:** `Ctrl+O`, Enter, `Ctrl+X`

### Paso 2: Activar sitio

```bash
sudo ln -s /etc/nginx/sites-available/calc3d /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

Si dice `test is successful`, está todo bien.

---

## PARTE 7: Mantener App Corriendo (Supervisor)

### Paso 1: Crear configuración

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

**Guardar:** `Ctrl+O`, Enter, `Ctrl+X`

### Paso 2: Iniciar aplicación

```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start calc3d
sudo supervisorctl status
```

Deberías ver: `calc3d RUNNING`

---

## PARTE 8: Configurar DNS (Apuntar calc3d.online al VPS)

### Paso 1: En hPanel de Hostinger

1. Ve a **Dominios**
2. Click en **calc3d.online**
3. Click en **DNS / Name Servers**
4. Busca sección **DNS Records**

### Paso 2: Agregar/Editar registros A

**Registro 1:**
- Tipo: `A`
- Nombre: `@`
- Apunta a: `TU_IP_DEL_VPS` (ejemplo: 123.456.78.90)
- TTL: `3600`

**Registro 2:**
- Tipo: `A`
- Nombre: `www`
- Apunta a: `TU_IP_DEL_VPS`
- TTL: `3600`

Click **Save** o **Add Record**

### Paso 3: Esperar propagación DNS

**Tiempo**: 10-30 minutos (a veces hasta 2 horas)

**Verificar desde tu computadora:**

```bash
ping calc3d.online
```

Debería responder con la IP de tu VPS.

---

## PARTE 9: Configurar HTTPS (SSL Gratis)

### Paso 1: Instalar Certbot

**En el servidor VPS (como root):**

```bash
sudo apt install certbot python3-certbot-nginx -y
```

### Paso 2: Obtener certificado

```bash
sudo certbot --nginx -d calc3d.online -d www.calc3d.online
```

Te preguntará:
1. **Email**: Tu email (para avisos de expiración)
2. **Terms**: `Y` (aceptar)
3. **Share email**: `N` (no compartir)
4. **Redirect HTTP to HTTPS**: `2` (sí, redirigir)

### Paso 3: Verificar

**Abrir navegador:**
`https://calc3d.online`

Deberías ver:
- ✅ Candado verde (HTTPS seguro)
- ✅ Tu aplicación funcionando

---

## PARTE 10: Configurar Firewall

```bash
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

Te preguntará si estás seguro, escribe: `y`

---

## ✅ CHECKLIST FINAL

Verifica que todo funcione:

- [ ] VPS contratado y accesible por SSH
- [ ] Aplicación subida al servidor
- [ ] Dependencias instaladas (venv + requirements.txt)
- [ ] Archivo .env configurado
- [ ] Base de datos inicializada
- [ ] Nginx configurado y corriendo
- [ ] Supervisor manteniendo app activa
- [ ] DNS apuntando a VPS (calc3d.online → IP)
- [ ] HTTPS configurado (certificado SSL)
- [ ] Firewall habilitado
- [ ] App accesible en https://calc3d.online

---

## 🎉 ¡LISTO!

Tu aplicación está en línea en:
**https://calc3d.online**

---

## 🔧 Comandos Útiles para el Día a Día

### Ver logs en tiempo real

```bash
# Logs de la aplicación
sudo tail -f /var/log/calc3d.out.log

# Logs de errores
sudo tail -f /var/log/calc3d.err.log
```

### Reiniciar servicios

```bash
# Reiniciar aplicación
sudo supervisorctl restart calc3d

# Reiniciar Nginx
sudo systemctl restart nginx

# Ver estado
sudo supervisorctl status
```

### Actualizar la aplicación (cuando hagas cambios)

```bash
# Conectar al servidor
ssh calc3d@TU_IP

# Ir al directorio
cd ~/calc3d

# Obtener últimos cambios (si usas Git)
git pull origin main

# Activar venv
source venv/bin/activate

# Instalar nuevas dependencias (si las hay)
pip install -r requirements.txt

# Reiniciar app
sudo supervisorctl restart calc3d
```

---

## 🆘 Problemas Comunes

### Error 502 Bad Gateway

```bash
# Ver si la app está corriendo
sudo supervisorctl status calc3d

# Si está STOPPED, ver por qué:
sudo tail -50 /var/log/calc3d.err.log

# Reiniciar
sudo supervisorctl restart calc3d
```

### No puedo conectar por SSH

```bash
# Verificar que tengas la IP correcta
# Verificar que uses el puerto 22
# Verificar contraseña
```

### DNS no resuelve

```bash
# Esperar más tiempo (hasta 2 horas)
# Verificar registros A en hPanel
# Limpiar caché DNS local:
sudo systemd-resolve --flush-caches
```

---

## 📞 Próximos Pasos Opcionales

1. **Configurar webhooks de pago** (Stripe/Mercado Pago)
2. **Configurar backups automáticos**
3. **Monitoreo con Uptime Robot** (gratis)
4. **Optimizar rendimiento** (caché, CDN)

---

## 💰 Costos Totales Mensuales

- Dominio calc3d.online: ~$10/año ≈ $0.83/mes
- VPS KVM 1: ~$4.99/mes
- **TOTAL: ~$5.82/mes** 🎯

¡Muy económico para una app completa en producción!

---

¡Éxito con tu deployment! 🚀
