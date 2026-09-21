# Guía de validación — Ambiente Sandbox Zima

**Hospital del Río · Equipo Zima · Septiembre 2026**

Ambiente de pruebas para validar la integración con el canal de WhatsApp **sin ningún
riesgo**: mismo servicio y mismo contrato que producción, con base de datos aislada.
Pueden crear, mover y cancelar citas a gusto — nada de lo que hagan aquí toca datos reales
ni le llega a ningún paciente.

---

## 1. Accesos

| | Sandbox | Producción (referencia) |
|---|---|---|
| URL base | `https://sandbox.hospitaldelrio.com` | `https://agente.hospitaldelrio.com` |
| Token | **token de sandbox** (se entrega por canal seguro, separado de este documento) | token de producción (distinto) |
| Docs interactivas (Swagger) | `https://sandbox.hospitaldelrio.com/externo/docs` | — |
| Salud (sin token) | `GET /externo/salud` | — |

- El token va en el header `X-Externo-Token` en **todas** las peticiones.
- El token de sandbox **no funciona** en producción, ni el de producción en sandbox.
- Convenciones (las mismas del contrato): cédula con prefijo (`C0102030405`), fechas ISO
  local de Ecuador (`2026-10-05T09:00:00`), códigos de especialidad (`E59`).

## 2. Qué es distinto en sandbox

- Los `id_chatbot` empiezan en **90000** — un id de sandbox jamás coincide con uno real.
- `notificar: true` responde `"notificacion": "simulada"` — **es imposible que un paciente
  reciba un WhatsApp desde el sandbox**, aunque manden datos de un celular real.
- Los datos son de juguete; el equipo Zima puede limpiarlos periódicamente.
- Todo lo demás (rutas, campos, validaciones, respuestas, errores) es **idéntico** a producción.

## 3. Datos precargados

| id_chatbot | cita_hospital | paciente | estado |
|---|---|---|---|
| 90001 | 80001 | PACIENTE EJEMPLO UNO | confirmada |
| 90002 | 80002 | PACIENTE EJEMPLO DOS | confirmada |

## 4. Checklist de validación

Ejecuten estos pasos en orden. Cada uno indica la respuesta esperada.

### 4.1 Conectividad y autenticación

```bash
curl https://sandbox.hospitaldelrio.com/externo/salud
# esperado: {"ok": true, "servicio": "zima-externo"}

curl https://sandbox.hospitaldelrio.com/externo/citas
# esperado: 401 (falta el token)

curl https://sandbox.hospitaldelrio.com/externo/citas -H "X-Externo-Token: $TOKEN"
# esperado: 200 con las citas de ejemplo
```

### 4.2 Modo simulación (recomendado para las primeras pruebas)

```bash
curl -X POST "https://sandbox.hospitaldelrio.com/externo/citas?simular=true" \
  -H "X-Externo-Token: $TOKEN" -H "Content-Type: application/json" -d '{
  "cita_hospital": 80100,
  "paciente": "VALIDACION DEV HOSPITAL",
  "cedula": "C0102030405",
  "celular": "0991112233",
  "especialidad": "E59",
  "nombre_especialidad": "Medicina Interna",
  "id_medico": 251,
  "nombre_medico": "MARTINEZ TORRES PAUL SANTIAGO",
  "fecha_aten": "2026-10-15T10:00:00",
  "empresa": 27,
  "usuario": "Dev Hospital",
  "recordatorios": false
}'
# esperado: {"ok": true, "simulado": true, "haria": "insertar cita de ..."}
# y NADA queda guardado (verifíquenlo listando por cédula: no aparece)
```

### 4.3 Ciclo completo de una cita

