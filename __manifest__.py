{
    'name': 'EventFlow Management',
    'version': '19.0.1.0.0',
    'summary': 'Event and training management with approval workflow',
    'category': 'Marketing/Events',
    'author': 'Sakti',
    'license': 'LGPL-3',
    'depends': ['base', 'event'],
    'data': [
                'security/eventflow_security.xml',  
                'views/event_event_views.xml',
                'views/event_registration_views.xml',
            ],
    'application': True,
    'installable': True,
}