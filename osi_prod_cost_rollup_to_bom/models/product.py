# Copyright (C) 2019, Open Source Integrators
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)


class ProductProduct(models.Model):
    _inherit = "product.product"

    std_cost_update_date = fields.Datetime(
        string="Standard Cost Update Date",
        copy=False,
        help="Last time the standard cost was performed on this product.",
    )

    def action_bom_cost(self):

        real_time_products = self.filtered(
            lambda p: p.valuation == "real_time" and p.valuation == "fifo"
        )
        if real_time_products:
            raise UserError(
                _(
                    "The costing method on some products %s is FIFO. The cost will be computed during manufacturing process. Use Standard Costing to update BOM cost manually."
                )
                % (real_time_products.mapped("display_name"))
            )

        else:
            boms_to_recompute = self.env["mrp.bom"].search(
                [
                    "|",
                    ("product_id", "in", self.ids),
                    "&",
                    ("product_id", "=", False),
                    ("product_tmpl_id", "in", self.mapped("product_tmpl_id").ids),
                ]
            )

            for product in self:
                account_id = (
                    product.property_account_expense_id.id
                    or product.categ_id.property_account_expense_categ_id.id
                )

                if product.cost_method == "standard":

                    if product.product_tmpl_id.product_variant_count == 1:
                        new_price = product._get_price_from_bom(boms_to_recompute)

                        if not float_is_zero(
                            new_price - product.standard_price, precision_rounding=2
                        ):
                            product.do_change_standard_price(new_price, account_id)
                            product.product_tmpl_id.std_cost_update_date = (
                                datetime.now()
                            )
                            _logger.info(
                                "Product : %s Standard Price: %s ",
                                product.default_code,
                                str(product.product_tmpl_id.standard_price),
                            )
                    else:
                        new_price = product._get_price_from_bom(boms_to_recompute)

                        if not float_is_zero(
                            new_price - product.standard_price, precision_rounding=2
                        ):
                            product.do_change_standard_price(new_price, account_id)
                            product.std_cost_update_date = datetime.now()
                            _logger.info(
                                "Product : %s Standard Price: %s ",
                                product.default_code,
                                str(product.standard_price),
                            )

    def _get_price_from_bom(self, boms_to_recompute=False):
        self.ensure_one()
        bom = self.env["mrp.bom"]._bom_find(product=self)
        # product has not changed
        return self.with_context(cost_all=True)._compute_bom_price(
            bom, boms_to_recompute=boms_to_recompute
        )

    def _compute_bom_price(self, bom, boms_to_recompute=False):
        self.ensure_one()
        if not boms_to_recompute:
            boms_to_recompute = []
        total = 0
        for opt in bom.operation_ids:
            duration_expected = (
                opt.workcenter_id.time_start
                + opt.workcenter_id.time_stop
                + opt.time_cycle
            )
            total += (duration_expected / 60) * opt.workcenter_id.costs_hour

        for line in bom.bom_line_ids:
            if line._skip_bom_line(self):
                continue

            # Compute recursive if line has `child_line_ids` and the product has not been computed recently
            if (
                line.child_bom_id
                and (
                    line.child_bom_id in boms_to_recompute
                    or self.env.context.get("cost_all", True)
                )
                and (
                    not bom.std_cost_update_date
                    or not line.product_id.std_cost_update_date
                    or line.child_bom_id._update_bom(bom.std_cost_update_date)
                )
            ):
                child_total = line.product_id._compute_bom_price(
                    line.child_bom_id, boms_to_recompute=boms_to_recompute
                )

                total += (
                    line.product_id.uom_id._compute_price(
                        child_total, line.product_uom_id
                    )
                    * line.product_qty
                )

                account_id = (
                    line.product_id.property_account_expense_id.id
                    or line.product_id.categ_id.property_account_expense_categ_id.id
                )

                if line.product_id.product_tmpl_id.product_variant_count == 1:
                    if not float_is_zero(
                        child_total - line.product_id.standard_price,
                        precision_rounding=2,
                    ):
                        line.product_id.do_change_standard_price(
                            child_total, account_id
                        )

                        line.product_id.product_tmpl_id.std_cost_update_date = (
                            datetime.now()
                        )
                        _logger.info(
                            "Product : %s Standard Price: %s ",
                            line.product_id.default_code,
                            str(line.product_id.product_tmpl_id.standard_price),
                        )
                else:
                    if not float_is_zero(
                        child_total - line.product_id.standard_price,
                        precision_rounding=2,
                    ):
                        line.product_id.do_change_standard_price(
                            child_total, account_id
                        )
                        line.product_id.std_cost_update_date = datetime.now()
                        _logger.info(
                            "Product : %s Standard Price: %s ",
                            line.product_id.default_code,
                            str(line.product_id.standard_price),
                        )
            else:
                ctotal = (
                    line.product_id.uom_id._compute_price(
                        line.product_id.standard_price, line.product_uom_id
                    )
                    * line.product_qty
                )

                total += ctotal
        bom.std_cost_update_date = datetime.now()
        return bom.product_uom_id._compute_price(total / bom.product_qty, self.uom_id)