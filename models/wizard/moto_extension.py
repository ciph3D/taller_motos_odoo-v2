# models/wizard/moto_extension.py
from odoo import api, fields, models, _

class MotoExtension(models.Model):
    _inherit = 'taller.moto'
    
    def action_ingresar_reparacion(self):
        """Abrir el wizard de ingreso a reparación con la moto preseleccionada"""
        self.ensure_one()
        
        # Crear un nuevo wizard con los datos precompletados
        wizard = self.env['taller.moto.ingresar.wizard'].create({
            'partner_id': self.cliente_id.id,
            'moto_id': self.id,
            'state': 'fotos',  # Saltar directamente a la etapa de fotos
            'marca': self.marca,
            'modelo': self.modelo,
            'matricula': self.matricula,
            'chasis': self.chasis,
            'kilometraje': self.kilometraje,
            'numero_llave': self.numero_llave,
        })
        
        # Devolver acción para abrir el wizard
        return {
            'name': _('Ingresar moto a reparación'),
            'type': 'ir.actions.act_window',
            'res_model': 'taller.moto.ingresar.wizard',
            'res_id': wizard.id,
            'view_mode': 'form',
            'target': 'new',
            'context': {'form_view_initial_mode': 'edit'}
        }