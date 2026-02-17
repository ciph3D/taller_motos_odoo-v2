# models/wizard/moto_ingresar_wizard.py
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import base64
import logging

_logger = logging.getLogger(__name__)

class MotoIngresarWizard(models.TransientModel):
    _name = 'taller.moto.ingresar.wizard'
    _description = 'Asistente para ingresar motos a reparación'
    
    # Campos para controlar el estado del wizard
    state = fields.Selection([
        ('cliente', 'Selección de Cliente'),
        ('moto', 'Datos de la Moto'),
        ('sintomas', 'Registro de Síntomas'),
        ('fotos', 'Documentación Fotográfica'),
        ('confirmacion', 'Confirmación Final')
    ], default='cliente', string='Etapa')
    
    # Campos para la etapa de cliente
    partner_id = fields.Many2one('res.partner', string='Cliente')
    partner_name = fields.Char(string='Nombre', related='partner_id.name', readonly=True)
    partner_phone = fields.Char(string='Teléfono', related='partner_id.phone', readonly=True)
    partner_email = fields.Char(string='Email', related='partner_id.email', readonly=True)
    cliente_nuevo = fields.Boolean(string='¿Cliente nuevo?')
    # Campos para crear cliente inline (cuando cliente_nuevo es True)
    nuevo_nombre = fields.Char(string='Nombre del cliente')  # obligatorio si cliente_nuevo
    nuevo_telefono = fields.Char(string='Teléfono')
    nuevo_email = fields.Char(string='Email')
    nuevo_nif = fields.Char(string='NIF/CIF')
    nuevo_street = fields.Char(string='Dirección')
    nuevo_city = fields.Char(string='Población')
    nuevo_zip = fields.Char(string='Código Postal')
    
    # Campos para la etapa de moto
    moto_id = fields.Many2one('taller.moto', string='Moto existente', domain="[('cliente_id', '=', partner_id)]")
    moto_nueva = fields.Boolean(string='¿Moto nueva?')
    marca = fields.Char(string='Marca')
    modelo = fields.Char(string='Modelo')
    matricula = fields.Char(string='Matrícula')
    chasis = fields.Char(string='Nº Chasis')
    kilometraje = fields.Float(string='Kilometraje')
    numero_llave = fields.Char(string='Número de llave')
    
    # Campos para la etapa de fotos
    foto_frontal = fields.Binary(string='Foto Frontal')
    foto_frontal_name = fields.Char(string='Nombre archivo frontal', default='frontal.jpg')
    foto_lateral_izq = fields.Binary(string='Foto Lateral Izquierdo')
    foto_lateral_izq_name = fields.Char(string='Nombre archivo lateral izq', default='lateral_izq.jpg')
    foto_lateral_der = fields.Binary(string='Foto Lateral Derecho')
    foto_lateral_der_name = fields.Char(string='Nombre archivo lateral der', default='lateral_der.jpg')
    foto_trasera = fields.Binary(string='Foto Trasera')
    foto_trasera_name = fields.Char(string='Nombre archivo trasera', default='trasera.jpg')
    foto_tablero = fields.Binary(string='Foto Tablero/Kilometraje')
    foto_tablero_name = fields.Char(string='Nombre archivo tablero', default='tablero.jpg')
    foto_adicional = fields.Binary(string='Foto Adicional')
    foto_adicional_name = fields.Char(string='Nombre archivo adicional', default='adicional.jpg')
    
    # Campos para la etapa de síntomas
    sintomas = fields.Text(string='Síntomas reportados', required=False)
    diagnostico_preliminar = fields.Text(string='Diagnóstico preliminar')
    fecha_prevista_entrega = fields.Date(string='Fecha prevista de entrega')
    solicita_presupuesto = fields.Boolean(string='Solicita presupuesto previo', default=True)
    
    # Campos para la etapa de confirmación
    nombre_proyecto = fields.Char(string='Nombre del proyecto', compute='_compute_nombre_proyecto')
    imagen_seleccionada = fields.Binary(string='Imagen principal', compute='_compute_imagen_seleccionada')
    cliente_firma = fields.Binary(string='Firma del cliente')
    cliente_acepta_condiciones = fields.Boolean(string='Aceptar términos y condiciones', default=False)
    recoge_piezas = fields.Boolean(string='Recoge piezas sustituidas', default=False)
    avisar_telefono = fields.Boolean(string='Avisar por teléfono', default=True)
    prioridad = fields.Selection([
        ('0', 'Normal'),
        ('1', 'Baja'),
        ('2', 'Alta'),
        ('3', 'Muy alta')
    ], string='Prioridad', default='0')
    
    # Campo para mostrar la matrícula de la moto seleccionada
    moto_matricula = fields.Char(string='Matrícula de moto seleccionada', compute='_compute_moto_matricula')
    
    # MÉTODOS COMPUTADOS
    
    @api.depends('marca', 'modelo', 'matricula', 'moto_id')
    def _compute_nombre_proyecto(self):
        for wizard in self:
            if wizard.moto_id:
                wizard.nombre_proyecto = f"Reparación de {wizard.moto_id.display_name}"
            elif wizard.marca and wizard.modelo:
                matricula_str = f" ({wizard.matricula})" if wizard.matricula else ""
                wizard.nombre_proyecto = f"Reparación de {wizard.marca} {wizard.modelo}{matricula_str}"
            else:
                wizard.nombre_proyecto = "Nueva reparación"
    
    @api.depends('foto_frontal', 'moto_id')
    def _compute_imagen_seleccionada(self):
        for wizard in self:
            if wizard.foto_frontal:
                wizard.imagen_seleccionada = wizard.foto_frontal
            elif wizard.moto_id and wizard.moto_id.imagen:
                wizard.imagen_seleccionada = wizard.moto_id.imagen
            else:
                wizard.imagen_seleccionada = False
    
    @api.depends('moto_id')
    def _compute_moto_matricula(self):
        for wizard in self:
            wizard.moto_matricula = wizard.moto_id.matricula if wizard.moto_id else False
    
    # MÉTODOS DE ACCIÓN
    
    def action_previous(self):
        """Retroceder a la etapa anterior"""
        states = ['cliente', 'moto', 'sintomas', 'fotos', 'confirmacion']
        current_index = states.index(self.state)
        
        if current_index > 0:
            self.state = states[current_index - 1]
        
        return self._reopen_view()
    
    def action_next(self):
        """Avanzar a la siguiente etapa"""
        # Validaciones específicas por etapa
        if self.state == 'cliente':
            if not self.partner_id and not self.cliente_nuevo:
                raise UserError(_("Debe seleccionar un cliente existente o marcar 'Cliente nuevo'"))
            if self.cliente_nuevo:
                if not (self.nuevo_nombre or '').strip():
                    raise UserError(_("El nombre del cliente es obligatorio"))
                partner_vals = {
                    'name': self.nuevo_nombre.strip(),
                    'customer_rank': 1,
                }
                if self.nuevo_telefono:
                    partner_vals['phone'] = self.nuevo_telefono
                if self.nuevo_email:
                    partner_vals['email'] = self.nuevo_email
                if self.nuevo_nif:
                    partner_vals['vat'] = self.nuevo_nif
                if self.nuevo_street:
                    partner_vals['street'] = self.nuevo_street
                if self.nuevo_city:
                    partner_vals['city'] = self.nuevo_city
                if self.nuevo_zip:
                    partner_vals['zip'] = self.nuevo_zip
                partner = self.env['res.partner'].with_context(no_wizard_redirect=True).create(partner_vals)
                self.partner_id = partner
                
        elif self.state == 'moto':
            if not self.moto_id and not self.moto_nueva:
                raise UserError(_("Debe seleccionar una moto existente o marcar 'Moto nueva'"))
            if self.moto_nueva and not self.marca:
                raise UserError(_("El campo 'Marca' es obligatorio para motos nuevas"))
            if self.moto_nueva and not self.modelo:
                raise UserError(_("El campo 'Modelo' es obligatorio para motos nuevas"))
            if self.moto_nueva and not self.matricula:
                raise UserError(_("El campo 'Matrícula' es obligatorio para motos nuevas"))
                
        elif self.state == 'sintomas':
            if not self.sintomas:
                raise UserError(_("Debe especificar los síntomas reportados por el cliente"))
            # if not self.fecha_prevista_entrega:
            #    raise UserError(_("Debe especificar una fecha prevista de entrega"))
        
        # Avanzar a la siguiente etapa
        states = ['cliente', 'moto', 'sintomas', 'fotos', 'confirmacion']
        current_index = states.index(self.state)
        
        if current_index < len(states) - 1:
            self.state = states[current_index + 1]
        
        return self._reopen_view()
    
    def action_confirm(self):
        """Confirmar y crear los registros necesarios"""
        self.ensure_one()
        
        if not self.cliente_acepta_condiciones:
            raise UserError(_("El cliente debe aceptar los términos y condiciones"))
            
        if not self.cliente_firma:
            raise UserError(_("Se requiere la firma del cliente para continuar"))
        
        # 1. Crear/actualizar moto si es necesario
        moto_id = self.moto_id
        if not moto_id:
            # Crear nueva moto
            moto_vals = {
                'marca': self.marca,
                'modelo': self.modelo,
                'matricula': self.matricula,
                'chasis': self.chasis,
                'kilometraje': self.kilometraje,
                'numero_llave': self.numero_llave,
                'cliente_id': self.partner_id.id,
                'state': 'reparacion',  # Marcar directamente como en reparación
            }
            
            # Asignar imagen frontal como imagen principal de la moto
            if self.foto_frontal:
                moto_vals['imagen'] = self.foto_frontal
                
            moto_id = self.env['taller.moto'].create(moto_vals)
        else:
            # Actualizar moto existente
            vals = {
                'state': 'reparacion',
                'kilometraje': self.kilometraje or moto_id.kilometraje,
            }
            if self.numero_llave:
                vals['numero_llave'] = self.numero_llave
            moto_id.write(vals)
        
        # 2. Crear proyecto de reparación
        project_vals = {
            'name': self.nombre_proyecto,
            'partner_id': self.partner_id.id,
            'moto_id': moto_id.id,
            'sintomas': self.sintomas,
            'diagnostico': self.diagnostico_preliminar,
            'kilometraje_entrada': self.kilometraje or moto_id.kilometraje,
            'fecha_entrada': fields.Date.today(),
            'fecha_prevista_entrega': self.fecha_prevista_entrega,
            'cliente_firma': self.cliente_firma,
            'cliente_acepta_condiciones': self.cliente_acepta_condiciones,
            'solicita_presupuesto': self.solicita_presupuesto,
            'recoge_piezas': self.recoge_piezas,
            'avisar_telefono': self.avisar_telefono,
            #'priority': self.prioridad,
        }
        
        repair_project = self.env['project.project'].create(project_vals)
        
        # 3. Adjuntar fotos como documentos al proyecto
        self._attach_photos_to_project(repair_project)
        
        # 4. Crear tarea inicial en el proyecto
        self._create_initial_task(repair_project)
        
        # 5. Mostrar mensaje de confirmación y redirigir
        return {
            'type': 'ir.actions.act_window',
            'name': _('Proyecto de Reparación'),
            'res_model': 'project.project',
            'res_id': repair_project.id,
            'view_mode': 'form',
            'target': 'current',

            }
        
        
    def _attach_photos_to_project(self, project):
        """Adjuntar las fotos tomadas al proyecto"""
        attachments = []
        
        # Mapeo de campos y nombres de archivo
        foto_fields = [
            ('foto_frontal', 'foto_frontal_name', 'Frontal'),
            ('foto_lateral_izq', 'foto_lateral_izq_name', 'Lateral Izquierdo'),
            ('foto_lateral_der', 'foto_lateral_der_name', 'Lateral Derecho'),
            ('foto_trasera', 'foto_trasera_name', 'Trasera'),
            ('foto_tablero', 'foto_tablero_name', 'Tablero/Kilometraje'),
            ('foto_adicional', 'foto_adicional_name', 'Adicional')
        ]
        
        for field, field_name, description in foto_fields:
            foto = getattr(self, field)
            if foto:
                filename = f"{project.name} - {description}.jpg"
                attachment = self.env['ir.attachment'].create({
                    'name': filename,
                    'datas': foto,
                    'res_model': 'project.project',
                    'res_id': project.id,
                })
                attachments.append(attachment.id)
        
        if attachments:
            project.write({'foto_ids': [(6, 0, attachments)]})
        return attachments
    
    def _create_initial_task(self, project):
        """Crear tarea inicial en el proyecto"""
        # Obtener la etapa de 'Diagnóstico'
        diagnosis_stage = self.env.ref('taller_motos.repair_stage_diagnosis', False)
        stage_id = diagnosis_stage.id if diagnosis_stage else False

        
        # Crear la tarea
        task_vals = {
            'name': 'Diagnóstico inicial',
            'project_id': project.id,
            'stage_id': stage_id,
            'description': self.sintomas,
            'partner_id': self.partner_id.id,
        #   'priority': self.prioridad,
            'date_deadline': self.fecha_prevista_entrega,
        }
        
        return self.env['project.task'].sudo().create(task_vals)
        
        
    def _reopen_view(self):
        """Volver a abrir la vista del wizard con el estado actualizado"""
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
        }