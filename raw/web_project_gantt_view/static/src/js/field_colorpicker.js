odoo.define('web_project_gantt_view.FieldColorPicker', function (require) {
    "use strict";
    
    var basic_fields = require('web.basic_fields');
    var FieldInteger = basic_fields.FieldInteger;
    var field_registry = require('web.field_registry');
    
    var core = require('web.core');
    var QWeb = core.qweb;
    
    var FieldColorPicker = FieldInteger.extend({

        init: function () {
            this._super.apply(this, arguments);
            this.tagName = 'div';
        },

        _renderEdit: function () {
            this.$el.html(QWeb.render('web_project_gantt_view.ColorPicker'));
            this._onColorPickerSetup();
            this._onSelectedColorHighlight();
        },

        _renderReadonly: function () {
            this.$el.html(QWeb.render('web_project_gantt_view.ColorPickerReadonly', {active_color: this.value,}));
            this.$el.on('click', 'a', function(ev){ ev.preventDefault(); });
        },

        _onColorPickerSetup: function () {
            var $picker = this.$('ul');
            if (!$picker.length) {
                return;
            }
            $picker.html(QWeb.render('KanbanColorPicker'));
            $picker.on('click', 'a', this._onColorChanged.bind(this));
        },

        _getValue: function (){
            return this.value;
        },

        _onColorChanged: function(ev) {
            ev.preventDefault();
            var color = null;
            if(ev.currentTarget && ev.currentTarget.dataset && ev.currentTarget.dataset.color){
                color = ev.currentTarget.dataset.color;
            }
            if(color){
                this.value = color;
                this._onChange();
                this._renderEdit();
            }
        },

        _onSelectedColorHighlight: function(){
            try{
                $(this.$('li')[parseInt(this.value)]).css('border', '2px solid teal');
            }
            catch(err) {
    
            }
        },
    });
    
    field_registry.add('color_picker', FieldColorPicker);
    
    return FieldColorPicker;
    
    });
