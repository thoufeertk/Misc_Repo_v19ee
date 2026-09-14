{
    'name': 'Property Management',
    'version': '19.0.1.3.0',
    'category': 'Real Estate/Property Management',
    'summary': 'Manage buildings, rooms, tenants, recurring rent invoicing and document expiry',
    'description': """
Property Management
====================
A minimal but complete property management module for Odoo 19:

* Manage buildings and their rooms/units.
* Manage tenants using the standard Contacts (res.partner) model.
* Create tenancy agreements with a monthly, quarterly, yearly or custom
  invoicing frequency; draft customer invoices are generated automatically
  (using the standard Odoo Invoicing model) until the tenancy validity date.
* Track building documents (tax receipts, insurance, licenses, ...) as
  attachments with expiry dates and automatic reminder activities.
* A colorful KPI & chart dashboard with building/room occupancy and revenue overview.
* Amenities, photo galleries and richer details on buildings and rooms.
* Free OpenStreetMap-based geolocation and an embedded buildings map.
""",
    'author': 'Machinser Group Global',
    'website': 'https://www.machinsergroupglobal.com',
    'license': 'LGPL-3',
    'depends': ['base', 'mail', 'product', 'account', 'base_geolocalize'],
    'data': [
        'security/ir.model.access.csv',
        'data/analytic_plan_data.xml',
        'data/amenity_data.xml',
        'data/ir_sequence_data.xml',
        'data/product_data.xml',
        'data/ir_cron_data.xml',
        'views/property_amenity_views.xml',
        'views/property_building_views.xml',
        'views/property_room_views.xml',
        'views/property_tenancy_views.xml',
        'views/property_document_views.xml',
        'views/res_partner_views.xml',
        'views/account_move_views.xml',
        'views/property_dashboard_views.xml',
        'views/property_map_views.xml',
        'views/msr_property_management_menus.xml',
        'views/res_config_settings_views.xml',
    ],
    'demo': [
        'demo/property_demo.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'msr_property_management/static/src/js/dashboard/*.js',
            'msr_property_management/static/src/js/map/*.js',
            'msr_property_management/static/src/js/widgets/*.js',
            'msr_property_management/static/src/xml/*.xml',
            'msr_property_management/static/src/scss/*.scss',
        ],
    },
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
    'post_init_hook': 'post_init_hook',
}
