odoo.define('gabmap.map2', function (require) {
"use strict";

var form_widget = require('web.form_widgets');
var core = require('web.core');
var _t = core._t;
var QWeb = core.qweb;

form_widget.WidgetButton.include({
    on_click: function() {
         if(this.node.attrs.custom === "click"){

            var lo = this.field_manager.get_field_value('longit');
            var la = this.field_manager.get_field_value('latit');
            var urls = (`maps.google.com/maps?q=${lo},${la}`)
            window.open('https://'+ urls)
         }
            return;
         }
         this._super();
    },
});
});