odoo.define('bi_pos_restrict_stock.Chrome', function(require) {
	'use strict';

	const Chrome = require('point_of_sale.Chrome');
	const Registries = require('point_of_sale.Registries');
	var models = require('point_of_sale.models');

	const BiPosChrome = (Chrome) =>
		class extends Chrome {
			mounted(){
			    let self = this;
                self.env.services.bus_service.updateOption('pos.sync.stock',self.env.session.uid);
				self.env.services.bus_service.onNotification(self,self._onProductNotification);
				self.env.services.bus_service.startPolling();
			}
			_onProductNotification(notifications){
				let self = this;
				_.each(notifications,function(not){
					let prod_data = JSON.parse(not[1].prod_data);
					let prod_id = JSON.parse(not[1].id);
					let product = self.env.pos.db.get_product_by_id(prod_id);
					product.pos = self.env.pos;
					if(self.env.pos.db.product_by_id[product.id]){
						$.each(prod_data, function( key, val ){
							if (key == 'quant_text') {
								let data = JSON.parse(val)
								$.each(data, function( i, j ){
									product['quant_text'] = val;
								})
							}
						})
						self.env.pos.db.product_by_id[product.id] = new models.Product({}, product);
					}
				})
			}
		};

	Registries.Component.extend(Chrome, BiPosChrome);

	return Chrome;
});
