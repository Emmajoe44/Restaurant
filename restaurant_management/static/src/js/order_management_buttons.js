odoo.define('restaurant_management.order_management_buttons', function (require) {
    'use strict';

    const { useListener } = require('web.custom_hooks');
    const { useContext } = owl.hooks;
    const PosComponent = require('point_of_sale.PosComponent');
    const OrderManagementScreen = require('point_of_sale.OrderManagementScreen');
    const Registries = require('point_of_sale.Registries');
    const contexts = require('point_of_sale.PosContext');
    const models = require('point_of_sale.models');

    function getSelectedOrder(component) {
        return component.orderManagementContext.selectedOrder;
    }

    function canManageOrder(component) {
        const order = getSelectedOrder(component);
        return (
            order &&
            order.locked &&
            order.backendId &&
            component.env.pos.config.manage_orders
        );
    }

    async function loadServerOrderIntoPos(component, method, orderId) {
        const payloads = await component.rpc({
            model: 'pos.order',
            method: method,
            args: [[orderId]],
            kwargs: { context: component.env.session.user_context },
        });
        if (!payloads || !payloads.length) {
            return;
        }
        const json = payloads[0];
        const order = new models.Order({}, { pos: component.env.pos, json: json });
        component.env.pos.add_order(order);
        component.env.pos.set_order(order);
        if (order.pricelist && order.set_pricelist) {
            order.set_pricelist(order.pricelist);
        }
        component.showScreen('ProductScreen');
    }

    class RefundOrderButton extends PosComponent {
        constructor() {
            super(...arguments);
            useListener('click', this._onClick);
            this.orderManagementContext = useContext(contexts.orderManagement);
        }
        get isHighlighted() {
            return canManageOrder(this);
        }
        async _onClick() {
            const order = getSelectedOrder(this);
            if (!canManageOrder(this)) {
                return;
            }
            const { confirmed } = await this.showPopup('ConfirmPopup', {
                title: this.env._t('Refund order'),
                body: this.env._t(
                    'Create a refund for this order in the current session?'
                ),
            });
            if (!confirmed) {
                return;
            }
            try {
                await loadServerOrderIntoPos(
                    this,
                    'refund_to_pos_session',
                    order.backendId
                );
            } catch (error) {
                const msg =
                    (error.data && error.data.message) ||
                    error.message ||
                    String(error);
                await this.showPopup('ErrorPopup', {
                    title: this.env._t('Refund failed'),
                    body: msg,
                });
            }
        }
    }
    RefundOrderButton.template = 'RefundOrderButton';

    class ExchangeOrderButton extends PosComponent {
        constructor() {
            super(...arguments);
            useListener('click', this._onClick);
            this.orderManagementContext = useContext(contexts.orderManagement);
        }
        get isHighlighted() {
            return canManageOrder(this);
        }
        async _onClick() {
            const order = getSelectedOrder(this);
            if (!canManageOrder(this)) {
                return;
            }
            const { confirmed } = await this.showPopup('ConfirmPopup', {
                title: this.env._t('Exchange order'),
                body: this.env._t(
                    'Open a new order with the same items for exchange?'
                ),
            });
            if (!confirmed) {
                return;
            }
            try {
                await loadServerOrderIntoPos(
                    this,
                    'exchange_to_pos_session',
                    order.backendId
                );
            } catch (error) {
                const msg =
                    (error.data && error.data.message) ||
                    error.message ||
                    String(error);
                await this.showPopup('ErrorPopup', {
                    title: this.env._t('Exchange failed'),
                    body: msg,
                });
            }
        }
    }
    ExchangeOrderButton.template = 'ExchangeOrderButton';

    OrderManagementScreen.addControlButton({
        component: RefundOrderButton,
        condition: function () {
            return this.env.pos.config.manage_orders;
        },
    });
    OrderManagementScreen.addControlButton({
        component: ExchangeOrderButton,
        condition: function () {
            return this.env.pos.config.manage_orders;
        },
    });

    Registries.Component.add(RefundOrderButton);
    Registries.Component.add(ExchangeOrderButton);
});
