from loguru import logger
from iibb.db import get_session
from iibb.seed.jurisdicciones import seed_jurisdicciones
from iibb.seed.american_implant import seed_tenant, seed_american_implant

PASSWORD_DEFAULT = "iibb2026"


def _seed_usuario_admin(session, tenant_id: int):
    from iibb.models.usuario import Usuario
    from iibb.service.auth import crear_usuario

    email = "dcasimiro@cgestudiocontable.com"
    existente = session.query(Usuario).filter_by(email=email).first()
    if not existente:
        crear_usuario(
            session,
            email=email,
            password=PASSWORD_DEFAULT,
            nombre="Diego Casimiro",
            tenant_id=tenant_id,
        )
        # Marcar como admin
        u = session.query(Usuario).filter_by(email=email).first()
        u.es_admin = True
        logger.info(f"Usuario admin creado: {email} / contraseña: {PASSWORD_DEFAULT}")
    else:
        # Asegurar que siempre sea admin aunque ya existiera
        existente.es_admin = True
        logger.info(f"Usuario {email} ya existe — marcado como admin.")


def main():
    logger.info("Iniciando seed de datos...")
    session = get_session()
    try:
        seed_jurisdicciones(session)
        logger.info("24 jurisdicciones cargadas.")

        tenant = seed_tenant(session)
        logger.info(f"Tenant '{tenant.nombre}' listo.")

        contrib = seed_american_implant(session, tenant.id)
        logger.info(f"Contribuyente '{contrib.razon_social}' cargado.")

        _seed_usuario_admin(session, tenant.id)

        session.commit()
        logger.success("Seed completado exitosamente.")
    except Exception as e:
        session.rollback()
        logger.error(f"Error en seed: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
