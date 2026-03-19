# Sistema de Suscripciones y Pagos - Calc3D

## Descripción General

Sistema profesional de suscripciones con múltiples planes, integración de pagos con Stripe y Mercado Pago, rate limiting, y gestión de límites de uso.

## Características Principales

### ✅ Planes de Suscripción

#### **Plan Gratuito**
- 20 cálculos por mes
- 5 presupuestos
- 5 clientes
- 10 piezas en catálogo
- Funcionalidades básicas

#### **Plan Profesional** ($9.99/mes)
- ✨ Cálculos ilimitados
- 100 presupuestos
- 50 clientes
- 100 piezas en catálogo
- Exportación a PDF
- Envío de presupuestos por email
- Análisis y estadísticas
- **14 días de prueba gratis**

#### **Plan Empresa** ($29.99/mes)
- ✨ Todo ilimitado
- Soporte prioritario
- Personalización de marca
- Acceso a API
- Análisis avanzados
- Integraciones personalizadas
- **14 días de prueba gratis**

### 💳 Procesadores de Pago

- **Stripe**: Para pagos internacionales con tarjeta
- **Mercado Pago**: Para Latinoamérica

### 🔒 Seguridad y Límites

- Rate limiting por IP y usuario
- Verificación de webhooks con firmas criptográficas
- Límites de uso por plan
- Manejo profesional de errores
- Logging completo

## Arquitectura del Sistema

```
app/
├── subscriptions.py           # Lógica de suscripciones y límites
├── payments/
│   ├── stripe_integration.py      # Integración con Stripe
│   └── mercadopago_integration.py # Integración con Mercado Pago
├── routes/
│   └── subscriptions.py       # Rutas de suscripciones y webhooks
├── middleware.py              # Rate limiting y verificación de límites
├── config.py                  # Configuración centralizada
├── error_handlers.py          # Manejo de errores
└── db.py                      # Base de datos

templates/
├── pricing.html              # Página de planes
├── subscription.html         # Dashboard de suscripción
└── subscription_success.html # Página de éxito

tests/
├── test_subscriptions.py     # Tests de suscripciones
└── test_payments.py          # Tests de pagos
```

## Flujo de Suscripción

### 1. Usuario Selecciona Plan

```
Usuario → /pricing → Selecciona "Pro" o "Business"
```

### 2. Checkout

```
POST /subscription/checkout
├── Crea customer en Stripe/MP (si no existe)
├── Crea sesión de checkout
└── Redirige a pasarela de pago
```

### 3. Pago Exitoso

```
Stripe/MP → Webhook → /webhooks/stripe
├── Verifica firma del webhook
├── Actualiza suscripción en BD
├── Registra pago
└── Activa plan (con trial de 14 días)
```

### 4. Gestión de Suscripción

```
Usuario → /subscription
├── Ve uso actual (cálculos, presupuestos, etc.)
├── Historial de pagos
├── Puede actualizar plan
├── Puede cancelar (vía Portal de Stripe)
└── Puede gestionar método de pago
```

## Gestión de Límites

### Verificación de Límites

El middleware verifica automáticamente los límites antes de crear recursos:

```python
# Ejemplo interno
from app.middleware import check_usage_limit

# En una ruta
response = await check_usage_limit(request, "calculations")
if response:
    return response  # Usuario alcanzó el límite

# Proceder con la creación...
track_usage(user_id, "calculations")
```

### Reset Mensual

Los límites se resetean automáticamente cada 30 días desde el inicio de la suscripción.

## Webhooks

### Stripe Webhooks

Eventos manejados:

- `checkout.session.completed`: Checkout completado
- `customer.subscription.created`: Suscripción creada
- `customer.subscription.updated`: Suscripción actualizada
- `customer.subscription.deleted`: Suscripción cancelada
- `invoice.payment_succeeded`: Pago exitoso
- `invoice.payment_failed`: Pago fallido

Endpoint: `POST /webhooks/stripe`

### Mercado Pago Webhooks

Eventos manejados:

- `payment`: Notificación de pago
- `subscription_preapproval`: Notificación de suscripción

Endpoint: `POST /webhooks/mercadopago`

## Rate Limiting

### Configuración

```bash
# .env
RATE_LIMIT_PER_MINUTE=100
RATE_LIMIT_PER_HOUR=1000
```

### Comportamiento

- **Por minuto**: Máximo 100 requests
- **Por hora**: Máximo 1000 requests
- Tracking por IP + user_id
- Headers informativos:
  - `X-RateLimit-Limit-Minute`
  - `X-RateLimit-Remaining-Minute`
  - `X-RateLimit-Limit-Hour`
  - `X-RateLimit-Remaining-Hour`

## Configuración de Desarrollo

### 1. Instalar Dependencias

