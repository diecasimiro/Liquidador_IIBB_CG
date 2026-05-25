# IIBB Convenio Multilateral — Estudio CG

App para liquidar IIBB bajo Convenio Multilateral (CM03 mensual).

## Requisitos
- Windows 10/11
- Python 3.10 o superior (con "Add Python to PATH" marcado durante la instalación)

## Instalación (primera vez)

1. Doble clic en `instalar.bat`
2. Esperar que termine (2-5 minutos según conexión a internet)
3. Listo

## Uso diario

1. Doble clic en `iibb.bat`
2. El navegador se abre automáticamente en `http://localhost:8501`
3. Seleccioná el contribuyente → Procesar período → subir archivos → Calcular

## Archivos que la app acepta

| Archivo | Formato | Origen |
|---|---|---|
| Mis Comprobantes Emitidos | `.xlsx` | ARCA / AFIP |
| SIRCREB CABA | `.csv` (con `sep=,`) | Rentas Ciudad / AGIP |
| SIRCREB Buenos Aires | `.xls` o `.xlsx` | ARBA |
| Retenciones / Percepciones | `.xlsx`, `.xls`, `.csv` | Cualquier formato |

## Correr los tests

Abrir PowerShell en la carpeta del proyecto:

```powershell
.venv\Scripts\Activate.ps1
pytest tests/ -v
```

El test crítico `test_american_implant_abril_2026` debe dar PASSED siempre.

## Estructura del proyecto

```
iibb/calculo/cm03.py     Motor de cálculo puro (sin BD)
iibb/importers/          Lectores de archivos ARCA/AGIP/ARBA
iibb/service/            Lógica de negocio + persistencia
iibb/ui/                 Pantallas Streamlit
tests/                   Tests automáticos
alembic/                 Migraciones de base de datos
```

## Base de datos

La base de datos se guarda en `C:\Users\TU_USUARIO\.iibb\iibb.db`.
**No borres esta carpeta** — ahí están todos tus datos.

Para hacer un backup manual: copiá el archivo `iibb.db` a otro lugar.

## Soporte

Contacto: dcasimiro@cgestudiocontable.com
