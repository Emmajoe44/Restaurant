# -*- coding: utf-8 -*-
# from odoo import http


# class ProductNotifications(http.Controller):
#     @http.route('/product_notifications/product_notifications/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/product_notifications/product_notifications/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('product_notifications.listing', {
#             'root': '/product_notifications/product_notifications',
#             'objects': http.request.env['product_notifications.product_notifications'].search([]),
#         })

#     @http.route('/product_notifications/product_notifications/objects/<model("product_notifications.product_notifications"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('product_notifications.object', {
#             'object': obj
#         })
