# Guía de Deployment en Hostinger - Calc3D

Esta guía te llevará paso a paso para subir tu aplicación FastAPI a Hostinger.

## Prerequisitos

- Cuenta de Hostinger con plan que soporte Python/SSH
- Acceso SSH habilitado
- Base de datos disponible (SQLite o MySQL)

---

## Paso 1: Preparar la aplicación para producción

### 1.1 Crear archivo de requirements.txt actualizado

```bash
cd /home/pedro/Desktop/calc3d
source venv/bin/activate
pip freeze > requirements.txt
```

### 1.2 Crear archivo .env.example (plantilla)

Crea `.env.example` con variables necesarias (sin valores sensibles):

```env
# Entorno
ENVIRONMENT=production
BASE_URL=https://tu-dominio.com

# Base de datos
DATABASE_PATH=calc3d.db

# Stripe (opcional)
STRIPE_SECRET_KEY=sk_live_...
STRIPE_PUBLISHABLE_KEY=pk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_ID_PRO=price_...
STRIPE_PRICE_ID_BUSINESS=price_...

# Mercado Pago (opcional)
MERCADOPAGO_ACCESS_TOKEN=APP_USR-...
MERCADOPAGO_PUBLIC_KEY=APP_USR-...
MERCADOPAGO_WEBHOOK_SECRET=...

# Seguridad
PBKDF2_ITERATIONS=260000
SESSION_TIMEOUT_HOURS=24

# Rate Limiting
RATE_LIMIT_PER_MINUTE=100
RATE_LIMIT_PER_HOUR=1000

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/calc3d.log
```

### 1.3 Crear script de inicio

Crea `start.sh`:

```bash
#!/bin/bash
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 2
```

### 1.4 Ignorar archivos sensibles

Verifica `.gitignore`:

```
venv/
__pycache__/
*.pyc
*.db
.env
*.log
logs/
.pytest_cache/
```

---

## Paso 2: Opciones de Deployment en Hostinger

Hostinger ofrece varios tipos de hosting. Aquí las opciones:

### Opción A: Hostinger VPS (Recomendado para FastAPI)
- Control total del servidor
- Soporte para Python y FastAPI
- Acceso SSH completo
- **Precio**: ~$4-8 USD/mes

### Opción B: Hostinger Shared Hosting con Python
- Limitado, puede no soportar FastAPI completamente
- Menos control
- **No recomendado para esta app**

### Opción C: Hostinger Cloud Hosting
- Balance entre VPS y Shared
- Buen soporte para aplicaciones Python
- **Precio**: ~$9-15 USD/mes

**RECOMENDACIÓN**: Usa VPS de Hostinger para mejor control y compatibilidad.

---

## Paso 3: Configurar VPS en Hostinger

### 3.1 Crear VPS

1. Inicia sesión en Hostinger
2. Ve a **VPS** → **Agregar VPS**
3. Selecciona plan (KVM 1 o superior)
4. Elige sistema operativo: **Ubuntu 22.04 LTS**
5. Configura contraseña root
6. Espera provisión (~5 minutos)

### 3.2 Acceder por SSH

Desde tu terminal local:

```bash
# Reemplaza IP_DE_TU_VPS con la IP real
ssh root@IP_DE_TU_VPS
```

Ingresa la contraseña que configuraste.

---

## Paso 4: Configurar el Servidor (Ubuntu)

### 4.1 Actualizar sistema

```bash
apt update && apt upgrade -y
```

### 4.2 Instalar Python y dependencias

```bash
apt install -y python3.11 python3.11-venv python3-pip nginx supervisor git
```

### 4.3 Crear usuario para la aplicación

```bash
adduser calc3d
usermod -aG sudo calc3d
su - calc3d
```

### 4.4 Configurar firewall

```bash
# Como root
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw enable
```

---

## Paso 5: Subir la aplicación al servidor

### 5.1 Opción A: Git (Recomendado)

**En tu máquina local:**

```bash
cd /home/pedro/Desktop/calc3d

# Inicializar git si no está
git init
git add .
git commit -m "Deploy a producción"

# Subir a GitHub/GitLab (privado)
# Ejemplo con GitHub:
git remote add origin https://github.com/TU-USUARIO/calc3d.git
git branch -M main
git push -u origin main
```

**En el servidor (como usuario calc3d):**

