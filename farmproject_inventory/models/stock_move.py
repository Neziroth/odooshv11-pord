# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models
from odoo.tools.float_utils import float_is_zero, float_compare
from odoo.addons import decimal_precision as dp


class StockMove(models.Model):
    _inherit = "stock.move"

    purchase_uom = fields.Many2one(comodel_name="product.uom", compute='_compute_product_uom', string="Unit of Measure")
    product_uom_po_qty = fields.Float(string="Initial Demand", compute="_compute_product_uom_po_qty", digits=dp.get_precision('Product Unit of Measure'), inverse="_product_uom_qty_set")
    po_qty_done = fields.Float(compute="_quantity_done_compute", string="Done", inverse="_po_qty_done_set", digits=dp.get_precision('Product Unit of Measure'))

    @api.depends('picking_code')
    def _compute_product_uom(self):
        for move in self:
            move.purchase_uom = move.product_id.uom_po_id if move.picking_code == 'incoming' else move.product_id.uom_id

    @api.multi
    def _compute_product_uom_po_qty(self):
        for move in self:
            move.product_uom_po_qty = move.product_uom._compute_quantity(move.product_uom_qty, move.product_id.uom_po_id, rounding_method='HALF-UP') if move.picking_code == 'incoming' else move.product_uom_qty

    def _product_uom_qty_set(self):
        for move in self:
            if move.product_uom_po_qty:
                move.product_uom_qty = move.purchase_uom._compute_quantity(move.product_uom_po_qty, move.product_uom, rounding_method='HALF-UP')

    def _prepare_move_line_vals(self, quantity=None, reserved_quant=None):
        vals = super(StockMove, self)._prepare_move_line_vals(quantity=quantity, reserved_quant=reserved_quant)
        if quantity and self.picking_code == 'incoming':
            uom_po_quantity = self.product_id.uom_id._compute_quantity(quantity, self.purchase_uom, rounding_method='HALF-UP')
            uom_quantity_back_to_product_uom = self.purchase_uom._compute_quantity(uom_po_quantity, self.product_id.uom_id, rounding_method='HALF-UP')
            rounding = self.env['decimal.precision'].precision_get('Product Unit of Measure')
            if float_compare(quantity, uom_quantity_back_to_product_uom, precision_digits=rounding) == 0:
                vals = dict(vals, product_uom_qty=uom_po_quantity, product_uom_id=self.purchase_uom.id)
            else:
                vals = dict(vals, product_uom_qty=quantity, product_uom_id=self.purchase_uom.id)
        return vals

    @api.depends('move_line_ids.qty_done', 'move_line_ids.product_uom_id', 'move_line_nosuggest_ids.qty_done')
    def _quantity_done_compute(self):
        """ This field represents the sum of the move lines `qty_done`. It allows the user to know
        if there is still work to do.

        We take care of rounding this value at the general decimal precision and not the rounding
        of the move's UOM to make sure this value is really close to the real sum, because this
        field will be used in `_action_done` in order to know if the move will need a backorder or
        an extra move.
        """
        for move in self:
            quantity_done = qty_po_done = 0
            for move_line in move._get_move_lines():
                quantity_done += move_line.product_uom_id._compute_quantity(move_line.qty_done, move.product_uom, round=False)
                qty_po_done += move_line.product_uom_id._compute_quantity(move_line.qty_done, move.purchase_uom, round=False)
            move.quantity_done = quantity_done
            move.po_qty_done = qty_po_done

    def _po_qty_done_set(self):
        self[0].quantity_done = self[0].po_qty_done
        self._quantity_done_set()

    @api.model
    def _run_fifo(self, move, quantity=None):
        """ Value `move` according to the FIFO rule, meaning we consume the
        oldest receipt first. Candidates receipts are marked consumed or free
        thanks to their `remaining_qty` and `remaining_value` fields.
        By definition, `move` should be an outgoing stock move.

        :param quantity: quantity to value instead of `move.product_qty`
        :returns: valued amount in absolute
        """
        move.ensure_one()

        # Deal with possible move lines that do not impact the valuation.
        valued_move_lines = move.move_line_ids.filtered(lambda ml: ml.location_id._should_be_valued() and not ml.location_dest_id._should_be_valued() and not ml.owner_id)
        valued_quantity = 0
        for valued_move_line in valued_move_lines:
            valued_quantity += valued_move_line.product_uom_id._compute_quantity(valued_move_line.qty_done, move.product_id.uom_id)

        # Find back incoming stock moves (called candidates here) to value this move.
        qty_to_take_on_candidates = quantity or valued_quantity
        candidates = move.product_id._get_fifo_candidates_in_move()
        new_standard_price = 0
        tmp_value = 0  # to accumulate the value taken on the candidates
        for candidate in candidates:
            new_standard_price = candidate.price_unit
            if candidate.remaining_qty <= qty_to_take_on_candidates:
                qty_taken_on_candidate = candidate.remaining_qty
            else:
                qty_taken_on_candidate = qty_to_take_on_candidates

            # As applying a landed cost do not update the unit price, naivelly doing
            # something like qty_taken_on_candidate * candidate.price_unit won't make
            # the additional value brought by the landed cost go away.
            candidate_price_unit = candidate.remaining_value / candidate.remaining_qty
            value_taken_on_candidate = qty_taken_on_candidate * candidate_price_unit
            candidate_vals = {
                'remaining_qty': candidate.remaining_qty - qty_taken_on_candidate,
                'remaining_value': candidate.remaining_value - value_taken_on_candidate,
            }
            candidate.write(candidate_vals)

            qty_to_take_on_candidates -= qty_taken_on_candidate
            tmp_value += value_taken_on_candidate
            if qty_to_take_on_candidates == 0:
                break

        # Update the standard price with the price of the last used candidate, if any.
        if new_standard_price and move.product_id.cost_method == 'fifo':
            move.product_id.sudo().standard_price = new_standard_price

        # If there's still quantity to value but we're out of candidates, we fall in the
        # negative stock use case. We chose to value the out move at the price of the
        # last out and a correction entry will be made once `_fifo_vacuum` is called.
        if qty_to_take_on_candidates == 0:
            move.write({
                'value': -tmp_value if not quantity else move.value or -tmp_value,  # outgoing move are valued negatively
                'price_unit': -tmp_value / move.product_qty if move.product_qty != 0.0 else 1.0, # move.product_qty cannot be 0.0, only line changed in whole method.
            })
        elif qty_to_take_on_candidates > 0:
            last_fifo_price = new_standard_price or move.product_id.standard_price
            negative_stock_value = last_fifo_price * -qty_to_take_on_candidates
            tmp_value += abs(negative_stock_value)
            vals = {
                'remaining_qty': move.remaining_qty + -qty_to_take_on_candidates,
                'remaining_value': move.remaining_value + negative_stock_value,
                'value': -tmp_value,
                'price_unit': -1 * last_fifo_price,
            }
            move.write(vals)
        return tmp_value
