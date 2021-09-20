# -*- coding: utf-8 -*-
{
    'name': "BI Analysis",

    'summary': """
        """,

    'description': """
        
    """,

    'author': "1000 Miles",
    'website': "http://www.1000miles.biz",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'product_development', 'customer_projects'],

    'js': [
        'static/src/js/alter_create.js',
        ],
    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'data/cron_config.xml',
        'views/customer_profitability.xml',
        'views/sale_order.xml',
        'views/views.xml',
        'views/templates.xml',
        ],

    'qweb': [
        'static/src/xml/web_widget_alter_create.xml',
        ],

    'installable': True,
    'application': True,
    'auto_install': False,
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}