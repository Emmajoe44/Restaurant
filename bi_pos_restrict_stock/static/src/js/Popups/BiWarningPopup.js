odoo.define('bi_pos_restrict_stock.BiWarningPopup', function(require) {
	'use strict';

	const PosComponent = require('point_of_sale.PosComponent');
	const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
	const Registries = require('point_of_sale.Registries');
    let pos_model = require('point_of_sale.models');

	class BiWarningPopup extends AbstractAwaitablePopup {
	    constructor() {
            super(...arguments);
        }

        order(){
            var self = this;
            var order = self.env.pos.get_order();
            order.add_product(self.props.product);
            self.trigger('close-popup');
            self.showScreen('ProductScreen');
        }
	}

	BiWarningPopup.template = 'BiWarningPopup';
	Registries.Component.add(BiWarningPopup);
	return BiWarningPopup;
});
