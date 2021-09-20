# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _
from datetime import datetime, timedelta, date, time
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from pprint import pprint


class SaleOrderProfitability(models.Model):
    _name = 'bi_analysis.so_profitability'

    so_id = fields.Many2one('sale.order', string='Sale Order')
    customer_id = fields.Many2one('res.partner', string='Customer')
    contact_id = fields.Many2one('res.partner', string='Contact')
    project_id = fields.Many2one('customer_projects.project', string='Project')
    merchandiser_id = fields.Many2one('res.users', string='Merchandiser')
    sales_team_id = fields.Many2one('crm.team', string='Sales Team')
    invoice_id = fields.Many2one('account.invoice', string='Invoice')

    so_name = fields.Char(string='Sale Order')
    customer_name = fields.Char(string='Customer Name')
    contact_name = fields.Char(string='Contact')
    merchandiser = fields.Char(string='Merchandiser')
    sales_team = fields.Char(string='Sales Team')
    project = fields.Char(string='Project')
    total_so_amount_usd = fields.Float(string='Total Sales Order Amount (USD)')
    total_so_amount_cny = fields.Float(string='Total Sales Order Amount (CNY)')
    total_po_amount_usd = fields.Float(string='Total PO Amount (USD)')
    total_po_amount_cny = fields.Float(string='Total PO Amount (CNY)')
    total_vendor_bill_usd = fields.Float(string='Total Vendor Bill Amount (USD)')
    total_vendor_bill_cny = fields.Float(string='Total Vendor Bill Amount (CNY)')
    total_invoice_amount_usd = fields.Float(string='Total Invoice Amount (USD)')
    total_invoice_amount_cny = fields.Float(string='Total Invoice Amount (CNY)')
    gross_profit_margin = fields.Float(string='Gross Profit Margin', compute='_compute_theoretical_gpm')
    gross_profit_margin_percent = fields.Float(string='Gross Profit Margin Percentage (%)', compute='_compute_theoretical_gpmp')
    usd_cny_exchange = fields.Float(string='Exchange Rate (USD to CNY)')
    cny_usd_exchange = fields.Float(string='Exchange Rate (CNY to USD)')
    invoice_date = fields.Datetime(string='Invoice Date')

    so_line_profit_id = fields.One2many('bi_analysis.so_line_profit', 'so_id', ondelete="cascade")
    po_line_profit_id = fields.One2many('bi_analysis.po_line_profit', 'so_id', ondelete="cascade")
    ci_line_profit_id = fields.One2many('bi_analysis.ci_profit', 'so_id', ondelete="cascade")
    vb_line_profit_id = fields.One2many('bi_analysis.vb_profit', 'so_id', ondelete="cascade")

    @api.multi
    def _get_usd_currency(self):
        usd = self.env['res.currency'].search([('name', '=', 'USD')])
        if usd:
            return usd.id

    @api.multi
    def _get_cny_currency(self):
        cny = self.env['res.currency'].search([('name', '=', 'CNY')])
        if cny:
            return cny.id

    usd_currency = fields.Many2one('res.currency', string='Currency USD', default=_get_usd_currency)
    cny_currency = fields.Many2one('res.currency', string='Currency CNY', default=_get_cny_currency)

    @api.model
    def update_so(self):
        config = self.env['bi_analysis.so_cron_config'].search([], order='id desc', limit=1)

        so_data = self.env['sale.order'].search([('module', '=', 'production')])

        self.env['bi_analysis.so_profitability'].search([('invoice_date', '>=', config.si_start_date),
                                                         ('invoice_date', '<=', config.si_end_date)]).unlink()

        for item in so_data:
            if item.invoice_ids:
                for inv_id_line in item.invoice_ids:
                    if inv_id_line.state not in ['draft', 'cancelled']:
                        if inv_id_line.date_invoice >= config.si_start_date and inv_id_line.date_invoice < config.si_end_date:
                            trans_data = {
                                'so_name': item.name,
                                'so_id': item.id,
                                'customer_id': item.partner_id.id,
                                'contact_id': item.contact.id,
                                'project_id': item.cp_project_id.id,
                                'merchandiser_id': item.user_id.id,
                                'sales_team_id': item.team_id.id,
                                'customer_name': item.partner_id.name,
                                'contact_name': item.contact.name,
                                'merchandiser': item.user_id.name,
                                'sales_team': item.team_id.name,
                                'project': item.cp_project_id.name,
                                'invoice_date': inv_id_line.date_invoice,
                                'invoice_id': inv_id_line.id,
                                'usd_cny_exchange': 1 / self._cny_rate(inv_id_line.date_invoice),
                                'cny_usd_exchange': self._cny_rate(inv_id_line.date_invoice)
                            }

                            sol = self._compute_order_lines(item.id)
                            if sol[-1] == 'USD':
                                trans_data['total_so_amount_usd'] = sol[0]
                                trans_data['total_so_amount_cny'] = (1 / self._cny_rate(inv_id_line.date_invoice)) * \
                                                                    sol[0]
                            else:
                                trans_data['total_so_amount_cny'] = sol[0]
                                trans_data['total_so_amount_usd'] = self._cny_rate(inv_id_line.date_invoice) * sol[0]

                            pol = self._compute_po_lines(item.id)
                            if pol[-1] == 'USD':
                                trans_data['total_po_amount_usd'] = pol[0]
                                trans_data['total_po_amount_cny'] = (1 / self._cny_rate(inv_id_line.date_invoice)) * \
                                                                    pol[0]
                            else:
                                trans_data['total_po_amount_cny'] = pol[0]
                                trans_data['total_po_amount_usd'] = self._cny_rate(inv_id_line.date_invoice) * pol[0]

                            cil = self._compute_customer_invoice(item.id, inv_id_line.id)
                            if cil[-1] == 'USD':
                                trans_data['total_invoice_amount_usd'] = cil[0]
                                trans_data['total_invoice_amount_cny'] = (1 / self._cny_rate(
                                    inv_id_line.date_invoice)) * cil[0]
                            else:
                                trans_data['total_invoice_amount_cny'] = cil[0]
                                trans_data['total_invoice_amount_usd'] = self._cny_rate(inv_id_line.date_invoice) * cil[
                                    0]

                            vbl = self._compute_vendor_bills(item.id)
                            if vbl[-1] == 'USD':
                                trans_data['total_vendor_bill_usd'] = vbl[0]
                                trans_data['total_vendor_bill_cny'] = (1 / self._cny_rate(inv_id_line.date_invoice)) * \
                                                                      vbl[0]
                            else:
                                trans_data['total_vendor_bill_cny'] = vbl[0]
                                trans_data['total_vendor_bill_usd'] = self._cny_rate(inv_id_line.date_invoice) * vbl[0]

                            new_data = self.env['bi_analysis.so_profitability'].create(trans_data)
                            for so_line_data in sol[1]:
                                if 'so_id' not in so_line_data:
                                    so_line_data['so_id'] = new_data.id
                                    self.env['bi_analysis.so_line_profit'].create(so_line_data)
                            for po_line_data in pol[1]:
                                if 'so_id' not in po_line_data:
                                    po_line_data['so_id'] = new_data.id
                                    self.env['bi_analysis.po_line_profit'].create(po_line_data)
                            for ci_line_data in cil[1]:
                                if 'so_id' not in ci_line_data:
                                    ci_line_data['so_id'] = new_data.id
                                    self.env['bi_analysis.ci_profit'].create(ci_line_data)
                            for vb_line_data in vbl[1]:
                                if 'so_id' not in vb_line_data:
                                    vb_line_data['so_id'] = new_data.id
                                    self.env['bi_analysis.vb_profit'].create(vb_line_data)



    @api.onchange('total_invoice_amount_usd', 'total_invoice_amount_cny', 'total_vendor_bill_usd', 'total_vendor_bill_cny')
    def _compute_theoretical_gpm(self):
        for line in self:
            line.gross_profit_margin = line.total_vendor_bill_cny / line.total_invoice_amount_cny

    @api.onchange('gross_profit_margin')
    def _compute_theoretical_gpmp(self):
        for line in self:
            line.gross_profit_margin_percent = line.gross_profit_margin * 100


