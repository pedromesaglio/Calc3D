"""
Modelos Pydantic para validación de datos de entrada y respuesta
"""
from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field, EmailStr, field_validator, ConfigDict
from decimal import Decimal


# ============================================================================
# MODELOS DE AUTENTICACIÓN
# ============================================================================

class UserRegister(BaseModel):
    """Validación para registro de usuario"""
    username: str = Field(..., min_length=3, max_length=50, pattern=r'^[a-zA-Z0-9_-]+$')
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)

    @field_validator('password')
    @classmethod
    def password_strength(cls, v: str) -> str:
        """Valida que la contraseña tenga mínima seguridad"""
        if not any(c.isupper() for c in v):
            raise ValueError('La contraseña debe contener al menos una mayúscula')
        if not any(c.islower() for c in v):
            raise ValueError('La contraseña debe contener al menos una minúscula')
        if not any(c.isdigit() for c in v):
            raise ValueError('La contraseña debe contener al menos un número')
        return v


class UserLogin(BaseModel):
    """Validación para login"""
    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1, max_length=100)


# ============================================================================
# MODELOS DE CÁLCULO
# ============================================================================

class CalculationInput(BaseModel):
    """Validación para cálculo de costos"""
    model_config = ConfigDict(str_strip_whitespace=True)

    weight_g: float = Field(..., gt=0, le=10000, description="Peso en gramos (debe ser positivo, máx 10kg)")
    filament_id: int = Field(..., gt=0, description="ID del filamento")
    print_time_hours: float = Field(..., gt=0, le=1000, description="Tiempo de impresión en horas")
    electricity_watts: float = Field(default=100, ge=0, le=5000, description="Consumo en watts")
    electricity_rate: float = Field(default=0.15, ge=0, le=10, description="Tarifa eléctrica por kWh")
    other_costs: float = Field(default=0, ge=0, le=10000, description="Otros costos")
    markup: float = Field(default=2.0, gt=0, le=100, description="Multiplicador de precio")
    quantity: int = Field(default=1, gt=0, le=10000, description="Cantidad de unidades")

    @field_validator('markup')
    @classmethod
    def validate_markup(cls, v: float) -> float:
        """Asegura que el markup sea razonable"""
        if v < 1.0:
            raise ValueError('El multiplicador debe ser al menos 1.0 (sin ganancia)')
        return v


# ============================================================================
# MODELOS DE SUSCRIPCIONES
# ============================================================================

PlanType = Literal["free", "pro", "business"]
SubscriptionStatus = Literal["active", "canceled", "past_due", "trialing", "incomplete"]
PaymentProvider = Literal["stripe", "mercadopago"]


class CheckoutRequest(BaseModel):
    """Validación para solicitud de checkout"""
    plan: PlanType
    provider: PaymentProvider


class SubscriptionUpdate(BaseModel):
    """Validación para actualización de suscripción"""
    plan: PlanType
    status: Optional[SubscriptionStatus] = None
    payment_provider: Optional[PaymentProvider] = None
    provider_customer_id: Optional[str] = Field(None, max_length=255)
    provider_subscription_id: Optional[str] = Field(None, max_length=255)


# ============================================================================
# MODELOS DE PAGOS
# ============================================================================

class PaymentRecord(BaseModel):
    """Validación para registro de pago"""
    user_id: int = Field(..., gt=0)
    amount: Decimal = Field(..., gt=0, decimal_places=2)
    currency: str = Field(..., min_length=3, max_length=3, pattern=r'^[A-Z]{3}$')
    status: Literal["succeeded", "failed", "pending", "refunded"]
    payment_provider: PaymentProvider
    provider_payment_id: Optional[str] = Field(None, max_length=255)
    provider_customer_id: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = Field(None, max_length=500)
    metadata: Optional[str] = None


# ============================================================================
# MODELOS DE CATÁLOGO
# ============================================================================

class FilamentCreate(BaseModel):
    """Validación para crear filamento"""
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(..., min_length=1, max_length=100)
    brand: str = Field(..., min_length=1, max_length=100)
    material: str = Field(..., min_length=1, max_length=50)
    color: str = Field(..., min_length=1, max_length=50)
    price_per_kg: Decimal = Field(..., gt=0, le=1000, decimal_places=2)
    diameter_mm: float = Field(..., gt=0, le=10, description="Diámetro en mm (ej: 1.75, 2.85)")
    notes: Optional[str] = Field(None, max_length=500)

    @field_validator('diameter_mm')
    @classmethod
    def validate_diameter(cls, v: float) -> float:
        """Valida que el diámetro sea estándar"""
        standard_diameters = [1.75, 2.85, 3.0]
        if not any(abs(v - d) < 0.1 for d in standard_diameters):
            raise ValueError(f'El diámetro debe ser uno de los estándares: {standard_diameters}')
        return v


class FilamentUpdate(BaseModel):
    """Validación para actualizar filamento"""
    model_config = ConfigDict(str_strip_whitespace=True)

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    brand: Optional[str] = Field(None, min_length=1, max_length=100)
    material: Optional[str] = Field(None, min_length=1, max_length=50)
    color: Optional[str] = Field(None, min_length=1, max_length=50)
    price_per_kg: Optional[Decimal] = Field(None, gt=0, le=1000, decimal_places=2)
    diameter_mm: Optional[float] = Field(None, gt=0, le=10)
    notes: Optional[str] = Field(None, max_length=500)


class CatalogItemCreate(BaseModel):
    """Validación para crear ítem de catálogo"""
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    category: str = Field(..., min_length=1, max_length=50)
    base_price: Decimal = Field(..., gt=0, le=100000, decimal_places=2)
    image_url: Optional[str] = Field(None, max_length=500)


# ============================================================================
# MODELOS DE CLIENTES Y COTIZACIONES
# ============================================================================

class ClientCreate(BaseModel):
    """Validación para crear cliente"""
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(..., min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20, pattern=r'^[\d\s\-\+\(\)]+$')
    address: Optional[str] = Field(None, max_length=200)
    notes: Optional[str] = Field(None, max_length=500)


class QuoteCreate(BaseModel):
    """Validación para crear cotización"""
    client_id: int = Field(..., gt=0)
    items: str = Field(..., min_length=1, description="JSON con items de la cotización")
    subtotal: Decimal = Field(..., ge=0, decimal_places=2)
    tax: Decimal = Field(default=Decimal('0'), ge=0, decimal_places=2)
    total: Decimal = Field(..., gt=0, decimal_places=2)
    notes: Optional[str] = Field(None, max_length=1000)

    @field_validator('total')
    @classmethod
    def validate_total(cls, v: Decimal, info) -> Decimal:
        """Valida que el total sea correcto"""
        if 'subtotal' in info.data and 'tax' in info.data:
            expected = info.data['subtotal'] + info.data['tax']
            if abs(v - expected) > Decimal('0.01'):
                raise ValueError(f'El total debe ser subtotal + impuesto ({expected})')
        return v


# ============================================================================
# MODELOS DE RESPUESTA (para documentación API)
# ============================================================================

class SuccessResponse(BaseModel):
    """Respuesta estándar de éxito"""
    success: bool = True
    message: str
    data: Optional[dict] = None


class ErrorResponse(BaseModel):
    """Respuesta estándar de error"""
    success: bool = False
    error: str
    detail: Optional[str] = None
