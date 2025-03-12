from odoo import models, fields, api, _

class Partner(models.Model):
    _inherit = 'res.partner'
    
    # Campos relacionados con motos
    moto_ids = fields.One2many('taller.moto', 'cliente_id', string='Motos')
    moto_count = fields.Integer(string='Número de motos', compute='_compute_moto_count')
    
    # Nuevo campo para gestión de reuniones
    meeting_count = fields.Integer(string="Reuniones", compute="_compute_meeting_count")
    
    @api.depends('moto_ids')
    def _compute_moto_count(self):
        for partner in self:
            partner.moto_count = len(partner.moto_ids)
    
    @api.depends()
    def _compute_meeting_count(self):
        for partner in self:
            partner.meeting_count = self.env['calendar.event'].search_count([
                ('partner_ids', 'in', partner.id)
            ])
    
    def action_view_motos(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Motos del cliente'),
            'res_model': 'taller.moto',
            'view_mode': 'list,form',
            'domain': [('cliente_id', '=', self.id)],
            'context': {'default_cliente_id': self.id}
        }
    
    def schedule_meeting(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Programar Reunión'),
            'res_model': 'calendar.event',
            'view_mode': 'form',
            'context': {
                'default_partner_ids': [(6, 0, [self.id])],
            },
        }