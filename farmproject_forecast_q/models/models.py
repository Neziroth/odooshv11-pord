# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime


class StockByLocation(models.TransientModel):
	_name = 'stock.by.location'

	location_id = fields.Many2one('stock.location', 'Location')
	product_id = fields.Many2one('product.product', 'Product')

	incoming_qty = fields.Float(string="Incoming")
	on_hand_qty = fields.Float(string="On Hand")

	forecasted_qty = fields.Float(string="Forecasted")
	reserved_qty = fields.Float(string="Reserved")
	unreserved_qty_on_hand = fields.Float(string="Unreserved On Hand")

	@api.multi
	def recalculate_stock_by_location(self):
		[r.unlink() for r in self.env['stock.by.location'].search([])]
		stock_locs = self.env['stock.location'].search([('usage','=','internal')])
		for loc in stock_locs:
			#get unfinished stock move lines that are coming from the location
			#moves_out = self.env['stock.move.line'].search([('location_id','=',loc),('state','!=','done')])

			#get unfinished stock move lines that are going into the location
			moves_in = self.env['stock.move.line'].search([('location_dest_id','=',loc.id),('state','!=','done')])
			for m in moves_in:
				temp = self.env['stock.by.location'].search([('product_id','=',m.product_id.id),('location_id','=',loc.id)])
				if not temp:
					temp = self.env['stock.by.location'].create({'location_id': loc.id, 'product_id': m.product_id.id})
				temp.update_quantities(inc=m.ordered_qty)

			#get all stock quants currently at the location
			quants = self.env['stock.quant'].search([('location_id','=',loc.id)])
			for q in quants:
				#try to find existing model
				temp = self.env['stock.by.location'].search([('product_id','=',q.product_id.id),('location_id','=',loc.id)])
				#create new instance of model
				if not temp:
					temp = self.env['stock.by.location'].create({'location_id': loc.id, 'product_id': q.product_id.id})
				temp.update_quantities(res=q.reserved_quantity,onhand=q.quantity)

		return self.env.ref('farmproject_forecast_q.x_stock_by_location').read()[0]

	@api.multi
	def update_quantities(self, inc=0, res=0, onhand=0, reset=False):
		if not reset:
			self.incoming_qty += inc
			self.reserved_qty += res
			self.on_hand_qty += onhand
		elif reset:
			self.incoming_qty = inc
			self.reserved_qty = res
			self.on_hand_qty = onhand
		self.forecasted_qty = self.on_hand_qty + self.incoming_qty - self.reserved_qty
		self.unreserved_qty_on_hand = self.on_hand_qty - self.reserved_qty

	@api.multi
	def unlink(self):
		super(StockByLocation, self).unlink()
