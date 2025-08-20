odoo.define('web_project_gantt_view.GanttController', function (require) {
    "use strict";

    var AbstractController = require('web.AbstractController');
    var core = require('web.core');
    var config = require('web.config');
    var Dialog = require('web.Dialog');
    var dialogs = require('web.view_dialogs');
    var time = require('web.time');
    var session = require('web.session');

    var _t = core._t;
    var qweb = core.qweb;

    var n_direction = false;

    var GanttController = AbstractController.extend({

        custom_events: _.extend({}, AbstractController.prototype.custom_events, {
            task_update: '_onTaskUpdate',
            task_display: '_onTaskDisplay',
            task_create: '_onTaskCreate',
            crate_link: '_onCreateLink',
            delete_link: '_onDeleteLink',
        }),

        init: function (parent, model, renderer, params) {
            this._super.apply(this, arguments);
            this.set('title', params.displayName);
            this.context = params.context;
            this.displayName = params.displayName;
            this.dateStartField = params.dateStartField;
            this.dateStopField = params.dateStopField;
            this.linkModel = params.linkModel;
            // Store initial domain and context for filter persistence
            this.initialDomain = params.domain || [];
            this.initialContext = params.context || {};
            this._setScale('month');
            console.log('gant_controller init');

        },

        getTitle: function () {
            return this.get('title');
        },

        /**
         * Reload the view while preserving current filters (domain and context)
         * This prevents losing project/revision filters after saving tasks
         */
        _reloadWithFilters: function () {
            var self = this;
            var currentState = this.model.get();

            // Get the current domain and context from the model state
            var currentDomain = currentState.domain || this.initialDomain;
            var currentContext = currentState.context || this.initialContext;

            // Try to get search panel state if available
            if (this.searchPanel && this.searchPanel.getState) {
                var searchState = this.searchPanel.getState();
                console.log('Search panel state:', searchState);
            }

            // Get search model state if available
            if (this.searchModel && this.searchModel.get) {
                var searchQuery = this.searchModel.get('query');
                console.log('Search model query:', searchQuery);
            }

            // Force reload with current filters
            return this.reload({
                domain: currentDomain,
                context: currentContext,
                groupBy: currentState.groupedBy
            }).then(function () {
                console.log('Reload completed with filters preserved');
            });
        },

        renderButtons: function ($node) {
            var self = this;
            this.$buttons = $(qweb.render("WebGanttView.buttons", { 'isMobile': config.device.isMobile }));
            this.$buttons.on('click', '.gantt_task_row .gantt_task_cell', this._onCreateClick.bind(this));
            this.$buttons.on('click', '.o_gantt_scale_button', this._onScaleClick.bind(this));
            this.$buttons.on('click', '.o_gantt_new_button', this._onNewClick.bind(this));
            this.$buttons.on('click', '.o_gantt_today_button', this._onTodayClick.bind(this));
            this.$buttons.on('click', '.o_gantt_left_button', this._onPreviousClick.bind(this));
            this.$buttons.on('click', '.o_gantt_right_button', this._onNextClick.bind(this));
            this.$buttons.on('click', '.o_gantt_sort_button', this._onSortClick.bind(this));
            this.$buttons.on('click', '.o_gantt_export_pdf', this._onExportPDFClick.bind(this));
            this.$buttons.on('click', '.o_gantt_export_png', this._onExportPNGClick.bind(this));
            if ($node) {
                this.$buttons.appendTo($node);
            }
        },

        _onScaleClick: function (event) {
            var self = this;
            self.$buttons.find('.o_gantt_scale_dropdown_button').text($(this).text());
            self.$buttons.find('.o_gantt_scale_button').removeClass('active');
            var scale = $(event.target).data('value');
            self._updateButtons(scale);
            return self._setScale($(event.target).data('value'));
        },

        _updateButtons: function (scale) {
            var self = this;
            if (!self.$buttons) {
                return;
            }
            self.$buttons.find('.o_gantt_scale_button[data-value="' + scale + '"]').addClass('active');
        },

        _onTodayClick: function () {
            var self = this;
            self.model.setFocusDate(moment(new Date()));
            // Use _reloadWithFilters to preserve project/revision filters
            return self._reloadWithFilters();
        },

        _onPreviousClick: function () {
            var self = this;
            var state = self.model.get();
            self._setFocusDate(state.focus_date.subtract(1, state.scale));
        },
        _onNextClick: function () {
            var self = this;
            var state = self.model.get();
            self._setFocusDate(state.focus_date.add(1, state.scale));
        },

        _setScale: function (scale) {
            var self = this;
            console.log('setScale', scale);

            this.model.setScale(scale);
            self.set('title', self.displayName + ' (' + self.model.get().date_display + ')');
            // Use _reloadWithFilters to preserve project/revision filters
            this._reloadWithFilters();
        },

        _onCreateClick: function (event) {
            console.log('_onCreateClick', event);

            if (this.activeActions.create) {

                var context = _.clone(this.context);
                var id = event.target.parentElement.attributes.task_id.value;
                var task = gantt.getTask(id);
                var classDate = _.find(event.target.classList, function (e) {
                    return e.indexOf("date_") > -1;
                });

                var startDate = moment(new Date(parseInt(classDate.split("_")[1], 10))).utc();
                var endDate;
                switch (this.model.get().scale) {
                    case "day":
                        endDate = startDate.clone().add(4, "hour");
                        break;
                    case "week":
                        endDate = startDate.clone().add(2, "day");
                        break;
                    case "month":
                        endDate = startDate.clone().add(4, "day");
                        break;
                    case "year":
                        endDate = startDate.clone().add(2, "month");
                        break;
                }

                var get_create = function (item) {
                    if (item.create) {
                        context["default_" + item.create[0]] = item.create[1][0];
                    }
                    if (item.parent) {
                        var parent = gantt.getTask(item.parent);
                        get_create(parent);
                    }
                };
                get_create(task);

                context["default_" + this.dateStartField] = startDate.format("YYYY-MM-DD HH:mm:ss");
                if (this.dateStopField) {
                    context["default_" + this.dateStopField] = endDate.format("YYYY-MM-DD HH:mm:ss");
                }
                else {
                    context["default_" + this.model.mapping.date_delay] = gantt.calculateDuration(startDate, endDate);
                }

                context.id = 0;

                new dialogs.FormViewDialog(this, {
                    res_model: this.modelName,
                    context: context,
                    on_saved: this._reloadWithFilters.bind(this),
                }).open();
            }
        },

        _onTaskUpdate: function (event) {
            var taskObj = event.data.task;
            var success = event.data.success;
            var fail = event.data.fail;
            var fields = this.model.fields;

            if (fields[this.dateStopField] === undefined) {
                Dialog.alert(this, _t('You have no date_stop field defined!'));
                return fail();
            }

            if (fields[this.dateStartField].readonly || fields[this.dateStopField].readonly) {
                Dialog.alert(this, _t('You are trying to write on a read-only field!'));
                return fail();
            }

            var start = taskObj.start_date;
            var end = taskObj.end_date;

            var data = {};
            data[this.dateStartField] = time.auto_date_to_str(start, fields[this.dateStartField].type);
            if (this.dateStopField) {
                var field_type = fields[this.dateStopField].type;
                if (field_type === 'date') {
                    end.setTime(end.getTime() - 86400000);
                    data[this.dateStopField] = time.auto_date_to_str(end, field_type);
                    end.setTime(end.getTime() + 86400000);
                } else {
                    data[this.dateStopField] = time.auto_date_to_str(end, field_type);
                }
            }

            var taskId = parseInt(taskObj.id.split("gantt_task_").slice(1)[0], 10);

            this._rpc({
                model: this.model.modelName,
                method: 'write',
                args: [taskId, data],
            })
                .then(success, fail);
        },

        _onTaskCreate: function () {
            console.log('_createTask', _createTask);

            if (this.activeActions.create) {
                var startDate = moment(new Date()).utc();
                this._createTask(0, startDate);
            }
        },

        _onCreateLink: function (item) {
            var linkObj = item.data.link;
            var success = item.data.success;
            var fail = item.data.fail;

            var linkSourceId = parseInt(linkObj.source.split("gantt_task_").slice(1)[0], 10);
            var linkTargetId = parseInt(linkObj.target.split("gantt_task_").slice(1)[0], 10);
            var linkType = linkObj.type || 0;

            var args = [{
                'task_id': linkSourceId,
                'target_task_id': linkTargetId,
                'link_type': linkType,
            }];

            return this._rpc({
                model: this.linkModel,
                method: 'create',
                args: args,
            }).then(success, fail);
        },

        _onDeleteLink: function (item) {
            var linkObj = item.data.link;
            var success = item.data.success;
            var fail = item.data.fail;

            var Id = parseInt(linkObj.id.split("gantt_link_").slice(1)[0], 10);

            return this._rpc({
                model: this.linkModel,
                method: 'unlink',
                args: [Id],
            }).then(success, fail);
        },

        _onTaskDisplay: function (event) {
            var readonly = !this.activeActions.edit;
            this._displayTask(event.data, readonly);
        },

        _displayTask: function (task, readonly) {
            var taskId = _.isString(task.id) ? parseInt(_.last(task.id.split("_")), 10) : task.id;
            readonly = readonly ? readonly : false;
            new dialogs.FormViewDialog(this, {
                res_model: this.modelName,
                res_id: taskId,
                context: session.user_context,
                on_saved: this._reloadWithFilters.bind(this),
                readonly: readonly
            }).open();
        },

        _setFocusDate: function (focusDate) {
            var self = this;
            this.model.setFocusDate(focusDate);
            self.set('title', self.displayName + ' (' + self.model.get().date_display + ')');
            // Use _reloadWithFilters to preserve project/revision filters
            this._reloadWithFilters();
        },

        _onNewClick: function (event) {
            var context = _.clone(this.context);
            var startDate = moment(new Date()).utc();
            var endDate;
            switch (this.model.get().scale) {
                case "day":
                    endDate = startDate.clone().add(4, "hour");
                    break;
                case "week":
                    endDate = startDate.clone().add(2, "day");
                    break;
                case "month":
                    endDate = startDate.clone().add(4, "day");
                    break;
                case "year":
                    endDate = startDate.clone().add(2, "month");
                    break;
            }

            context["default_" + this.dateStartField] = startDate.format("YYYY-MM-DD HH:mm:ss");
            if (this.dateStopField) {
                context["default_" + this.dateStopField] = endDate.format("YYYY-MM-DD HH:mm:ss");
            }

            new dialogs.FormViewDialog(this, {
                res_model: this.modelName,
                context: context,
                on_saved: this.reload.bind(this),
            }).open();
        },

        _onSortClick: _.debounce(function (event) {
            event.preventDefault();
            if (n_direction) {
                gantt.sort("id", false);
            }
            else {
                gantt.sort("id", true);
            }
            n_direction = !n_direction;
        }, 200, true),

        _onExportPNGClick: _.debounce(function (event) {
            event.preventDefault();
            this._onExportOpen('png')
        }, 200, true),

        _onExportPDFClick: _.debounce(function (event) {
            event.preventDefault();
            this._onExportOpen('pdf')
        }, 200, true),

        _onExportOpen(format) {
            var self = this;
            var format = format;
            var $content = `<div class='form-group'>
                <label for='startDate'>Start Date</label>
                <input type='text' id="startDate" class='form-control'>
                </div>
                <div class='form-group'>
                <label for='endDate'>End Date</label>
                <input type='text' id="endDate" class='form-control'>
                </div>`;
            this.exportToDialog = new Dialog(this, {
                size: 'small',
                title: _t('Export PDF'),
                $content: $content,
                buttons: [
                    {
                        text: _t('Export'),
                        classes: 'btn-primary',
                        close: false,
                        click: function () {
                            var date_start = this.$el.find('#startDate');
                            var date_end = this.$el.find('#endDate');

                            if (!date_start.val()) {
                                date_start[0].style.borderColor = '#ff0000';
                                return;
                            } else {
                                date_start[0].style.borderColor = '#ced4da';
                            }
                            if (!date_end.val()) {
                                date_end[0].style.borderColor = '#ff0000';
                                return;
                            } else {
                                date_end[0].style.borderColor = '#ced4da';
                            }

                            if (Date.parse(date_start.val()) >= Date.parse(date_end.val())) {
                                self.displayNotification({ message: _t('Start date must be anterior to end date!'), type: 'warning' });
                                return;
                            }

                            if (format === 'pdf') {
                                gantt.exportToPDF({
                                    start: date_start.val(),
                                    end: date_end.val(),
                                });
                            } else if (format === 'png') {
                                gantt.exportToPNG({
                                    start: date_start.val(),
                                    end: date_end.val(),
                                });
                            } else {
                                self.displayNotification({ message: _t('The export format has not been specified!'), type: 'warning' });
                            }
                        }
                    },
                    {
                        text: _t('Discard'),
                        close: true
                    }
                ],
            });
            this.exportToDialog.opened().then(function () {
                self.exportToDialog.$("#startDate").datepicker({
                    dateFormat: 'dd-mm-yy',
                });
                self.exportToDialog.$("#endDate").datepicker({
                    dateFormat: 'dd-mm-yy',
                });
            });
            this.exportToDialog.open();
        }
    });
    return GanttController;
});
