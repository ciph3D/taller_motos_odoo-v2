{
    'name': 'Taller de Motos',
    'version': '1.1',
    'category': 'Services',
    'summary': 'Gestión de taller de motos',
    'description': """
        Módulo para gestionar un taller de motos
        - Preserva datos de motos al desinstalar
        - Wizard integrado para ingreso de motos a reparación
    """,
    'depends': [
        'base', 
        'contacts', 
        'project', 
        'sale_management', 
        'account',
        'calendar',
        'web'
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/repair_stages.xml',
        'views/partner_views.xml',
        'views/moto_views.xml',
        'views/repair_views.xml',
        'views/menu_views.xml',
        'views/wizard/moto_ingresar_wizard_views.xml',
        'views/wizard/moto_button_views.xml',
        'report/repair_reports.xml',
    ],
    'uninstall_hook': 'uninstall_hook',
    'application': True,
    'installable': True,
    'license': 'LGPL-3',

    'assets': {
        'web.assets_backend': [
            'taller_motos/static/src/css/wizard_styles.css',
        ],
    },
}