```bash
cd ~
git clone https://github.com/TU-USUARIO/calc3d.git
cd calc3d
```

### 5.2 Opción B: SCP (Transferencia directa)

**En tu máquina local:**

```bash
cd /home/pedro/Desktop
scp -r calc3d calc3d@IP_DE_TU_VPS:~/
```

---

## Paso 6: Configurar la aplicación en el servidor

### 6.1 Crear entorno virtual

```bash
cd ~/calc3d
python3.11 -m venv venv
source venv/bin/activate
```

### 6.2 Instalar dependencias

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 6.3 Crear archivo .env

```bash
nano .env
```

Copia el contenido de `.env.example` y rellena con valores reales:

```env
ENVIRONMENT=production
BASE_URL=https://tu-dominio.com
DATABASE_PATH=/home/calc3d/calc3d/calc3d.db
# ... resto de variables
```

Guarda con `Ctrl+O`, Enter, `Ctrl+X`

### 6.4 Inicializar base de datos

```bash
python -c "from app.db import init_db; init_db()"
```

### 6.5 Probar la aplicación

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

Abre navegador: `http://IP_DE_TU_VPS:8000`

Si funciona, presiona `Ctrl+C` para detener.

---

## Paso 7: Configurar Nginx como Reverse Proxy

### 7.1 Crear configuración de Nginx

```bash
sudo nano /etc/nginx/sites-available/calc3d
```

Pega esta configuración:

```nginx
server {
    listen 80;
    server_name tu-dominio.com www.tu-dominio.com;  # Cambia esto

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

    # Archivos estáticos (si tienes)
    location /static {
        alias /home/calc3d/calc3d/static;
        expires 30d;
    }
}
```

### 7.2 Activar sitio

```bash
sudo ln -s /etc/nginx/sites-available/calc3d /etc/nginx/sites-enabled/
sudo nginx -t  # Verificar configuración
sudo systemctl restart nginx
```

---

## Paso 8: Configurar Supervisor (mantener app corriendo)

### 8.1 Crear configuración de Supervisor

```bash
sudo nano /etc/supervisor/conf.d/calc3d.conf
```

Pega:

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

### 8.2 Activar aplicación

```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start calc3d
sudo supervisorctl status calc3d
```

---

## Paso 9: Configurar Dominio

### 9.1 En Hostinger Panel

1. Ve a **Dominios**
2. Selecciona tu dominio
3. Ve a **DNS/Name Servers**
4. Agrega registro A:
   - **Tipo**: A
   - **Nombre**: @ (o tu subdominio)
   - **Apunta a**: IP_DE_TU_VPS
   - **TTL**: 3600

5. Agrega registro A para www:
   - **Tipo**: A
   - **Nombre**: www
   - **Apunta a**: IP_DE_TU_VPS
   - **TTL**: 3600

Espera 10-30 minutos para propagación DNS.

---

## Paso 10: Configurar HTTPS con Let's Encrypt (SSL)

### 10.1 Instalar Certbot

```bash
sudo apt install certbot python3-certbot-nginx -y
```

### 10.2 Obtener certificado

```bash
sudo certbot --nginx -d tu-dominio.com -d www.tu-dominio.com
```

Sigue las instrucciones:
- Ingresa email
- Acepta términos
- Elige redirección automática HTTP → HTTPS (opción 2)

### 10.3 Renovación automática

Certbot configura renovación automática. Verificar:

```bash
sudo certbot renew --dry-run
```

---

## Paso 11: Configurar Webhooks de Pago

### 11.1 Stripe Webhooks

1. Ve a https://dashboard.stripe.com/webhooks
2. Click **Add endpoint**
3. URL: `https://tu-dominio.com/webhooks/stripe`
4. Eventos a escuchar:
   - `checkout.session.completed`
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.payment_succeeded`
   - `invoice.payment_failed`
5. Copia **Signing secret** → agregar a `.env` como `STRIPE_WEBHOOK_SECRET`

### 11.2 Mercado Pago Webhooks

1. Ve a https://www.mercadopago.com.ar/developers/panel/webhooks
2. Agrega URL: `https://tu-dominio.com/webhooks/mercadopago`
3. Copia secret → agregar a `.env` como `MERCADOPAGO_WEBHOOK_SECRET`

### 11.3 Reiniciar aplicación

```bash
sudo supervisorctl restart calc3d
```

---

## Paso 12: Configurar Backups Automáticos

