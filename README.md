# Zima-Externo

API REST para que los sistemas del **Hospital del Río** reflejen en el canal de WhatsApp las gestiones de citas realizadas fuera de él: agendamientos, reagendamientos y cancelaciones hechos por counters, call center u otros módulos internos.

Forma parte del ecosistema **Zima** (canal de citas por WhatsApp del Hospital del Río), junto a [zima-agente](https://github.com/vidd1992/zima-agente) (el bot conversacional) y [zima-crm](https://github.com/vidd1992/zima-crm) (el panel de administración).

## Qué hace

- **Registrar** una cita creada en el sistema del hospital → queda visible en el CRM y, opcionalmente, entra al ciclo de recordatorios de WhatsApp.
- **Reagendar** y **cancelar** citas por su identificador (`id_chatbot`), con aviso opcional al paciente.
- **Consultar** citas con filtros (cédula, teléfono, fecha, estado, origen).

Principios de diseño: escribe **únicamente** en la base del canal (nunca llama a los sistemas del hospital), referencias siempre explícitas, idempotencia en las escrituras, respuestas honestas (`ok:false` con motivo) y modo de prueba `?simular=true` en toda operación de escritura.

## Stack

Python 3.11 · FastAPI · PostgreSQL (usuario de base de datos restringido a la tabla de citas) · desplegado como contenedor en AWS Lambda detrás de API Gateway.

## Estructura

```
app/
├── main.py            # aplicación FastAPI + bitácora de acceso
├── config.py          # configuración por variables de entorno
├── seguridad.py       # autenticación por token (X-Externo-Token)
├── modelos.py         # contrato de entrada/salida (Pydantic)
├── whatsapp.py        # avisos opcionales al paciente (Meta Cloud API)
└── rutas/
    ├── consultas.py   # GET (listar / ver)
    └── escrituras.py  # POST / PUT / cancelar
migraciones/           # SQL de columnas propias (idempotente)
pruebas/               # validación automática del contrato + ejemplos .http
docs/                  # contrato de integración (la fuente de los ejemplos)
```

## Desarrollo local

```bash
cp .env.ejemplo .env        # completar DATABASE_URL y EXTERNO_TOKEN
pip install -r requirements.txt
uvicorn app.main:app --port 8090
```

Documentación interactiva en `http://localhost:8090/externo/docs`.

**Validar el contrato** (ejecuta cada ejemplo documentado contra el servicio y limpia sus datos al terminar):

```bash
python pruebas/validar_contrato.py
```

## Despliegue

Imagen de contenedor (`Dockerfile.lambda`, con AWS Lambda Web Adapter) publicada en ECR y ejecutada en un Lambda propio, independiente del bot. La documentación de integración para el equipo del hospital vive en `docs/contrato-api.md`.
