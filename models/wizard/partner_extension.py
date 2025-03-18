# models/wizard/partner_extension.py
from odoo import api, fields, models

class PartnerExtension(models.Model):
    _inherit = 'res.partner'
    
    # No definir el campo como almacenado en la base de datos
    taller_wizard_active = fields.Boolean(string='Wizard Activo', default=False, store=False)
    
    @api.model
    def create(self, vals):
        """Sobreescribir create para redirigir al wizard después de crear un cliente"""
        # Crear el socio normalmente
        partner = super(PartnerExtension, self).create(vals)
        
        # Verificar si viene del wizard
        wizard_active = vals.get('taller_wizard_active', False)
        context = self.env.context
        
        if wizard_active and not context.get('no_wizard_redirect', False):
            # Crear y abrir un nuevo wizard con el cliente preseleccionado
            wizard = self.env['taller.moto.ingresar.wizard'].create({
                'partner_id': partner.id,
                'state': 'moto',  # Avanzar directamente a la siguiente etapa
            })
            
            # Devolver acción para abrir el wizard
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'taller.moto.ingresar.wizard',
                'res_id': wizard.id,
                'view_mode': 'form',
                'target': 'new',
                'context': {'form_view_initial_mode': 'edit'}
            }
        
        return partner