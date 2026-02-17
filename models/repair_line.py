# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class RepairLine(models.Model):
    _name = 'project.project.line'
    _description = 'Línea de reparación'

    project_id = fields.Many2one(
        'project.project',
        string='Reparación',
        required=True,
        ondelete='cascade',
    )
    product_id = fields.Many2one(
        'product.product',
        string='Producto/Servicio',
        required=True,
    )
    name = fields.Char(string='Descripción')
    quantity = fields.Float(string='Cantidad', default=1.0)
    product_uom_id = fields.Many2one(
        'uom.uom',
        string='Unidad de medida',
    )
    price_unit = fields.Float(string='Precio unitario')
    discount = fields.Float(string='Descuento (%)', default=0.0)
    price_subtotal = fields.Float(
        string='Subtotal',
        compute='_compute_price_subtotal',
        store=True,
    )
    tax_ids = fields.Many2many(
        'account.tax',
        string='Impuestos',
        context={'active_test': False},
    )

    @api.depends('quantity', 'price_unit', 'discount')
    def _compute_price_subtotal(self):
        for line in self:
            subtotal = line.quantity * line.price_unit * (1.0 - (line.discount or 0.0) / 100.0)
            line.price_subtotal = subtotal

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.name = self.product_id.name
            self.price_unit = self.product_id.list_price
            self.product_uom_id = self.product_id.uom_id
            company = self.project_id.company_id if self.project_id else self.env.company
            self.tax_ids = self.product_id.taxes_id._filter_taxes_by_company(company) if self.product_id.taxes_id else self.env['account.tax']
        else:
            self.name = False
            self.price_unit = 0.0
            self.product_uom_id = False
            self.tax_ids = self.env['account.tax']
