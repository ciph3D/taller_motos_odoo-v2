from odoo import models, fields, api, _

class Repair(models.Model):
    _inherit = 'project.project'
    
    # Campos básicos existentes
    moto_id = fields.Many2one('taller.moto', index=True)
    kilometraje_entrada = fields.Integer()
    fecha_entrada = fields.Date(default=fields.Date.today)
    fecha_salida = fields.Date()
    sintomas = fields.Text()
    diagnostico = fields.Text()
    trabajo_realizado = fields.Text()
    
    # Campos para ventas/facturación
    sale_order_id = fields.Many2one('sale.order', copy=False)
    
    # Campos para la firma
    fecha_prevista_entrega = fields.Date(string="Fecha prevista de entrega")
    cliente_firma = fields.Binary(string="Firma del cliente", attachment=True)
    cliente_acepta_condiciones = fields.Boolean(
        string="Acepta condiciones", 
        default=False,
        help="El cliente acepta las condiciones generales de la Orden de Trabajo"
    )
    solicita_presupuesto = fields.Boolean(string="Solicita presupuesto", default=False)
    recoge_piezas = fields.Boolean(string="Recoge piezas sustituidas", default=False)
    avisar_telefono = fields.Boolean(string="Avisar por teléfono", default=False)
    
    # Campo calculado para mostrar referencia con matrícula
    display_name = fields.Char(compute='_compute_display_name', store=True)
    
    @api.depends('name', 'moto_id')
    def _compute_display_name(self):
        for repair in self:
            if repair.moto_id:
                repair.display_name = f"{repair.name} - {repair.moto_id.display_name}"
            else:
                repair.display_name = repair.name
    
    @api.onchange('moto_id')
    def _onchange_moto_id(self):
        if self.moto_id:
            self.partner_id = self.moto_id.cliente_id
            self.kilometraje_entrada = self.moto_id.kilometraje
    
    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        # Vaciar moto_id si cambió el cliente y la moto no le pertenece
        if self.partner_id and self.moto_id and self.moto_id.cliente_id != self.partner_id:
            self.moto_id = False
    
    def action_create_sale_order(self):
        self.ensure_one()
        return {
            'name': _('Crear Presupuesto'),
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'form',
            'context': {
                'default_partner_id': self.partner_id.id,
                'default_origin': self.name,
            }
        }
    
    def action_view_sale_order(self):
        self.ensure_one()
        return {
            'name': _('Presupuesto/Orden'),
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'form',
            'res_id': self.sale_order_id.id,
        }
    
    def action_update_moto_kilometraje(self):
        """Actualiza el kilometraje de la moto al completar la reparación"""
        for repair in self:
            if repair.moto_id and repair.kilometraje_entrada > 0:
                repair.moto_id.write({'kilometraje': repair.kilometraje_entrada})

class RepairTask(models.Model):
    _inherit = 'project.task'
    
    moto_id = fields.Many2one(related='project_id.moto_id', store=True, readonly=True)
    labor_time = fields.Float()
    parts_used = fields.Text()