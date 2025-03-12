{
    'name': 'Taller de Motos',
    'version': '1.0',
    'category': 'Services',
    'summary': 'Gestión de taller de motos',
    'description': """
        Módulo para gestionar un taller de motos
        - Preserva datos de motos al desinstalar
    """,
    'depends': [
        'base', 
        'contacts', 
        'project', 
        'sale_management', 
        'account',
        'calendar'
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/repair_stages.xml',
        'views/partner_views.xml',
        'views/moto_views.xml',
        'views/repair_views.xml',
        'views/menu_views.xml',
    ],
    'uninstall_hook': 'uninstall_hook',  # Añadimos este hook
    'application': True,
    'installable': True,
    'license': 'LGPL-3',
}