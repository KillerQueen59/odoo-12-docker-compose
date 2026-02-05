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
        // Access params from the action object directly (Odoo 12 compatible)
        var params = (this.action && this.action.params) || {};

        // Show notification
        if (params && params.notification) {
            this.do_notify(
                params.notification.title || 'Success',
                params.notification.message || 'Operation completed',
                params.notification.sticky || false,
                params.notification.type || 'success'
            );
        }

        // Close the wizard dialog - use history_back to return to previous view
        this.trigger_up('history_back');

        return this._super.apply(this, arguments);
    },
});

core.action_registry.add('import_complete_action', ImportCompleteAction);

return ImportCompleteAction;
});
