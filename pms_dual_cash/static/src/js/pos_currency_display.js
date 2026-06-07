odoo.define('pms_dual_cash.pos_currency_display', function (require) {
    'use strict';

    const PaymentScreen = require('point_of_sale.PaymentScreen');
    const PaymentScreenPaymentLines = require('point_of_sale.PaymentScreenPaymentLines');
    const PaymentScreenStatus = require('point_of_sale.PaymentScreenStatus');
    const Registries = require('point_of_sale.Registries');

    function syncOrderCurrency(pos) {
        if (pos && pos._syncCurrencyFromSelectedOrder) {
            pos._syncCurrencyFromSelectedOrder();
        }
    }

    const DualCashPaymentScreen = (Component) =>
        class extends Component {
            async mounted() {
                syncOrderCurrency(this.env.pos);
                return super.mounted(...arguments);
            }
            async _onNewOrder(newOrder) {
                syncOrderCurrency(this.env.pos);
                return super._onNewOrder(...arguments);
            }
            addNewPaymentLine() {
                syncOrderCurrency(this.env.pos);
                return super.addNewPaymentLine(...arguments);
            }
            _updateSelectedPaymentline() {
                syncOrderCurrency(this.env.pos);
                return super._updateSelectedPaymentline(...arguments);
            }
        };

    const DualCashPaymentLines = (Component) =>
        class extends Component {
            formatLineAmount(paymentline) {
                syncOrderCurrency(this.env.pos);
                return this.env.pos.format_currency(paymentline.get_amount());
            }
        };

    const DualCashPaymentStatus = (Component) =>
        class extends Component {
            get changeText() {
                syncOrderCurrency(this.env.pos);
                return super.changeText;
            }
            get totalDueText() {
                syncOrderCurrency(this.env.pos);
                return super.totalDueText;
            }
            get remainingText() {
                syncOrderCurrency(this.env.pos);
                return super.remainingText;
            }
        };

    Registries.Component.extend(PaymentScreen, DualCashPaymentScreen);
    Registries.Component.extend(PaymentScreenPaymentLines, DualCashPaymentLines);
    Registries.Component.extend(PaymentScreenStatus, DualCashPaymentStatus);
});
