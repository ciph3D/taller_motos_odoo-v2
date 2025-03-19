# models/__init__.py
from . import partner
from . import moto
from . import repair
from . import wizard

# Añade esta línea para importar el nuevo wizard
from .wizard import moto_export_import_wizard

def uninstall_hook(cr, registry):
    """
    Preserve moto records by changing their model if the module is uninstalled
    """
    from odoo import api, SUPERUSER_ID
    import logging

    _logger = logging.getLogger(__name__)

    # Create a new environment with sudo privileges
    env = api.Environment(cr, SUPERUSER_ID, {})
    
    try:
        # Find existing moto records
        moto_model = env['taller.moto']
        motos = moto_model.search([])
        
        if motos:
            # Create a base model to preserve the records
            cr.execute("""
                CREATE TABLE IF NOT EXISTS preserved_motos (
                    id INTEGER PRIMARY KEY,
                    marca VARCHAR,
                    modelo VARCHAR,
                    matricula VARCHAR,
                    chasis VARCHAR,
                    cliente_id INTEGER,
                    fecha_compra DATE,
                    kilometraje FLOAT,
                    notas TEXT,
                    state VARCHAR,
                    numero_llave VARCHAR
                )
            """)
            
            # Backup existing moto data
            for moto in motos:
                cr.execute("""
                    INSERT INTO preserved_motos 
                    (id, marca, modelo, matricula, chasis, cliente_id, 
                     fecha_compra, kilometraje, notas, state, numero_llave)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                    marca = EXCLUDED.marca,
                    modelo = EXCLUDED.modelo,
                    matricula = EXCLUDED.matricula
                """, (
                    moto.id, moto.marca, moto.modelo, moto.matricula, 
                    moto.chasis, moto.cliente_id.id, moto.fecha_compra, 
                    moto.kilometraje, moto.notas, moto.state, moto.numero_llave
                ))
            
            cr.commit()
            _logger.info("Moto records preserved successfully!")
    except Exception as e:
        _logger.error(f"Error preserving moto records: {e}")
    
    return True