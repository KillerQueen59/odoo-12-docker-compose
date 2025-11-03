odoo.define('rnet_project_management.import_wizard', function (require) {
"use strict";

var AbstractAction = require('web.AbstractAction');
var core = require('web.core');

/**
 * Client action to show notification, close wizard, and reload parent view
 */
var ImportCompleteAction = AbstractAction.extend({
    start: function () {
        var self = this;
        var params = this.action_manager.action_stack[this.action_manager.action_stack.length - 1].params;

        // Show notification
        if (params && params.notification) {
            this.do_notify(
                params.notification.title || 'Success',
                params.notification.message || 'Operation completed',
                params.notification.sticky || false,
                params.notification.type || 'success'
            );
        }

        // Close the dialog/wizard
        this.do_action({'type': 'ir.actions.act_window_close'});

        // Reload the parent view
        if (this.action_manager && this.action_manager.inner_action) {
            var controller = this.action_manager.inner_action.controller;
            if (controller && controller.reload) {
                controller.reload();
            }
        }

        return this._super.apply(this, arguments);
    },
});

core.action_registry.add('import_complete_action', ImportCompleteAction);

return ImportCompleteAction;
});
