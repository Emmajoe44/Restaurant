odoo.define('bi_pos_restrict_stock.models', function(require) {
	"use strict";

	var models = require('point_of_sale.models');

	models.load_fields('product.product', ['type','virtual_available','qty_available','incoming_qty','outgoing_qty','quant_ids','quant_text']);

    models.load_models({
		model: 'stock.location',
		fields: [],
		loaded: function(self, locations){
			self.locations = locations;
		},
	});

    let OrderSuper = models.Order.prototype;
	models.Order = models.Order.extend({

	    get_display_product_qty: function(prd){
            var self = this;
            var products = {};
            var order = this.pos.get_order();
            var display_qty = 0;
            if(order){
                var orderlines = order.get_orderlines();
                if(orderlines.length > 0){
                    orderlines.forEach(function (line) {
                        if(line.product['id'] == prd.id){
                            display_qty += line.get_quantity()
                        }
                    });
                }
            }
            return display_qty
        },
	});

});
