odoo.define('gabzilmap.map', function (require) {
"use strict";

var form_widget = require('web.form_widgets');
var core = require('web.core');
var _t = core._t;
var QWeb = core.qweb;

form_widget.WidgetButton.include({
    on_click: function() {
         if(this.node.attrs.custom === "click"){
            alert("Hello! This is an Alert For Gabzil");
            //window.open('https://www.google.com/maps/@18.5138317,73.8625551,2995m/data=!3m1!1e3')
         }
         this._super();
    },
});
});