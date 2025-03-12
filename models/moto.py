from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class Moto(models.Model):
    _name = 'taller.moto'
    _description = 'Motocicleta del cliente'
    _rec_name = 'display_name'
    
    # Campos básicos
    marca = fields.Char(string='Marca', required=True)
    modelo = fields.Char(string='Modelo', required=True)
    matricula = fields.Char(string='Matrícula', required=True)
    chasis = fields.Char(string='Nº Chasis')
    fecha_compra = fields.Date(string='Fecha de compra')
    kilometraje = fields.Float(string='Kilometraje')
    notas = fields.Text(string='Notas')
    
    # Campo para llaves
    numero_llave = fields.Char(string='Número de llave', help='Número de la etiqueta asignada a la llave de la moto')
    
    # Campo para imagen
    imagen = fields.Binary(string='Imagen')
    
    # Relaciones
    cliente_id = fields.Many2one('res.partner', string='Cliente', required=True)
    
    # Estados
    state = fields.Selection([
        ('activa', 'Activa'),
        ('reparacion', 'En reparación'),
        ('pendiente', 'Pendiente de recogida'),
        ('terminado', 'Terminado')
    ], string='Estado', default='activa')
    
    # Campos calculados
    display_name = fields.Char(compute='_compute_display_name', store=True)
    repair_count = fields.Integer(compute='_compute_repair_count', string="Reparaciones")
    
    # Restricciones SQL
    _sql_constraints = [
        ('unique_matricula', 'unique(matricula)', 'La matrícula debe ser única'),
    ]
    
    # Validaciones
    @api.constrains('matricula')
    def _check_matricula(self):
        for record in self:
            if record.matricula and len(record.matricula) < 3:
                raise ValidationError(_("La matrícula debe tener al menos 3 caracteres"))
    
    @api.depends('marca', 'modelo', 'matricula')
    def _compute_display_name(self):
        for moto in self:
            moto.display_name = f"{moto.marca} {moto.modelo} ({moto.matricula or 'Sin matrícula'})"
    
    @api.depends()
    def _compute_repair_count(self):
        for moto in self:
            moto.repair_count = self.env['project.project'].search_count([
                ('moto_id', '=', moto.id)
            ])
    
    def action_view_repairs(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Reparaciones'),
            'res_model': 'project.project',
            'view_mode': 'list,form',
            'domain': [('moto_id', '=', self.id)],
            'context': {'default_moto_id': self.id, 'default_partner_id': self.cliente_id.id}
        }
    
    def copy(self, default=None):
        """
        Personalizar la duplicación para evitar conflictos de matrícula
        """
        if default is None:
            default = {}
        default['matricula'] = f"{self.matricula}_COPIA"
        return super().copy(default)
    
    # Métodos para transiciones de estado
    def action_set_activa(self):
        """Cambiar estado a Activa"""
        for moto in self:
            moto.write({'state': 'activa'})
    
    def action_set_reparacion(self):
        """Cambiar estado a En reparación"""
        for moto in self:
            moto.write({'state': 'reparacion'})
            
            # Opcional: Crear un proyecto de reparación automáticamente
            self.env['project.project'].create({
                'name': f"Reparación de {moto.display_name}",
                'partner_id': moto.cliente_id.id,
                'moto_id': moto.id,
                'kilometraje_entrada': moto.kilometraje,
            })
    
    def action_set_pendiente(self):
        """Cambiar estado a Pendiente de recogida"""
        for moto in self:
            # Buscar si hay un proyecto de reparación activo
            repair_projects = self.env['project.project'].search([
                ('moto_id', '=', moto.id),
                ('stage_id.name', '!=', 'Completado')
            ], limit=1)
            
            if repair_projects:
                # Marcar la reparación como completada
                task_type_completed = self.env.ref('taller_motos.repair_stage_completed', False)
                if task_type_completed:
                    for task in repair_projects.task_ids:
                        task.write({'stage_id': task_type_completed.id})
            
            moto.write({'state': 'pendiente'})
            
    def action_set_terminado(self):
        """Cambiar estado a Terminado (entregado al cliente)"""
        for moto in self:
            # Registramos que la moto ha sido entregada
            moto.write({
                'state': 'terminado',
                # También podríamos actualizar la fecha de salida si lo deseamos
            })
            
            # Opcionalmente, podríamos cerrar formalmente los proyectos de reparación
            # asociados que estén en estado pendiente
            repair_projects = self.env['project.project'].search([
                ('moto_id', '=', moto.id),
                ('active', '=', True)
            ])
            
            if repair_projects:
                for repair in repair_projects:
                    # Si la reparación tiene alguna tarea pendiente, la marcamos como completada
                    for task in repair.task_ids.filtered(lambda t: t.stage_id.fold is False):
                        task_type_completed = self.env.ref('taller_motos.repair_stage_completed', False)
                        if task_type_completed:
                            task.write({'stage_id': task_type_completed.id})
                    
                    # Si queremos, podríamos también registrar la fecha de salida
                    if not repair.fecha_salida:
                        repair.write({'fecha_salida': fields.Date.today()})