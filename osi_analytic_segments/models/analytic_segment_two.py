# Copyright (C) 2019 Open Source Integrators
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).
from odoo import api, fields, models
from odoo.osv import expression


class AnalyticSegmentTwo(models.Model):
    _name = "analytic.segment.two"
    _description = "Analytic Segment Two"
    _order = "name,code"

    code = fields.Char()
    name = fields.Char()
    description = fields.Text()

    def name_get(self):
        result = []
        for segment in self:
            name = "[{}] {}".format(segment.code, segment.name)
            result.append((segment.id, name))
        return result

    @api.model
    def name_search(self, name, args=None, operator="ilike", limit=100):
        args = args or []
        domain = []
        if name:
            domain = ["|", ("code", "=ilike", name + "%"), ("name", operator, name)]
            if operator in expression.NEGATIVE_TERM_OPERATORS:
                domain = ["&", "!"] + domain[1:]
        segments = self.search(domain + args, limit=limit)
        return segments.name_get()
