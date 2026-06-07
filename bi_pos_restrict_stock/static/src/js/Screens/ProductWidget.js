odoo.define('bi_pos_restrict_stock.ProductsWidget', function(require) {
	"use strict";


	const Registries = require('point_of_sale.Registries');
	const ProductsWidget = require('point_of_sale.ProductsWidget');
	var models = require('point_of_sale.models');

	const BiProductsWidget = (ProductsWidget) =>
		class extends ProductsWidget {
			constructor() {
				super(...arguments);
			}

			get productsToDisplay() {
			    let self = this;
				let prods = super.productsToDisplay;
				let order = self.env.pos.get_order();
                let locations = self.env.pos.locations;
                if(self.env.pos.config.pos_stock_type == 'onhand'){
                    $.each(prods, function( i, prd ){
                        prd['qty_available'] = 0;
                        let loc_onhand = JSON.parse(prd.quant_text);
                        _.each(locations,function(location){
                            $.each(loc_onhand, function( k, v ){
                                if(location.id == k){
                                    prd['qty_available'] = prd['qty_available'] + v[0];
                                }
                            })
                        })
                        if(prd['bi_on_hand'] > 0){
                            prd['bi_on_hand'] = order.get_display_product_qty(prd)
                            prd['qty_available'] = prd['qty_available'] - prd['bi_on_hand']
                        }
                        else{
                            var reserved_qty = order.get_display_product_qty(prd);
                            prd['qty_available'] = prd['qty_available'] - reserved_qty;
                        }
                    });
                }else if(self.env.pos.config.pos_stock_type == 'virtual'){
                    $.each(prods, function( i, prd ){
                        let loc_available = JSON.parse(prd.quant_text);
                        prd['virtual_available'] = 0;
                        let total = 0;
                        let out = 0;
                        let inc = 0;
                        _.each(locations,function(location){
                            $.each(loc_available, function( k, v ){
                                if(location.id == k){
                                    total += v[0];
                                    if(v[1]){
                                        out += v[1];
                                    }
                                    if(v[2]){
                                        inc += v[2];
                                    }
                                    let final_data = (total + inc) - out
                                    prd['virtual_available'] = final_data;
                                }
                            })
                        })
                        if(prd['bi_on_virtual']>0){
                            prd['bi_on_virtual'] = order.get_display_product_qty(prd);
                            prd['virtual_available'] = prd['virtual_available'] - prd['bi_on_virtual']
                        }
                        else{
                            var reserved_qty = order.get_display_product_qty(prd);
                            prd['virtual_available'] = prd['virtual_available'] - reserved_qty;
                        }
                    });
                }
                if (this.searchWord !== '') {
                    return this.env.pos.db.search_product_in_category(
                        this.selectedCategoryId,
                        this.searchWord
                    );
                } else {
                    return this.env.pos.db.get_product_by_category(this.selectedCategoryId);
                }
            }
        };

	Registries.Component.extend(ProductsWidget, BiProductsWidget);

	return ProductsWidget;

});
