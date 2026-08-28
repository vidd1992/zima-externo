# API Zima-Externo — Contrato de integración

**Hospital del Río · v1.0 · Agosto 2026**
Todos los ejemplos de este documento fueron ejecutados y verificados contra el servicio (6/6 ✓).

---

## 1. Qué es

Cuando su personal **agenda, reagenda o cancela** una cita en el sistema del hospital, el canal de WhatsApp no se entera — y el paciente puede recibir recordatorios de citas que ya no existen, o quedarse sin recordatorio de una cita nueva. Esta API lo resuelve: su sistema nos avisa con una llamada HTTP y el registro del canal queda al día al instante.

- La API escribe **únicamente en la base del canal de WhatsApp**. Jamás toca los sistemas del hospital: es un espejo, no un eco.
- Opcionalmente pueden pedir **recordatorios** para la cita registrada, o un **aviso WhatsApp** al paciente cuando la muevan o cancelen.

## 2. Acceso

| | |
|---|---|
| URL base | `https://agente.hospitaldelrio.com` |
| Autenticación | header `X-Externo-Token: <token>` en **todas** las peticiones (el token se entrega por canal seguro, separado de este documento) |
| Docs interactivas | `https://agente.hospitaldelrio.com/externo/docs` (Swagger — prueben desde el navegador) |
| Salud | `GET /externo/salud` (sin token) |

**Convenciones** (las mismas que ya usan con el chatbot): cédula **con prefijo de tipo** (`C0102030405`), fechas **ISO local de Ecuador** (`2026-09-10T11:00:00`), códigos de especialidad (`E59`), ids de aseguradora.

## 3. La llave: `id_chatbot`

Toda cita se identifica por `id_chatbot` — **el mismo campo que su tabla de citas ya tiene**:

- Citas creadas por el chatbot → ustedes ya guardan ese id (columna `idChatbot`).
- Citas que registren por esta API → se lo devolvemos en la respuesta: **guárdenlo** y con él reagendan o cancelan.

Nunca adivinamos a qué cita se refiere una petición: si el id no existe, la respuesta lo dice.

## 4. Endpoints

### 4.1 Registrar una cita agendada en su sistema

```bash
curl -X POST "https://agente.hospitaldelrio.com/externo/citas" \
  -H "X-Externo-Token: $TOKEN" -H "Content-Type: application/json" -d '{
  "cita_hospital": 90501,
  "paciente": "MARIA FERNANDA EJEMPLO RODAS",
  "cedula": "C0102030405",
  "celular": "0991112233",
  "email": "paciente@correo.com",
  "especialidad": "E59",
  "nombre_especialidad": "Medicina Interna",
  "id_medico": 251,
  "nombre_medico": "MARTINEZ TORRES PAUL SANTIAGO",
  "fecha_aten": "2026-09-10T11:00:00",
  "empresa": 27,
  "usuario": "Counter 2301",
  "recordatorios": false
}'
```

```json
{"ok": true, "id_chatbot": 5037, "cita_hospital": 90501,
 "nota": "guarden id_chatbot en su columna idChatbot para futuras gestiones"}
```

- `cita_hospital` = **su** número de cita (obligatorio). `usuario` = quién lo hizo en su sistema (obligatorio — trazabilidad).
- **Idempotente**: reenviar el mismo `cita_hospital` no duplica — devuelve el mismo `id_chatbot`.
- Si ya existe una cita activa de esa cédula + especialidad + fecha: `{"ok": false, "motivo": "..."}`.

### 4.2 Reagendar

```bash
curl -X PUT "https://agente.hospitaldelrio.com/externo/citas" \
  -H "X-Externo-Token: $TOKEN" -H "Content-Type: application/json" -d '{
  "id_chatbot": 5037,
  "fecha_nueva": "2026-09-12T15:30:00",
  "usuario": "Counter 2301",
  "notificar": false
}'
```

```json
{"ok": true, "id_chatbot": 5037, "fecha": "2026-09-12", "hora": "15:30"}
```

Con `"notificar": true` el paciente recibe por WhatsApp la confirmación con la fecha nueva (plantilla aprobada — llega siempre).

### 4.3 Cancelar

```bash
curl -X POST "https://agente.hospitaldelrio.com/externo/citas/cancelar" \
  -H "X-Externo-Token: $TOKEN" -H "Content-Type: application/json" -d '{
  "id_chatbot": 5037,
  "motivo": "El médico no atenderá ese día",
  "usuario": "Counter 2301",
  "notificar": false
}'
```

```json
{"ok": true, "id_chatbot": 5037, "estado": "cancelada"}
```

Idempotente: cancelar dos veces no es error. Con `"notificar": true` se intenta avisar al paciente (los avisos de cancelación solo llegan garantizado si el paciente escribió al canal en las últimas 24 h — regla de Meta).

### 4.4 Consultar / listar

```bash
curl "https://agente.hospitaldelrio.com/externo/citas?cedula=C0102030405" -H "X-Externo-Token: $TOKEN"
curl "https://agente.hospitaldelrio.com/externo/citas/5037"              -H "X-Externo-Token: $TOKEN"
```

Filtros combinables: `cedula`, `celular`, `fecha` (YYYY-MM-DD), `estado` (confirmada/pendiente/cancelada/rechazada), `origen` (bot/hospital), `limite` (máx 200).

## 5. Modo de prueba: `?simular=true`

En **cualquier escritura**, agreguen `?simular=true`: validamos todo y respondemos qué haríamos, **sin guardar nada**.

```bash
curl -X POST "https://agente.hospitaldelrio.com/externo/citas?simular=true" ...
```

```json
{"ok": true, "simulado": true, "haria": "insertar cita de ... el 2026-09-15 14:10 (origen=hospital, usuario=Dev Hospital)"}
```

Usen esto durante toda su integración — es imposible dañar datos con `simular=true`.

## 6. Errores — siempre con motivo

| Respuesta | Significado |
|---|---|
| `401` | Falta o es inválido el `X-Externo-Token` |
| `422` + detalle | Petición mal formada; el detalle dice **el campo exacto y el porqué** (ej.: `cédula '0102030405' inválida: debe llevar prefijo de tipo, ej. C0102030405`) |
| `200` con `{"ok": false, "motivo": "..."}` | Petición válida pero no procede (cita inexistente, duplicada, ya cancelada…) |

Nunca respondemos `ok: true` sin haber hecho el trabajo.

## 7. Checklist de integración

1. Probar los ejemplos de este documento con `?simular=true` y su token.
2. Registrar una cita real de prueba, verificar el `id_chatbot` devuelto, y **cancelarla** (no dejar pruebas vivas).
3. Guardar el `id_chatbot` devuelto en su columna `idChatbot` al registrar.
4. Definir con su área de atención al paciente la política de `recordatorios` y `notificar`.
5. Coordinar la salida en vivo con el equipo Zima.

---

*Equipo Zima · David Mejía — los ejemplos de este contrato se regeneran y se ejecutan automáticamente contra el servicio (`pruebas/validar_contrato.py`); si algún ejemplo no funcionara tal cual está escrito, es un bug nuestro.*
