from iibb.models.catalogos import Jurisdiccion

JURISDICCIONES_DATA = [
    ("901", "Ciudad Autónoma de Buenos Aires", "CABA"),
    ("902", "Buenos Aires", "Buenos Aires"),
    ("903", "Catamarca", "Catamarca"),
    ("904", "Córdoba", "Córdoba"),
    ("905", "Corrientes", "Corrientes"),
    ("906", "Chaco", "Chaco"),
    ("907", "Chubut", "Chubut"),
    ("908", "Entre Ríos", "Entre Ríos"),
    ("909", "Formosa", "Formosa"),
    ("910", "Jujuy", "Jujuy"),
    ("911", "La Pampa", "La Pampa"),
    ("912", "La Rioja", "La Rioja"),
    ("913", "Mendoza", "Mendoza"),
    ("914", "Misiones", "Misiones"),
    ("915", "Neuquén", "Neuquén"),
    ("916", "Río Negro", "Río Negro"),
    ("917", "Salta", "Salta"),
    ("918", "San Juan", "San Juan"),
    ("919", "San Luis", "San Luis"),
    ("920", "Santa Cruz", "Santa Cruz"),
    ("921", "Santa Fe", "Santa Fe"),
    ("922", "Santiago del Estero", "Sgo. del Estero"),
    ("923", "Tucumán", "Tucumán"),
    ("924", "Tierra del Fuego", "Tierra del Fuego"),
]


def seed_jurisdicciones(session):
    existing = {j.codigo for j in session.query(Jurisdiccion).all()}
    for codigo, nombre, nombre_corto in JURISDICCIONES_DATA:
        if codigo not in existing:
            session.add(Jurisdiccion(codigo=codigo, nombre=nombre, nombre_corto=nombre_corto))
    session.flush()
