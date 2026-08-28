-- Zima-Externo · migración 001 — inofensiva (IF NOT EXISTS) y compartida con el bot.
-- `origen`: quién creó la cita (bot | hospital | crm). `cita_hospital`: el número de cita
-- en el sistema del hospital (su id), para referencia cruzada y trazabilidad.
ALTER TABLE citas_solicitadas ADD COLUMN IF NOT EXISTS origen TEXT DEFAULT 'bot';
ALTER TABLE citas_solicitadas ADD COLUMN IF NOT EXISTS cita_hospital INTEGER;
ALTER TABLE citas_solicitadas ADD COLUMN IF NOT EXISTS nota TEXT DEFAULT '';
ALTER TABLE citas_solicitadas ADD COLUMN IF NOT EXISTS creada TIMESTAMPTZ DEFAULT now();
-- recordatorios: las citas registradas por el hospital solo reciben recordatorios de
-- WhatsApp si lo piden explícitamente (flag por cita). El job del bot lo respetará (F2).
ALTER TABLE citas_solicitadas ADD COLUMN IF NOT EXISTS recordatorios_habilitados BOOLEAN DEFAULT TRUE;
CREATE INDEX IF NOT EXISTS idx_citas_cita_hospital ON citas_solicitadas (cita_hospital);
