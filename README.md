# BIOFLOC ERP

Sistema ERP para la gestión productiva de un cultivo de tilapia en Biofloc.

## Stack

**Backend**

- FastAPI
- Python
- PostgreSQL

**Frontend**

- React
- TypeScript
- Vite

## Estructura

- `backend/` — API FastAPI, servicios, modelos y pruebas.
- `frontend/` — interfaz React (Vite).
- `database/` — esquema SQL y migraciones.

## Configuración local

1. Copiar `backend/.env.example` a `backend/.env`.
2. Configurar PostgreSQL (`POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`).
3. Definir `JWT_SECRET_KEY` (obligatorio; no dejarlo vacío).
4. Aplicar el esquema en una base **propia**, no en la de laboratorio: `database/biofloc_erp_v1_1_schema_final.sql`.
5. Backend (desde `backend/`):

   ```
   python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
   ```

6. Frontend (desde `frontend/`):

   ```
   npm install
   npm run dev
   ```

   La interfaz queda en http://127.0.0.1:5173/ y el proxy de Vite apunta a la API en el puerto 8000.

Dependencias del backend: `backend/requirements.txt`.

## Base de datos

- `database/biofloc_erp_v1_1_schema_final.sql` es el esquema/base actual.
- Los archivos de `database/migrations/` son para bases **existentes**, según corresponda.
- No ejecutar migraciones de forma indiscriminada sobre el laboratorio.
- La aplicación en desarrollo usa una BD de laboratorio **separada**.
- Los datos del laboratorio **no** forman parte de este repositorio.

## Seguridad

- Nunca subir `.env`.
- Nunca subir credenciales, `JWT_SECRET_KEY` real ni passwords.
- Nunca ejecutar scripts de demo o test contra producción.
- `backend/scripts/demo/datos_demo.py` y `backend/scripts/aplicar_catalogo_6c.py` requieren especial cuidado: pueden escribir en la BD configurada.
- Los tests HTTP (`backend/tests/`) pueden escribir en la BD indicada en `.env`. No apuntarlos a laboratorio ni a producción.

## Estado del proyecto

El sistema cuenta actualmente con:

- autenticación JWT/RBAC
- gestión de lotes
- biometrías
- mortalidades
- alimentación
- inventario
- cosechas
- análisis productivo
- dashboard
- reportes
- catálogo productivo de Tilapia
- referencias de alimentación
- referencias de agua/Biofloc