### 12.1 Crear script de backup

```bash
mkdir -p ~/backups
nano ~/backup.sh
```

Contenido:

```bash
#!/bin/bash
BACKUP_DIR="/home/calc3d/backups"
DATE=$(date +%Y%m%d_%H%M%S)
DB_PATH="/home/calc3d/calc3d/calc3d.db"

# Backup de base de datos
cp $DB_PATH $BACKUP_DIR/calc3d_$DATE.db

# Mantener solo últimos 7 días
find $BACKUP_DIR -name "calc3d_*.db" -mtime +7 -delete

echo "Backup completado: $DATE"
```

Hacer ejecutable:

```bash
chmod +x ~/backup.sh
```

### 12.2 Configurar cron

```bash
crontab -e
```

Agregar (backup diario a las 2 AM):

```
0 2 * * * /home/calc3d/backup.sh >> /home/calc3d/backup.log 2>&1
```

---

## Paso 13: Monitoreo y Mantenimiento

### 13.1 Ver logs

```bash
# Logs de la aplicación
sudo tail -f /var/log/calc3d.out.log
sudo tail -f /var/log/calc3d.err.log

# Logs de Nginx
sudo tail -f /var/log/nginx/calc3d_access.log
sudo tail -f /var/log/nginx/calc3d_error.log

# Logs de Supervisor
sudo supervisorctl tail -f calc3d
```

### 13.2 Reiniciar servicios

```bash
# Reiniciar aplicación
sudo supervisorctl restart calc3d

# Reiniciar Nginx
sudo systemctl restart nginx

# Ver estado
sudo supervisorctl status
sudo systemctl status nginx
```

### 13.3 Actualizar aplicación

```bash
cd ~/calc3d
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
sudo supervisorctl restart calc3d
```

---

## Paso 14: Seguridad Adicional

### 14.1 Cambiar puerto SSH (opcional)

```bash
sudo nano /etc/ssh/sshd_config
# Cambiar: Port 22 → Port 2222
sudo systemctl restart ssh

# Actualizar firewall
sudo ufw allow 2222/tcp
sudo ufw delete allow 22/tcp
```

### 14.2 Configurar Fail2Ban

```bash
sudo apt install fail2ban -y
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

### 14.3 Limitar conexiones SSH

```bash
sudo nano /etc/ssh/sshd_config
```

Agregar:
```
MaxAuthTries 3
PermitRootLogin no
```

Reiniciar:
```bash
sudo systemctl restart ssh
```

---

## Checklist Final

- [ ] VPS configurado y corriendo
- [ ] Aplicación corriendo con Supervisor
- [ ] Nginx configurado como reverse proxy
- [ ] Dominio apuntando al VPS
- [ ] HTTPS configurado con Let's Encrypt
- [ ] Webhooks de Stripe/Mercado Pago configurados
- [ ] Backups automáticos configurados
- [ ] Logs accesibles y monitoreados
- [ ] Variables de entorno en producción configuradas
- [ ] Firewall habilitado
- [ ] Fail2Ban instalado

---

## Troubleshooting Común

### Problema: Aplicación no inicia

```bash
# Ver logs
sudo supervisorctl tail -f calc3d

# Verificar puerto
sudo netstat -tulpn | grep 8000

# Reiniciar
sudo supervisorctl restart calc3d
```

### Problema: Error 502 Bad Gateway

```bash
# Verificar que aplicación esté corriendo
sudo supervisorctl status calc3d

# Ver logs de Nginx
sudo tail -f /var/log/nginx/calc3d_error.log
```

### Problema: Base de datos locked

```bash
# Verificar permisos
ls -la ~/calc3d/calc3d.db

# Ajustar permisos
chmod 644 ~/calc3d/calc3d.db
```

---

## Recursos Adicionales

- **Hostinger Docs**: https://support.hostinger.com/
- **FastAPI Deployment**: https://fastapi.tiangolo.com/deployment/
- **Nginx Docs**: https://nginx.org/en/docs/
- **Certbot**: https://certbot.eff.org/

---

## Soporte

Si encuentras problemas, revisa:
1. Logs de la aplicación (`/var/log/calc3d.out.log`)
2. Logs de Nginx (`/var/log/nginx/calc3d_error.log`)
3. Estado de Supervisor (`sudo supervisorctl status`)

¡Tu aplicación Calc3D está lista para producción! 🚀