class TransSoProfitability(models.TransientModel):
    _name = 'bi_analysis.so_profitability.create'

    start_date = fields.Datetime()
    end_date = fields.Datetime()

    @api.model
    def display_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'bi_analysis.so_profitability.create',
            'name': 'Sales Invoice Data',
            'views': [(False, 'form')],
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
        }

    @api.multi
    def _compute_order_lines(self, so_id):
        so_line = self.env['sale.order.line'].search([('order_id', '=', so_id)])
        so_line_total = False
        curr = False
        so_line_data = []
        for item in so_line:
            so_line_total = so_line_total + item.price_subtotal
            curr = item.currency_id.name
            so_new_data = {
                'so_item_number': item.product_id.id,
                'so_item_number_id': item.product_id.item_number,
                'so_description': item.product_id.name,
                'so_ppu_st': item.ppu_st,
                'so_assortment_order_qty': item.product_uom_qty,
                'so_product_order_qty': item.ppu_st * item.product_uom_qty,
                'so_product_sales_price': item.prod_sales_price,
                'so_qty_invoice': item.qty_invoiced,
                'so_assortment_sales_price': item.price_unit,
                'so_price_subtotal': item.price_subtotal
            }
            so_line_data.append(so_new_data)
        so_line_data = [so_line_total, so_line_data, curr]
        return so_line_data

    @api.multi
    def _compute_po_lines(self, so_id):
        po_line = self.env['purchase.order'].search([('sale_order', '=', so_id)])
        po_line_total = False
        curr = False
        po_line_data = []
        for item in po_line:
            po_line_total = po_line_total + item.amount_total
            curr = item.currency_id.name
            po_new_data = {
                'po_name': item.name,
                'po_item_number': item.product_id.id,
                'po_item_number_id': item.product_id.item_number,
                'po_description': item.product_id.name,
                'po_partner_id': item.partner_id.id,
                'po_amount_total': item.amount_total,
                'po_status': item.state
            }
            po_line_data.append(po_new_data)
        po_line_data = [po_line_total, po_line_data, curr]
        return po_line_data

    @api.multi
    def _compute_customer_invoice(self, so_id, inv_id1):
        invoice_lines = self.env['account.invoice.line'].search([('invoice_id', '=', inv_id1)])
        ci_line_total = False
        curr = False
        ci_line_data = []
        for inv in invoice_lines:
            if inv.sale_order_id.id == so_id:
                ci_line_total = ci_line_total + inv.price_subtotal
                curr = inv.currency_id.name
                ci_new_data = {
                    'ci_cust_invoice_id': inv.invoice_id.id,
                    'ci_cust_invoice': inv.invoice_id.name,
                    'ci_item_number': inv.product_id.id,
                    'ci_item_number_id': inv.product_id.item_number,
                    'ci_description': inv.product_id.name,
                    'ci_account': inv.account_id.id,
                    'ci_quantity': inv.quantity,
                    'ci_unit_price': inv.price_unit,
                    'ci_total_amount': inv.price_subtotal
                }
                ci_line_data.append(ci_new_data)
        ci_line_data = [ci_line_total, ci_line_data, curr]
        return ci_line_data

    @api.multi
    def _compute_vendor_bills(self, so_id):
        po_line = self.env['purchase.order'].search([('sale_order', '=', so_id)])
        vendor_bill_total = False
        curr = False
        vb_line_data = []
        for item in po_line:
            acc_invoice_line = self.env['account.invoice'].search([('reference', '=', item.name),
                                                                   ('vendor_bill_date', '!=', False)])
            if acc_invoice_line:
                for ai_line in acc_invoice_line:
                    acc_invoice_line_line = self.env['account.invoice.line'].search(
                        [('invoice_id', '=', ai_line.id)])
                    for aill in acc_invoice_line_line:
                        vendor_bill_total = vendor_bill_total + aill.price_subtotal
                        curr = aill.currency_id.name
                        vb_new_data = {
                            'vb_vendor_bill_id': ai_line.id,
                            'vb_vendor_bill': ai_line.name,
                            'vb_item_number': aill.product_id.id,
                            'vb_item_number_id': aill.product_id.item_number,
                            'vb_description': aill.product_id.name,
                            'vb_quantity': aill.quantity,
                            'vb_unit_price': aill.price_unit,
                            'vb_total_amount': aill.price_subtotal
                        }
                        vb_line_data.append(vb_new_data)
        vb_line_data = [vendor_bill_total, vb_line_data, curr]
        return vb_line_data

    def _cny_rate(self, inv_date):
        rate = self.env['res.currency.rate'].search([('currency_id', '=', 3),
                                              ('name', '>=', inv_date),
                                              ('name', '<=', inv_date)])
        return rate.rate if rate else 1

    @api.multi
    def close_dialog(self):
        so_data = self.env['sale.order'].search([('module', '=', 'production')])

        self.env['bi_analysis.so_profitability'].search([('invoice_date', '>=', self.start_date),
                                                         ('invoice_date', '<=', self.end_date)]).unlink()

        for item in so_data:
            if item.invoice_ids:
                for inv_id_line in item.invoice_ids:
                    if inv_id_line.state not in ['draft', 'cancelled']:
                        if inv_id_line.date_invoice >= self.start_date and inv_id_line.date_invoice < self.end_date:
                            trans_data = {
                                'so_name': item.name,
                                'so_id': item.id,
                                'customer_id': item.partner_id.id,
                                'contact_id': item.contact.id,
                                'project_id': item.cp_project_id.id,
                                'merchandiser_id': item.user_id.id,
                                'sales_team_id': item.team_id.id,
                                'customer_name': item.partner_id.name,
                                'contact_name': item.contact.name,
                                'merchandiser': item.user_id.name,
                                'sales_team': item.team_id.name,
                                'project': item.cp_project_id.name,
                                'invoice_date': inv_id_line.date_invoice,
                                'invoice_id': inv_id_line.id,
                                'usd_cny_exchange': 1 / self._cny_rate(inv_id_line.date_invoice),
                                'cny_usd_exchange': self._cny_rate(inv_id_line.date_invoice)
                            }

                            sol = self._compute_order_lines(item.id)
                            if sol[-1] == 'USD':
                                trans_data['total_so_amount_usd'] = sol[0]
                                trans_data['total_so_amount_cny'] = (1 / self._cny_rate(inv_id_line.date_invoice)) * sol[0]
                            else:
                                trans_data['total_so_amount_cny'] = sol[0]
                                trans_data['total_so_amount_usd'] = self._cny_rate(inv_id_line.date_invoice) * sol[0]

                            pol = self._compute_po_lines(item.id)
                            if pol[-1] == 'USD':
                                trans_data['total_po_amount_usd'] = pol[0]
                                trans_data['total_po_amount_cny'] = (1 / self._cny_rate(inv_id_line.date_invoice)) * pol[0]
                            else:
                                trans_data['total_po_amount_cny'] = pol[0]
                                trans_data['total_po_amount_usd'] = self._cny_rate(inv_id_line.date_invoice) * pol[0]

                            cil = self._compute_customer_invoice(item.id, inv_id_line.id)
                            if cil[-1] == 'USD':
                                trans_data['total_invoice_amount_usd'] = cil[0]
                                trans_data['total_invoice_amount_cny'] = (1 / self._cny_rate(inv_id_line.date_invoice)) * cil[0]
                            else:
                                trans_data['total_invoice_amount_cny'] = cil[0]
                                trans_data['total_invoice_amount_usd'] = self._cny_rate(inv_id_line.date_invoice) * cil[0]

                            vbl = self._compute_vendor_bills(item.id)
                            if vbl[-1] == 'USD':
                                trans_data['total_vendor_bill_usd'] = vbl[0]
                                trans_data['total_vendor_bill_cny'] = (1 / self._cny_rate(inv_id_line.date_invoice)) * vbl[0]
                            else:
                                trans_data['total_vendor_bill_cny'] = vbl[0]
                                trans_data['total_vendor_bill_usd'] = self._cny_rate(inv_id_line.date_invoice) * vbl[0]

                            new_data = self.env['bi_analysis.so_profitability'].create(trans_data)
                            for so_line_data in sol[1]:
                                if 'so_id' not in so_line_data:
                                    so_line_data['so_id'] = new_data.id
                                    self.env['bi_analysis.so_line_profit'].create(so_line_data)
                            for po_line_data in pol[1]:
                                if 'so_id' not in po_line_data:
                                    po_line_data['so_id'] = new_data.id
                                    self.env['bi_analysis.po_line_profit'].create(po_line_data)
                            for ci_line_data in cil[1]:
                                if 'so_id' not in ci_line_data:
                                    ci_line_data['so_id'] = new_data.id
                                    self.env['bi_analysis.ci_profit'].create(ci_line_data)
                            for vb_line_data in vbl[1]:
                                if 'so_id' not in vb_line_data:
                                    vb_line_data['so_id'] = new_data.id
                                    self.env['bi_analysis.vb_profit'].create(vb_line_data)

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }


