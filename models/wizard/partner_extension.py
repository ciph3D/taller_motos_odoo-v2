# models/wizard/partner_extension.py
from odoo import fields, models


class PartnerExtension(models.Model):
    _inherit = 'res.partner'

    # Campo legacy (ya no se usa para redirección; el wizard crea el cliente inline)
    taller_wizard_active = fields.Boolean(string='Wizard Activo', default=False, store=False)