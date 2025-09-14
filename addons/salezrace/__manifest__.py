# -*- coding: utf-8 -*-
{
    "name": "SalezRace",
    "version": "17.0.1.0.0",
    "category": "Tools",
    "summary": "Simple race organizer: Registration, Start, Finish",
    "description": "Register racers, start them, and log/assign finish times.",
    "author": "Your Company",
    "license": "LGPL-3",
    "depends": ["base", "web", "mail"],
    "data": [
        "security/salezrace_security.xml",
        "security/ir.model.access.csv",
        "views/racer_views.xml",
        "views/racer_time_wizard_views.xml",
        "views/menu_and_actions.xml",
        "views/hide_apps.xml"
    ],
    "assets": {
        "web.assets_backend": [
            "salezrace/static/src/js/start_client_action.js",
            "salezrace/static/src/xml/start_client_action.xml",
            "salezrace/static/src/js/finish_client_action.js",
            "salezrace/static/src/xml/finish_client_action.xml",
            'salezrace/static/src/scss/style.scss',
        ],
    },
    "installable": True,
    "application": True,
}
