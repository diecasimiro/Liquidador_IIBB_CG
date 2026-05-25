# IIBB Convenio Multilateral — Contexto para Claude Code

## Qué es este proyecto
App Python/Streamlit para liquidar IIBB bajo Convenio Multilateral en Argentina.
Desarrollada para el Estudio CG (Dieguito Casimiro / dcasimiro@cgestudiocontable.com).
Aproximadamente 30 contribuyentes inscriptos en CM.

## Stack
- **UI**: Streamlit (NO Flet — tuvo problemas de compatibilidad)
- **ORM**: SQLAlchemy 2.0
- **Migraciones**: Alembic (siempre usar Alembic, nunca create_all solo)
- **DB**: SQLite en `~/.iibb/iibb.db`
- **Tests**: pytest

## Regla crítica de cálculo
TODA la aritmética monetaria usa `decimal.Decimal` con `ROUND_HALF_UP`.
Nunca usar `float` para montos. Ver `iibb/calculo/cm03.py::q2()`.

## Test de validación obligatorio
`tests/test_calculo_cm03_american_implant.py::test_american_implant_abril_2026`
Este test verifica que el motor da exactamente $2.090.054,20 con los datos de
American Implant S.A. para Abril 2026. Si falla, hay un bug en el motor.
Correr SIEMPRE después de cambiar `iibb/calculo/cm03.py`.

## Estructura clave
```
iibb/calculo/cm03.py     → motor puro (sin DB), testeable aislado
iibb/importers/          → lectores de archivos ARCA/AGIP/ARBA
iibb/service/            → orquestación DB + motor
iibb/ui/                 → pantallas Streamlit
tests/conftest.py        → genera fixtures sintéticos automáticamente
```

## Comandos útiles
```powershell
# Instalar (primera vez)
.\.venv\Scripts\activate.ps1
pip install -e ".[dev]"
alembic upgrade head
python -m iibb.seed

# Lanzar app
streamlit run iibb/main.py

# Tests (siempre antes de commitear)
pytest tests/ -v

# Nueva migración de BD
alembic revision --autogenerate -m "descripcion"
alembic upgrade head
```

## Inmutabilidad de períodos
Un período presentado nunca se modifica. Las rectificativas son nuevos registros
con secuencia=1, 2, etc. Ver `iibb/service/liquidacion.py`.

## Roadmap
- Fase 1 (actual): MVP con CM03 Régimen General Art. 2
- Fase 2: CRUD de contribuyentes en UI, importación masiva desde Excel
- Fase 3: Arts. 6-13 CM (regímenes especiales), CM05 anual
- Fase 4: Multi-tenant SaaS

## Usuario
No tiene experiencia de programación. Siempre dar instrucciones paso a paso
con comandos exactos para Windows PowerShell/CMD.
