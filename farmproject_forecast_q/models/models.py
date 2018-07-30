# -*- coding: utf-8 -*-

from odoo import models, fields, api

class stockQuantInherit(models.Model):
	_inherit = 'stock.quant'

	unreserved_qty_on_hand = fields.Float(compute='_calculate_unreserved', string='Unreserved Quantity On Hand')
	forecasted_qty = fields.Float(compute='_calculate_forecasted_qty', string="Forecasted Quantity")


	@api.multi
	def _calculate_unreserved(self):
		for r in self:
			r.unreserved_qty_on_hand = r.quantity - r.reserved_quantity

	@api.multi
	def _calculate_forecasted_qty(self):
		for r in self:
			moves = r.env['stock.move.line'].search_read([
				('product_id', '=', r.product_id.id),
				('state', '!=', 'done'),
				('location_dest_id', '=', r.location_id.id)])
			for l in moves:
				r.forecasted_qty += l['product_qty']
			r.forecasted_qty += r.unreserved_qty_on_hand


class productTemplateInherit(models.Model):
	_inherit = 'product.template'

	stock_quants = fields.Many2many('stock.quant', 'Stock Quants', compute='_get_stock_quants')

	@api.multi
	def _get_stock_quants(self):
		self.stock_quants = self.product_variant_id.stock_quant_ids.search([
			('location_id.usage', '=', 'internal'),
			('product_id', '=', self.product_variant_id.id)])