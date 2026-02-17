from odoo import models, fields, api, _
from odoo.fields import Command


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
    
    # Líneas de trabajo / materiales
    repair_line_ids = fields.One2many(
        'project.project.line',
        'project_id',
        string='Líneas de trabajo',
    )
    amount_untaxed = fields.Float(
        string='Base imponible',
        compute='_compute_amounts',
        store=True,
    )
    amount_tax = fields.Float(
        string='Impuestos',
        compute='_compute_amounts',
        store=True,
    )
    amount_total = fields.Float(
        string='Total',
        compute='_compute_amounts',
        store=True,
    )
    
    # Campos para ventas/facturación
    sale_order_id = fields.Many2one('sale.order', copy=False)
    
    # Fotos de documentación (ingreso desde wizard)
    foto_ids = fields.Many2many(
        'ir.attachment',
        relation='taller_motos_project_foto_rel',
        column1='project_id',
        column2='attachment_id',
        string='Fotos de ingreso',
    )
    
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

    @api.depends(
        'repair_line_ids',
        'repair_line_ids.price_subtotal',
        'repair_line_ids.tax_ids',
        'repair_line_ids.quantity',
        'repair_line_ids.price_unit',
        'repair_line_ids.discount',
        'company_id',
        'currency_id',
        'partner_id',
    )
    def _compute_amounts(self):
        for repair in self:
            if not repair.repair_line_ids:
                repair.amount_untaxed = 0.0
                repair.amount_tax = 0.0
                repair.amount_total = 0.0
                continue
            company = repair.company_id or self.env.company
            if not company:
                repair.amount_untaxed = 0.0
                repair.amount_tax = 0.0
                repair.amount_total = 0.0
                continue
            currency = repair.currency_id or company.currency_id
            if not currency:
                repair.amount_untaxed = sum(repair.repair_line_ids.mapped('price_subtotal'))
                repair.amount_tax = 0.0
                repair.amount_total = repair.amount_untaxed
                continue
            amount_untaxed = sum(repair.repair_line_ids.mapped('price_subtotal'))
            amount_tax = 0.0
            for line in repair.repair_line_ids:
                if line.tax_ids:
                    price_after_discount = line.price_unit * (1.0 - (line.discount or 0.0) / 100.0)
                    result = line.tax_ids.compute_all(
                        price_after_discount,
                        currency=currency,
                        quantity=line.quantity,
                        product=line.product_id,
                        partner=repair.partner_id,
                    )
                    amount_tax += result['total_included'] - result['total_excluded']
            repair.amount_untaxed = amount_untaxed
            repair.amount_tax = amount_tax
            repair.amount_total = amount_untaxed + amount_tax

    def action_create_sale_order(self):
        self.ensure_one()
        if self.sale_order_id:
            return {
                'name': _('Presupuesto/Orden'),
                'type': 'ir.actions.act_window',
                'res_model': 'sale.order',
                'view_mode': 'form',
                'res_id': self.sale_order_id.id,
            }
        order_lines = [
            Command.create({
                'product_id': line.product_id.id,
                'name': line.name or line.product_id.name,
                'product_uom_qty': line.quantity,
                'product_uom': line.product_uom_id.id,
                'price_unit': line.price_unit,
                'discount': line.discount,
                'tax_id': [Command.set(line.tax_ids.ids)],
            })
            for line in self.repair_line_ids
        ]
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_id.id,
            'origin': self.name,
            'company_id': self.company_id.id,
            'order_line': order_lines,
        })
        self.sale_order_id = sale_order.id
        return {
            'name': _('Presupuesto/Orden'),
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'form',
            'res_id': sale_order.id,
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