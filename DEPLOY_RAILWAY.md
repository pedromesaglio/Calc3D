# Guía de Despliegue en Railway

Esta guía te ayudará a desplegar Calc3D en Railway paso a paso.

## 📋 Pre-requisitos

- Cuenta en [Railway](https://railway.app)
- Repositorio Git (GitHub, GitLab o Bitbucket)
- Cuenta de Stripe (opcional, para suscripciones)

## 🚀 Paso 1: Preparar el código

Los siguientes archivos ya están configurados en el proyecto:

- ✅ `Procfile` - Define cómo Railway ejecutará la app
- ✅ `railway.json` - Configuración de deployment
- ✅ `requirements.txt` - Dependencias de Python
- ✅ `.env.example` - Plantilla de variables de entorno

## 📦 Paso 2: Subir código a Git

Si aún no has hecho commit de los últimos cambios:

```bash
git add .
git commit -m "chore: preparar app para Railway deployment"
git push origin main
```

## ☁️ Paso 3: Crear proyecto en Railway

1. Ve a [railway.app](https://railway.app) y haz login
2. Click en **"New Project"**
3. Selecciona **"Deploy from GitHub repo"**
4. Autoriza Railway a acceder a tu repositorio
5. Selecciona el repositorio `calc3d`
6. Railway detectará automáticamente que es una app Python

## 🔧 Paso 4: Configurar variables de entorno

En el dashboard de Railway, ve a **"Variables"** y agrega las siguientes:

### Variables obligatorias:

```bash
ENVIRONMENT=production
BASE_URL=https://tu-app.railway.app  # Railway te dará esta URL
```

### Si usas el plan gratuito (sin suscripciones):

Eso es todo. La app funcionará sin configuración de pagos.

### Si vas a habilitar suscripciones (Stripe):

```bash
STRIPE_SECRET_KEY=sk_live_xxxxx
STRIPE_PUBLISHABLE_KEY=pk_live_xxxxx
STRIPE_WEBHOOK_SECRET=whsec_xxxxx
STRIPE_PRICE_ID_PRO=price_xxxxx
STRIPE_PRICE_ID_BUSINESS=price_xxxxx
```

Para obtener estas credenciales:
1. Ve a [Stripe Dashboard](https://dashboard.stripe.com)
2. En **Developers > API Keys** copia las claves
3. En **Products** crea dos productos (Pro y Business) y copia los Price IDs
4. Los webhooks los configurarás en el Paso 6

### Opcional - Rate Limiting:

```bash
RATE_LIMIT_PER_MINUTE=100
RATE_LIMIT_PER_HOUR=1000
```

## 💾 Paso 5: Configurar almacenamiento persistente

Railway proporciona volúmenes persistentes para la base de datos:

1. En tu proyecto de Railway, ve a la pestaña **"Data"**
2. Click en **"+ New Volume"**
3. Configura:
   - **Mount Path**: `/data`
   - **Size**: 1 GB (suficiente para empezar)
4. Agrega esta variable de entorno:
   ```bash
   DATABASE_PATH=/data/calc3d.db
   ```

## 🎯 Paso 6: Deploy

1. Railway desplegará automáticamente después de configurar las variables
2. Espera 2-3 minutos mientras construye y despliega
3. Railway te asignará una URL tipo: `https://calc3d-production.up.railway.app`
4. Actualiza la variable `BASE_URL` con tu URL real
5. Railway re-desplegará automáticamente

## 🔗 Paso 7: Configurar webhooks de Stripe (si usas suscripciones)

1. Ve a [Stripe Dashboard > Webhooks](https://dashboard.stripe.com/webhooks)
2. Click en **"Add endpoint"**
3. URL del endpoint: `https://tu-app.railway.app/webhooks/stripe`
4. Selecciona estos eventos:
   - `checkout.session.completed`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.payment_succeeded`
   - `invoice.payment_failed`
5. Copia el **Signing secret** (empieza con `whsec_`)
6. Agrégalo como `STRIPE_WEBHOOK_SECRET` en Railway

## ✅ Paso 8: Verificar que todo funciona

1. Abre tu app en `https://tu-app.railway.app`
2. Verifica que carga correctamente
3. Crea una cuenta de prueba
4. Realiza un cálculo de costos
5. Si configuraste Stripe, prueba el flujo de suscripción en modo test

## 📊 Monitoreo

Railway proporciona:

- **Logs en tiempo real**: Pestaña "Deployments" > Click en deployment > "View Logs"
- **Métricas**: CPU, memoria, red
- **Alertas**: Configúralas en Settings

## 🔄 Actualizaciones automáticas

Railway re-desplegará automáticamente cuando hagas push a tu rama principal:

```bash
git add .
git commit -m "feat: nueva funcionalidad"
git push origin main
```

## 💰 Costos

Railway ofrece:

- **Plan Hobby**: $5/mes + $0.000231/GB-hour
- **Plan gratuito**: 500 horas/mes (suficiente para desarrollo)

Estima ~$5-10/mes para una app en producción con tráfico moderado.

## 🐛 Troubleshooting

### La app no inicia

Revisa los logs en Railway:
```bash
# En la pestaña Deployments > View Logs
```

Verifica que todas las variables de entorno obligatorias están configuradas.

### Error de base de datos

Verifica que:
- El volumen está montado en `/data`
- `DATABASE_PATH=/data/calc3d.db` está configurado
- El volumen tiene espacio suficiente

### Webhooks de Stripe no funcionan

1. Verifica que `STRIPE_WEBHOOK_SECRET` esté configurado
2. En Stripe Dashboard, verifica que el endpoint apunta a la URL correcta
3. Revisa los logs de Railway para ver si los webhooks están llegando

### Error "Configuration validation failed"

Esto significa que falta configuración obligatoria. Si usas `ENVIRONMENT=production`, debes configurar al menos Stripe o Mercado Pago.

Para deshabilitar la validación estricta temporalmente, cambia:
```bash
ENVIRONMENT=development
```

## 📚 Recursos adicionales

- [Railway Docs](https://docs.railway.app)
- [FastAPI Deployment Guide](https://fastapi.tiangolo.com/deployment/)
- [Stripe Webhooks Guide](https://stripe.com/docs/webhooks)

## 🎉 ¡Listo!

Tu app Calc3D ahora está en producción. Comparte tu URL con tus usuarios.

Para soporte, revisa los otros archivos de documentación en el proyecto.