```bash
pip install -r requirements.txt
```

### 2. Configurar Variables de Entorno

```bash
cp .env.example .env
```

Edita `.env` y configura las claves de **prueba** de Stripe:

```bash
ENVIRONMENT=development
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_ID_PRO=price_...
STRIPE_PRICE_ID_BUSINESS=price_...
```

### 3. Ejecutar en Desarrollo

```bash
source venv/bin/activate
uvicorn main:app --reload
```

### 4. Probar Webhooks Localmente

Usa **Stripe CLI** para reenviar webhooks localmente:

```bash
# Instalar Stripe CLI
brew install stripe/stripe-cli/stripe

# Login
stripe login

# Reenviar webhooks
stripe listen --forward-to localhost:8000/webhooks/stripe
```

Esto te dará un `STRIPE_WEBHOOK_SECRET` temporal para desarrollo.

## Tests

### Ejecutar Tests

```bash
# Todos los tests
pytest

# Solo suscripciones
pytest tests/test_subscriptions.py

# Solo pagos
pytest tests/test_payments.py

# Con coverage
pytest --cov=app tests/
```

### Tests Implementados

- ✅ Creación de suscripciones
- ✅ Verificación de límites
- ✅ Incremento de uso
- ✅ Actualización de planes
- ✅ Características por plan
- ✅ Reset de límites
- ✅ Integración Stripe (mocked)
- ✅ Integración Mercado Pago (mocked)

## Ejemplos de Uso

### Verificar Límite Antes de Crear Recurso

```python
from app.subscriptions import check_limit, increment_usage

# Verificar límite
can_use, error = check_limit(user_id, "calculations")

if not can_use:
    return {"error": error}, 403

# Crear recurso...

# Incrementar contador
increment_usage(user_id, "calculations")
```

### Verificar Feature Premium

```python
from app.subscriptions import has_feature

if not has_feature(user_id, "pdf_export"):
    return {"error": "Esta función requiere plan Pro o superior"}, 403

# Generar PDF...
```

### Obtener Info del Plan

```python
from app.subscriptions import get_user_plan_info

plan_info = get_user_plan_info(user_id)

print(f"Plan: {plan_info['plan']['name']}")
print(f"Cálculos usados: {plan_info['usage']['calculations_used']}")
print(f"Puede actualizar: {plan_info['can_upgrade']}")
```

## Base de Datos

### Tablas Nuevas

#### `subscriptions`
- `user_id`: ID del usuario
- `plan`: free | pro | business
- `status`: active | trialing | past_due | canceled | incomplete
- `stripe_customer_id`: ID de customer en Stripe
- `stripe_subscription_id`: ID de suscripción en Stripe
- `mercadopago_customer_id`: ID en Mercado Pago
- Timestamps: `started_at`, `current_period_start`, `current_period_end`

#### `usage_limits`
- `user_id`: ID del usuario
- `calculations_used`: Contador de cálculos
- `quotes_used`: Contador de presupuestos
- `clients_used`: Contador de clientes
- `catalog_items_used`: Contador de piezas
- `reset_at`: Fecha de próximo reset

#### `payments`
- Historial completo de pagos
- `status`: succeeded | pending | failed | canceled | refunded
- `payment_provider`: stripe | mercadopago
- Metadatos del pago

#### `webhook_events`
- Log de todos los webhooks recibidos
- `processed`: 0 | 1
- `error_message`: Si falló el procesamiento

## Troubleshooting

### Webhook no se recibe

1. Verifica que la URL sea correcta y accesible públicamente
2. Revisa logs: `grep webhook calc3d.log`
3. Verifica el webhook secret en `.env`
4. Usa Stripe CLI para debugging local

### Usuario no puede usar recurso

1. Verifica su plan: `SELECT * FROM subscriptions WHERE user_id = X`
2. Verifica uso: `SELECT * FROM usage_limits WHERE user_id = X`
3. Revisa logs de rate limiting

### Pago no se refleja

1. Revisa `webhook_events` table
2. Verifica que el webhook se procesó (`processed = 1`)
3. Revisa `payments` table
4. Verifica logs de Stripe Dashboard

## Mejoras Futuras

- [ ] Webhooks de Mercado Pago más robustos
- [ ] Panel de admin para gestión de suscripciones
- [ ] Métricas y analytics de conversión
- [ ] Cupones y descuentos
- [ ] Facturación automática
- [ ] Multi-tenant support
- [ ] Exportar reportes de facturación

## Recursos

- [Documentación de Stripe](https://stripe.com/docs)
- [Documentación de Mercado Pago](https://www.mercadopago.com.ar/developers/es/docs)
- [Guía de Despliegue](./DEPLOYMENT.md)

---

**Versión**: 2.0.0
**Autor**: Calc3D Team
**Licencia**: MIT
