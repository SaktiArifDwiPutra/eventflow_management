{
    'name': 'EventFlow Management',
    'version': '19.0.1.0.0',
    'summary': 'Event and training management with approval workflow',
    'category': 'Marketing/Events',
    'author': 'Sakti',
    'license': 'LGPL-3',
    'depends': ['base', 'event', 'event_sale'],
    'data': [
                'security/eventflow_security.xml', 
                'security/eventflow_rules.xml', 
                'views/event_event_views.xml',
                'views/event_registration_views.xml',
                'views/eventflow_menus.xml',
                'views/eventflow_reports.xml',
            ],
    'application': True,
    'installable': True,
}