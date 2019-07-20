# -*- coding: utf-8 -*-
# Copyright (C) 2019 - TODAY, Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _


class SaleSubscription(models.Model):
    _inherit = 'sale.subscription'

    brand_id = fields.Many2one('res.partner', string='Brand',
                               domain="[('type', '=', 'brand')]")

    def _prepare_invoice_data(self):
        res = super()._prepare_invoice_data()
        if self.brand_id:
            res.update({'brand_id': self.brand_id.id})
        return res