```bash
# a) Registrar (mismo payload de arriba, SIN ?simular=true)
# esperado: {"ok": true, "id_chatbot": 90xxx, "cita_hospital": 80100, ...}
# GUARDEN el id_chatbot devuelto: es la llave de todo lo demás.

# b) Idempotencia: repitan el MISMO POST
# esperado: mismo id_chatbot, sin duplicar

# c) Reagendar
curl -X PUT "https://sandbox.hospitaldelrio.com/externo/citas" \
  -H "X-Externo-Token: $TOKEN" -H "Content-Type: application/json" -d '{
  "id_chatbot": 90xxx,
  "fecha_nueva": "2026-10-16T15:30:00",
  "usuario": "Dev Hospital",
  "notificar": true
}'
# esperado: {"ok": true, ..., "notificacion": "simulada (...)"}

# d) Consultar por id
curl "https://sandbox.hospitaldelrio.com/externo/citas/90xxx" -H "X-Externo-Token: $TOKEN"
# esperado: la cita con la fecha NUEVA y la traza en "nota"

# e) Cancelar
curl -X POST "https://sandbox.hospitaldelrio.com/externo/citas/cancelar" \
  -H "X-Externo-Token: $TOKEN" -H "Content-Type: application/json" -d '{
  "id_chatbot": 90xxx,
  "motivo": "prueba de integración",
  "usuario": "Dev Hospital",
  "notificar": false
}'
# esperado: {"ok": true, "estado": "cancelada"}; cancelar de nuevo NO es error
```

### 4.4 Manejo de errores

```bash
# Cédula sin prefijo
# esperado: 422 con el detalle exacto ("debe llevar prefijo de tipo, ej. C0102030405")

# id_chatbot inexistente (ej. 99999) al reagendar/cancelar
# esperado: 200 {"ok": false, "motivo": "..."} — nunca adivinamos la cita
```

### 4.5 Filtros de consulta

```bash
curl "https://sandbox.hospitaldelrio.com/externo/citas?cedula=C0102030405" -H "X-Externo-Token: $TOKEN"
curl "https://sandbox.hospitaldelrio.com/externo/citas?estado=cancelada"   -H "X-Externo-Token: $TOKEN"
curl "https://sandbox.hospitaldelrio.com/externo/citas?fecha=2026-10-05"   -H "X-Externo-Token: $TOKEN"
# combinables; también celular, origen (bot/hospital) y limite (máx 200)
```

## 5. Criterios de salida (qué debe cumplir su integración)

1. ✅ Guardan el `id_chatbot` devuelto al registrar, en su columna `idChatbot`.
2. ✅ Reagendan y cancelan usando ese `id_chatbot` (nunca otro identificador).
3. ✅ Envían siempre `usuario` (quién hizo la gestión — trazabilidad).
4. ✅ Manejan `{"ok": false, "motivo": ...}` sin tratarlo como éxito.
5. ✅ Definieron su política de `recordatorios` y `notificar` con atención al paciente.

Cumplido esto, se coordina la salida a producción con el equipo Zima:
**solo cambia la URL base y el token** — ni un campo más.

## 6. Prueba conversacional por WhatsApp (opcional)

Además del API, el **bot conversacional** tiene su propio modo sandbox: podemos registrar
números de teléfono de prueba para que, escribiendo al número normal de WhatsApp del
hospital, toda la conversación ocurra contra el ambiente de pruebas (se consultan agendas
reales en solo-lectura, pero **ninguna cita se crea de verdad**). Si quieren probarlo,
envíen al equipo Zima los números de los evaluadores.

> **Pendiente de su lado:** cuando nos entreguen la URL del ambiente de pruebas de su API,
> conectamos el bot sandbox contra él y las pruebas conversacionales podrán agendar
> de punta a punta en su sistema de pruebas.

## 7. Soporte

Cualquier respuesta inesperada durante la validación: envíen al equipo Zima el
**request completo** (sin el token) y la **respuesta** — toda petición queda registrada
de nuestro lado con hora e IP, así que la rastreamos al instante.

---

*Equipo Zima · David Mejía — los ejemplos de esta guía provienen del contrato
(`contrato-api.md`), cuya batería automática se ejecuta contra el propio servicio.*
