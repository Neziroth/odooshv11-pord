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
