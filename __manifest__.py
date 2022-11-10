{
    'name': 'Fleet Booking For Trucking',
    'version': '15.0.0.0.0.1',
    'summary': 'Fleet Booking For Trucking',
    'author': 'Agus Muhammad Ramdan',
    'license': 'LGPL-3',
    'website': 'https://www.mycompany.com',
    'depends': [
        'fleet',
        'contacts' 
    ],
    'data': [
        "security/res_groups.xml",
        "security/ir.model.access.csv",
        "views/fleet_booking_view.xml"
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
