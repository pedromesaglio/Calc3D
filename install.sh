#!/bin/bash

# ============================================
# Script de Instalación Rápida - Calc3D
# ============================================

set -e  # Salir si hay errores

echo "🚀 Instalando Calc3D..."
echo ""

# Colores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Verificar Python
echo "📦 Verificando Python..."
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 no está instalado${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
echo -e "${GREEN}✅ Python $PYTHON_VERSION encontrado${NC}"

# Crear entorno virtual
echo ""
echo "🐍 Creando entorno virtual..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo -e "${GREEN}✅ Entorno virtual creado${NC}"
else
    echo -e "${YELLOW}⚠️  Entorno virtual ya existe${NC}"
fi

# Activar entorno virtual
echo ""
echo "⚡ Activando entorno virtual..."
source venv/bin/activate

# Actualizar pip
echo ""
echo "📦 Actualizando pip..."
pip install --upgrade pip > /dev/null 2>&1
echo -e "${GREEN}✅ pip actualizado${NC}"

# Instalar dependencias
echo ""
echo "📦 Instalando dependencias..."
pip install -r requirements.txt
echo -e "${GREEN}✅ Dependencias instaladas${NC}"

# Crear archivo .env si no existe
echo ""
if [ ! -f ".env" ]; then
    echo "⚙️  Creando archivo .env..."
    cp .env.example .env
    echo -e "${GREEN}✅ Archivo .env creado${NC}"
    echo -e "${YELLOW}⚠️  Por favor edita .env y configura tus claves de API${NC}"
else
    echo -e "${YELLOW}⚠️  .env ya existe, no se sobrescribió${NC}"
fi

# Inicializar base de datos
echo ""
echo "🗄️  Inicializando base de datos..."
python3 -c "from app.db import init_db; init_db()"
echo -e "${GREEN}✅ Base de datos inicializada${NC}"

# Crear directorio de logs si no existe
echo ""
echo "📝 Creando directorio de logs..."
mkdir -p logs
echo -e "${GREEN}✅ Directorio de logs creado${NC}"

echo ""
echo "============================================"
echo -e "${GREEN}✅ Instalación completada exitosamente!${NC}"
echo "============================================"
echo ""
echo "Próximos pasos:"
echo ""
echo "1. Edita el archivo .env y configura tus claves:"
echo "   nano .env"
echo ""
echo "2. Para desarrollo, configura claves de TEST de Stripe:"
echo "   - STRIPE_SECRET_KEY=sk_test_..."
echo "   - STRIPE_WEBHOOK_SECRET=whsec_..."
echo ""
echo "3. Inicia el servidor de desarrollo:"
echo "   source venv/bin/activate"
echo "   uvicorn main:app --reload"
echo ""
echo "4. Abre http://localhost:8000 en tu navegador"
echo ""
echo "📖 Documentación:"
echo "   - README_SUBSCRIPTIONS.md - Sistema de suscripciones"
echo "   - DEPLOYMENT.md - Guía de despliegue a producción"
echo ""
echo "🧪 Para ejecutar tests:"
echo "   pytest"
echo ""
echo "¡Disfruta usando Calc3D! 🎉"
echo ""
