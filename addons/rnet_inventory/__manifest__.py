{
    'name': "RNET - Inventory",
    'author': "RNET",
    'version': '0.1',

    'depends': ['stock'],

    'data': [
        'security/ir.model.access.csv',
        'data/product_sequence.xml',
        'views/brand_view.xml',
        'views/product_group_views.xml',
        'views/res_users_views.xml',
        'views/stock_picking_views.xml',
        'views/cost_category.xml',
        'views/stock_location.xml',
        'views/stock_inventory.xml',
        'security/security.xml',
    ],

    "installable": True,
    "auto_install": False,
    "application": True,
}