class SaleOrderLineProfitability(models.Model):
    _name = 'bi_analysis.so_line_profit'

    so_id = fields.Many2one('bi_analysis.so_profitability', string='Sales Order')
    so_item_number = fields.Many2one('product.product', string='Item Number')
    so_item_number_id = fields.Char(string='Item Number')
    so_description = fields.Char(string='Description')
    so_ppu_st = fields.Float(string='Products per Assortment')
    so_assortment_order_qty = fields.Float(string='Assortment Order Qty')
    so_product_order_qty = fields.Float(string='Product Order Qty')
    so_product_sales_price = fields.Float(string='Product Sales Price')
    so_qty_invoice = fields.Float(string='Invoice Qty')
    so_assortment_sales_price = fields.Float(string='Assortment Sales Price')
    so_price_subtotal = fields.Float(string='Sub-Total')


class POLineProfitability(models.Model):
    _name = 'bi_analysis.po_line_profit'

    so_id = fields.Many2one('bi_analysis.so_profitability', string='Sales Order')
    po_name = fields.Char(string='Purchase Order Number')
    po_item_number = fields.Many2one('product.product', string='Item Number')
    po_item_number_id = fields.Char(string='Item Number')
    po_description = fields.Char(string='Description')
    po_partner_id = fields.Many2one('res.partner', string='Vendor')
    po_amount_total = fields.Float(string='Total')
    po_status = fields.Selection([
        ('hold', 'On Hold'),
        ('draft', 'Draft'),
        ('sent', 'Draft Sent'),
        ('to approve', 'To Approve'),
        ('purchase', 'Purchase Order'),
        ('finish', 'Done'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled')
    ], string='Status')


class CustInvoiceProfitability(models.Model):
    _name = 'bi_analysis.ci_profit'

    so_id = fields.Many2one('bi_analysis.so_profitability', string='Sales Order')
    ci_cust_invoice_id = fields.Many2one('account.invoice', string='Customer Invoice')
    ci_cust_invoice = fields.Char('Customer Invoice')
    ci_item_number = fields.Many2one('product.product', string='Item Number')
    ci_item_number_id = fields.Char(string='Item Number')
    ci_description = fields.Char(string='Description')
    ci_account = fields.Many2one('account.account', string='Account')
    ci_quantity = fields.Float(string='Quantity')
    ci_unit_price = fields.Float(string='Unit Price')
    ci_total_amount = fields.Float(string='Amount')


class VendorBillProfitability(models.Model):
    _name = 'bi_analysis.vb_profit'

    so_id = fields.Many2one('bi_analysis.so_profitability', string='Sales Order')
    vb_vendor_bill_id = fields.Many2one('account.invoice', string='Vendor Bill')
    vb_vendor_bill = fields.Char('Vendor Bill')
    vb_item_number = fields.Many2one('product.product', string='Item Number')
    vb_item_number_id = fields.Char(string='Item Number')
    vb_item_name = fields.Char(string='Product')
    vb_description = fields.Char(string='Description')
    vb_quantity = fields.Float(string='Quantity')
    vb_unit_price = fields.Float(string='Unit Price')
    vb_total_amount = fields.Float(string='Total Amount')


class SOProfitabilityCRONConfig(models.Model):
    _name = 'bi_analysis.so_cron_config'

    def _get_default_exec_date(self):
        config = self.env['bi_analysis.so_cron_config'].search([], order='id desc', limit=1)
        return config.first_exec_date if config.first_exec_date else False

    def _get_default_exec_time(self):
        config = self.env['bi_analysis.so_cron_config'].search([], order='id desc', limit=1)
        return config.first_exec_time if config.first_exec_time else False

    def _get_default_interval_type(self):
        config = self.env['bi_analysis.so_cron_config'].search([], order='id desc', limit=1)
        return config.interval_type if config.interval_type else False

    def _get_default_interval_number(self):
        config = self.env['bi_analysis.so_cron_config'].search([], order='id desc', limit=1)
        return config.number_of_interval if config.number_of_interval else False

    def _get_default_active(self):
        config = self.env['bi_analysis.so_cron_config'].search([], order='id desc', limit=1)
        return config.is_active if config.is_active else False

    def _get_default_si_sd(self):
        config = self.env['bi_analysis.so_cron_config'].search([], order='id desc', limit=1)
        return config.si_start_date if config.si_start_date else False

    def _get_default_si_ed(self):
        config = self.env['bi_analysis.so_cron_config'].search([], order='id desc', limit=1)
        return config.si_end_date if config.si_end_date else False

    def _get_default_exec_date(self):
        config = self.env['bi_analysis.so_cron_config'].search([], order='id desc', limit=1)
        return config.exec_date if config.exec_date else False

    first_exec_date = fields.Datetime(string='First Execution Date', default=_get_default_exec_date)
    first_exec_time = fields.Float(string='First Execution Time', default=_get_default_exec_time)
    exec_date = fields.Datetime(string='Scheduled Date and Time', default=_get_default_exec_date)
    interval_type = fields.Selection([
        ('days', 'Daily'),
        ('weeks', 'Weekly'),
        ('months', 'Monthly')
    ], string='Interval Type', default=_get_default_interval_type)
    number_of_interval = fields.Integer(string='Number of Interval', default=1)
    is_active = fields.Boolean(string='Active', default=_get_default_active)
    si_start_date = fields.Datetime(string='Start Date', default=_get_default_si_sd)
    si_end_date = fields.Datetime(string='End Date', default=_get_default_si_ed)

    @api.multi
    def execute(self):
        self.ensure_one()
        first_exec_date = False
        first_exec_time = False
        interval_type = False
        interval_number = False
        is_active = False

        for item in self:
            # base_date = item.first_exec_date.split(' ')
            # first_exec_date = base_date[0]
            # first_exec_time = str(timedelta(hours=item.first_exec_time))
            # exec_date = first_exec_date + ' ' + first_exec_time
            exec_date = item.exec_date
            interval_type = str(item.interval_type)
            is_active = item.is_active

            self._cr.execute("""UPDATE ir_cron SET nextcall = %s, interval_type = %s, active = %s 
                                WHERE name='Sale Order Data CRON Settings' AND model='bi_analysis.so_profitability'""",
                             (datetime.strptime(exec_date, '%Y-%m-%d %H:%M:%S'),
                              interval_type, is_active))
