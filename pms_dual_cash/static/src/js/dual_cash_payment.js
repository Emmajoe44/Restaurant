odoo.define('pms_dual_cash.dual_cash_payment', function (require) {
    'use strict';

    const Registries = require('point_of_sale.Registries');

    const DualCashPaymentScreen = (PaymentScreen) =>
        class extends PaymentScreen {
            constructor() {
                super(...arguments);
                this._allPaymentMethods = this.env.pos.payment_methods.filter((method) =>
                    this.env.pos.config.payment_method_ids.includes(method.id)
                );
                this._updatePaymentMethodsForCurrentOrder();
            }

            _pricelistCurrencyId(order) {
                if (!order || !order.pricelist || !order.pricelist.currency_id) {
                    return null;
                }
                return order.pricelist.currency_id[0];
            }

            _cashMethodMatchesPricelist(method, plCurrencyId) {
                if (!method.is_cash_count) {
                    return true;
                }
                if (method.currency_id && method.currency_id[0] === plCurrencyId) {
                    return true;
                }
                const cur = this.env.pos.currencies.find((c) => c.id === plCurrencyId);
                const code = cur ? cur.name : '';
                if (code === 'SSP' && method.name.indexOf('SSP') !== -1) {
                    return true;
                }
                if (code === 'USD' && method.name.indexOf('USD') !== -1) {
                    return true;
                }
                return false;
            }

            _updatePaymentMethodsForCurrentOrder() {
                const order = this.currentOrder;
                if (!order || !this.env.pos.config.use_pricelist) {
                    this.payment_methods_from_config = this._allPaymentMethods;
                    return;
                }
                const plCurrencyId = this._pricelistCurrencyId(order);
                const filtered = this._allPaymentMethods.filter((method) =>
                    this._cashMethodMatchesPricelist(method, plCurrencyId)
                );
                const hasCash = filtered.some((m) => m.is_cash_count);
                this.payment_methods_from_config =
                    hasCash || !this._allPaymentMethods.some((m) => m.is_cash_count)
                        ? filtered
                        : this._allPaymentMethods;
            }

            _cashPaymentMethodForOrder(order, paymentMethod) {
                if (!paymentMethod || !paymentMethod.is_cash_count) {
                    return paymentMethod;
                }
                const plCurrencyId = this._pricelistCurrencyId(order);
                const match = this.env.pos.payment_methods.find((pm) =>
                    this._cashMethodMatchesPricelist(pm, plCurrencyId)
                );
                return match || paymentMethod;
            }

            async _onNewOrder(newOrder) {
                this._updatePaymentMethodsForCurrentOrder();
                if (newOrder && this.env.pos._syncCurrencyFromSelectedOrder) {
                    this.env.pos._syncCurrencyFromSelectedOrder();
                }
                return super._onNewOrder(...arguments);
            }

            async mounted() {
                this._updatePaymentMethodsForCurrentOrder();
                if (super.mounted) {
                    await super.mounted();
                }
            }

            addNewPaymentLine({detail: paymentMethod}) {
                this._updatePaymentMethodsForCurrentOrder();
                return super.addNewPaymentLine(...arguments);
            }

            async validateOrder(isForceValidate) {
                const order = this.currentOrder;
                if (order) {
                    for (const line of order.get_paymentlines()) {
                        const pm = line.payment_method;
                        const correct = this._cashPaymentMethodForOrder(order, pm);
                        if (correct && pm.id !== correct.id) {
                            line.payment_method = correct;
                        }
                    }
                }
                return super.validateOrder(isForceValidate);
            }
        };

    const PaymentScreen = Registries.Component.get('PaymentScreen');
    Registries.Component.extend(PaymentScreen, DualCashPaymentScreen);
});
