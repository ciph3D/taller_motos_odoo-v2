from . import partner
from . import moto
from . import repair

def uninstall_hook(cr, registry):
    """
    Preserve moto records by changing their model if the module is uninstalled
    """
    from odoo import api, SUPERUSER_ID

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
                    state VARCHAR
                )
            """)
            
            # Backup existing moto data
            for moto in motos:
                cr.execute("""
                    INSERT INTO preserved_motos 
                    (id, marca, modelo, matricula, chasis, cliente_id, 
                     fecha_compra, kilometraje, notas, state)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    moto.id, moto.marca, moto.modelo, moto.matricula, 
                    moto.chasis, moto.cliente_id.id, moto.fecha_compra, 
                    moto.kilometraje, moto.notas, moto.state
                ))
            
            cr.commit()
            print("Moto records preserved successfully!")
    except Exception as e:
        print(f"Error preserving moto records: {e}")
    
    return True