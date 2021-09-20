odoo.define('bi_analysis.alter_create', function (require) {
    var FormView = require('web.FormView');
    var core = require('web.core');
    var Column = core.list_widget_registry.get('field');
    var Model = require('web.DataModel');
    var session = require('web.session');
    var ListView = require('web.ListView');
    var data = require('web.data');
    var QWeb = core.qweb;

    ListView.include({
        render_buttons: function() {
            this._super.apply(this, arguments);
            if(this.dataset.model == 'bi_analysis.so_profitability') {
                var create_btn = this.$buttons.find('.o_list_button_add')
                var import_btn = this.$buttons.find('.o_button_import')
                create_btn.hide();
                import_btn.hide();
            }
            if(this.dataset.model == 'bi_analysis.customer_profitability') {
                var create_btn = this.$buttons.find('.o_list_button_add');
                create_btn.hide();
            }
            if (this.$buttons){
                var btn = this.$buttons.find('button.bi_analysis_so_update')
                btn.on('click', this.proxy('bi_analysis_cp_create'))
            }
        },
        bi_analysis_cp_create: function() {
            var self = this
            var context = this.dataset._model;
            new Model('bi_analysis.so_profitability.create')
                .call('display_wizard', [], {context: context})
                .then(function(response) {
                    self.do_action(response);
                });
        }
    });
});