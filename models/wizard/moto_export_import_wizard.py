from odoo import models, fields, api, _
from odoo.exceptions import UserError
import base64
import csv
import io
import os

class MotoExportWizard(models.TransientModel):
    _name = 'taller.moto.export.wizard'
    _description = 'Exportar Motos'

    export_file = fields.Binary('Archivo de exportación')
    export_filename = fields.Char('Nombre de archivo', default='motos_export.csv')
    export_images = fields.Boolean('Exportar imágenes', default=True)
    export_images_folder = fields.Char('Carpeta de imágenes', default='/tmp/motos_export')

    def action_export_motos(self):
        # Buscar todas las motos
        motos = self.env['taller.moto'].search([])
        
        # Preparar buffer para CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Escribir encabezados
        headers = [
            'ID', 'Marca', 'Modelo', 'Matrícula', 'Chasis', 
            'Cliente', 'Fecha de Compra', 'Kilometraje', 
            'Notas', 'Estado', 'Número de Llave', 'Imagen'
        ]
        writer.writerow(headers)
        
        # Crear carpeta para imágenes si está habilitado
        if self.export_images:
            os.makedirs(self.export_images_folder, exist_ok=True)
        
        # Escribir datos de motos
        for moto in motos:
            # Manejar imagen
            imagen_filename = ''
            if self.export_images and moto.imagen:
                # Generar nombre de archivo único
                imagen_filename = f"moto_{moto.id}_{moto.matricula}.jpg"
                imagen_path = os.path.join(self.export_images_folder, imagen_filename)
                
                # Guardar imagen
                try:
                    with open(imagen_path, 'wb') as imagen_file:
                        imagen_file.write(base64.b64decode(moto.imagen))
                except Exception as e:
                    self.env.cr.rollback()
                    raise UserError(f"Error guardando imagen: {str(e)}")
            
            # Escribir fila de datos
            writer.writerow([
                moto.id,
                moto.marca,
                moto.modelo,
                moto.matricula,
                moto.chasis,
                moto.cliente_id.name,
                moto.fecha_compra,
                moto.kilometraje,
                moto.notas,
                moto.state,
                moto.numero_llave,
                imagen_filename
            ])
        
        # Convertir a base64
        export_file = base64.b64encode(output.getvalue().encode('utf-8'))
        
        # Guardar archivo y abrir wizard de descarga
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'taller.moto.export.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_export_file': export_file,
                'default_export_filename': 'motos_export.csv'
            }
        }

class MotoImportWizard(models.TransientModel):
    _name = 'taller.moto.import.wizard'
    _description = 'Importar Motos'

    import_file = fields.Binary('Archivo CSV', required=True)
    import_images_folder = fields.Char('Carpeta de imágenes')
    filename = fields.Char('Nombre de archivo')

    def action_import_motos(self):
        # Verificar que se haya subido un archivo
        if not self.import_file:
            raise UserError(_("Por favor, suba un archivo CSV"))
        
        # Decodificar el archivo
        try:
            csv_data = base64.b64decode(self.import_file).decode('utf-8')
            csv_file = io.StringIO(csv_data)
            csv_reader = csv.reader(csv_file)
            
            # Saltar encabezados
            next(csv_reader)
            
            # Contador de importaciones
            created_count = 0
            
            # Procesar cada línea
            for row in csv_reader:
                # Verificar si la línea tiene suficientes datos
                if len(row) < 12:
                    continue
                
                # Buscar o crear cliente
                cliente = self.env['res.partner'].search([('name', '=', row[5])], limit=1)
                if not cliente:
                    cliente = self.env['res.partner'].create({'name': row[5]})
                
                # Manejar imagen
                imagen_data = False
                imagen_filename = row[11]
                if imagen_filename and self.import_images_folder:
                    imagen_path = os.path.join(self.import_images_folder, imagen_filename)
                    try:
                        with open(imagen_path, 'rb') as imagen_file:
                            imagen_data = base64.b64encode(imagen_file.read())
                    except Exception as e:
                        # Log error pero continuar con la importación
                        self.env.cr.rollback()
                
                # Crear o actualizar moto
                moto_data = {
                    'marca': row[1],
                    'modelo': row[2],
                    'matricula': row[3],
                    'chasis': row[4],
                    'cliente_id': cliente.id,
                    'fecha_compra': row[6] or False,
                    'kilometraje': float(row[7] or 0),
                    'notas': row[8],
                    'state': row[9],
                    'numero_llave': row[10],
                    'imagen': imagen_data
                }
                
                # Intentar encontrar moto existente por matrícula
                existing_moto = self.env['taller.moto'].search([('matricula', '=', row[3])], limit=1)
                
                if existing_moto:
                    existing_moto.write(moto_data)
                else:
                    self.env['taller.moto'].create(moto_data)
                
                created_count += 1
            
            # Mostrar mensaje de éxito
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Importación Completada'),
                    'message': _(f'Se importaron {created_count} motos'),
                    'sticky': False,
                }
            }
        
        except Exception as e:
            raise UserError(_(f"Error al importar: {str(e)}"))