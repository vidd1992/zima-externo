# Ambiente Sandbox — API Zima-Externo

Ambiente de pruebas para que el equipo del hospital integre **sin ningún riesgo**: es el
mismo servicio y el mismo contrato que producción, pero completamente aislado.

| | Sandbox | Producción |
|---|---|---|
| URL base | `https://sandbox.hospitaldelrio.com` | `https://agente.hospitaldelrio.com` |
| Token | propio de sandbox (se entrega por canal seguro) | propio de producción |
| Base de datos | esquema `sandbox` aislado (ids desde 90000) | tabla real del canal |
| Avisos WhatsApp | **nunca salen** (siempre `simulada`) | según configuración |
| Docs interactivas | `<URL base>/externo/docs` | `<URL base>/externo/docs` |

## Reglas del sandbox

- **Mismo contrato**: todos los ejemplos de `contrato-api.md` funcionan igual cambiando
  la URL base y el token.
- Los `id_chatbot` del sandbox empiezan en **90000** — jamás coinciden con ids reales.
- El usuario de base de datos del sandbox no tiene acceso a ninguna tabla real
  (verificado: `InsufficientPrivilege` en cualquier intento).
- `notificar: true` responde `"notificacion": "simulada"` — es imposible que un paciente
  reciba un mensaje desde el sandbox.
- Los datos del sandbox son de juguete: se pueden crear, mover y cancelar citas a gusto,
  y el equipo Zima puede limpiarlos periódicamente.
- El token de sandbox **no funciona** en producción ni viceversa (verificado: 401 cruzado).

## Datos de ejemplo precargados

| id_chatbot | cita_hospital | paciente | estado |
|---|---|---|---|
| 90001 | 80001 | PACIENTE EJEMPLO UNO | confirmada |
| 90002 | 80002 | PACIENTE EJEMPLO DOS | confirmada |
| 90000 | 90501 | (rastro de la validación del contrato) | cancelada |

## Flujo sugerido de integración

1. Probar todo contra el **sandbox** (con y sin `?simular=true`).
2. Cuando el flujo esté validado de su lado, coordinar con el equipo Zima.
3. Cambiar URL base + token a los de producción. Nada más cambia.

---

*Infraestructura: Lambda `zima-externo-sandbox` (misma imagen que producción) ·
API Gateway `y08c5hm352` con dominio `sandbox.hospitaldelrio.com` (certificado ACM propio) ·
usuario de BD `zima_externo_sandbox` restringido al esquema `sandbox`.*
