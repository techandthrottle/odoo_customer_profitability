# -*- coding: utf-8 -*-
from odoo import http

# class BiAnalysis(http.Controller):
#     @http.route('/bi_analysis/bi_analysis/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/bi_analysis/bi_analysis/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('bi_analysis.listing', {
#             'root': '/bi_analysis/bi_analysis',
#             'objects': http.request.env['bi_analysis.bi_analysis'].search([]),
#         })

#     @http.route('/bi_analysis/bi_analysis/objects/<model("bi_analysis.bi_analysis"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('bi_analysis.object', {
#             'object': obj
#         })