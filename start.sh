#!/bin/bash
# Script de inicio para Calc3D en producción

# Activar entorno virtual
source venv/bin/activate

# Iniciar aplicación con uvicorn
# --host 0.0.0.0: Escuchar en todas las interfaces
# --port 8000: Puerto de la aplicación
# --workers 2: Número de workers (ajustar según CPU)
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 2
