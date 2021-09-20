# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _
from pprint import pprint


class CustomerProfitability(models.Model):
    _name = 'bi_analysis.customer_profitability'

    cust_id = fields.Many2one('hr.employee')
    so_id = fields.Many2one('sale.order')
    sales_order_ids = fields.Many2many('sale.order')
    merch_id = fields.Many2one('res.users')
    sales_team = fields.Many2one('crm.team')
    project_id = fields.Many2one('customer_projects.project')
    assortment_id = fields.Many2one('product.product')

    so_qty = fields.Float(string='Order Qty.')
    so_sales_price = fields.Float(string='Sales Price')
    so_sub_total = fields.Float(string='Sale Order Sub-Total')
    po_total_cost = fields.Float(string='PO Total Cost')
    vendor_bill_cost = fields.Float(string='Vendor Bill Cost')
    invoice_date = fields.Float(string='Invoice Date')
    invoice_qty = fields.Float(string='Invoice Quantity')
    invoice_amount = fields.Float(string='Invoice Amount')

    name = fields.Char()
    so_name = fields.Char(string='Sale Order', store=True)
    cust_name = fields.Char(string='Customer Name', store=True)
    merch_name = fields.Char(string='Merchandiser', store=True)
    sales_team_name = fields.Char(string='Sales Team', store=True)
    project_name = fields.Char(string='Project', store=True)
    assortment_number = fields.Char(string='Assortment Number', store=True)
    assortment_description = fields.Char(string='Description', store=True)
    product_category = fields.Char(string='Product Category', store=True)

    @api.model
    def display_so_list(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'res_id': 'order_id',
            'name': 'Sales Order',
            'views': [(False, 'form')],
            'view_type': 'form',
            'view_mode': 'tree',
            'target': 'new',
        }

    @api.model
    def do_get_so_list(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'bi_analysis.customer_profitability',
            'name': 'Sales Order',
            'views': [(False, 'form')],
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
        }

    @api.multi
    def close_dialog(self):
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }


class BITempSO(models.TransientModel):
    _name = 'bi_analysis.so.create'

    name = fields.Char(string='Name')
    sales_order_ids = fields.Many2many('sale.order')

    @api.model
    def do_get_so_list(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'bi_analysis.so.create',
            'name': 'Sales Order',
            'views': [(False, 'form')],
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
        }

    @api.multi
    def close_dialog(self):
        pprint("XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX")
        #pprint(self.sales_order_ids.ids)
        for item in self.sales_order_ids.ids:
            pprint(item)
        # self.env['bi_analysis.customer_profitability'].create({
        #     'sales_order_ids': [[6, 0, self.sales_order_ids.ids]]
        # })
        pass
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }


class BISaleOrder(models.Model):
    _inherit = 'sale.order'

