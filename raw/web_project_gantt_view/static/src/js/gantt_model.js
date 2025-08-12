odoo.define('web_project_gantt_view.GanttModel', function (require) {
"use strict";

var AbstractModel = require('web.AbstractModel');
var core = require('web.core');
var fieldUtils = require('web.field_utils');
var session = require('web.session');

var _t = core._t;

var  GanttModel = AbstractModel.extend({

    init: function () {
        this._super.apply(this, arguments);
        this.gantt = null;
    },

    get: function () {
        return _.extend({}, this.gantt);
    },

    load: function (params) {        
        this.modelName = params.modelName;
        this.mapping = params.mapping;
        this.fields = params.fields;
        this.domain = params.domain;
        
        this.dateStartField = params.dateStartField;
        this.dateStopField = params.dateStopField;
        this.progressField = params.progressField;
        this.colorField = params.colorField;
        this.taskType = params.taskType;
        this.deadLine = params.deadLine;
        this.showLinks = params.showLinks;

        this.defaultGroupBy = params.defaultGroupBy ? [params.defaultGroupBy] : [];
        var groupedBy = params.groupedBy;
        if (!groupedBy || !groupedBy.length) {
            groupedBy = this.defaultGroupBy;
        }
        groupedBy = this._dateFilterInGroupedBy(groupedBy);

        
        this.gantt = {
            fields: this.fields,
            mapping: this.mapping,
            
            dateStartField: params.dateStartField,
            dateStopField: params.dateStopField,

            groupedBy: groupedBy,
            domain: params.domain || [],
            context: params.context || {},
        };
        this._setFocusDate(params.initialDate, params.scale);
        return this._fetchData().then(function () {
            return Promise.resolve();
        });
    },

    reload: function (handle, params) {
        if (params.domain) {
            this.gantt.domain = params.domain;
        }
        if (params.context) {
            this.gantt.context = params.context;
        }

        if (params.domain) {
            this.domain = params.domain;
        }

        this.defaultGroupBy = params.defaultGroupBy ? [params.defaultGroupBy] : [];
        if (params.groupBy) {
            if (params.groupBy && params.groupBy.length) {
                this.gantt.groupedBy = this._dateFilterInGroupedBy(params.groupBy);
                if (this.gantt.groupedBy.length !== params.groupBy.length) {
                    this.do_warn(false, _t('Grouping by date is not supported'));
                }
            } else {
                this.gantt.groupedBy = this.defaultGroupBy;
            }
        }
        return this._fetchData();
    },

    _dateFilterInGroupedBy(groupedBy) {
        var self = this;
        return groupedBy.filter(function(groupedByField)
            {
                var fieldName = groupedByField.split(':')[0];
                return fieldName in self.fields && self.fields[fieldName].type.indexOf('date') === -1;
            }
        );
    },

    setFocusDate: function (focusDate) {
        this._setFocusDate(focusDate, this.gantt.scale);
    },

    setScale: function (scale) {
        this._setFocusDate(this.gantt.focus_date, scale);
    },

    _getDomain: function () {
        var gannt_start_date = this.gantt.start_date.locale('en').format("YYYY-MM-DD");
        var gannt_to_date = this.gantt.to_date.locale('en').format("YYYY-MM-DD");
        
        var domain = [
            [this.dateStartField, '<', gannt_to_date]
        ];
        if (this.fields[this.dateStopField]) {
             domain = domain.concat([
                '|',
                [this.dateStartField, ">", gannt_start_date],
                [this.dateStopField, '=', false]
            ]);
        }
        return this.domain.concat(domain);
    },
    
    _getFields: function () {
        var self = this;
        var fields = _.values(this.mapping).concat(this.gantt.groupedBy);
        fields.push('display_name',this.gantt.dateStartField, this.gantt.dateStopField);

        if (this.progressField) {
            fields.push(this.progressField);
        }

        if (this.colorField) {
            fields.push(this.colorField);
        }

        if (this.taskType) {
            fields.push(this.taskType);
        }
        
        if (this.deadLine) {
            fields.push(this.deadLine);
        }

        return _.uniq(fields);
    },

    _fetchData: function () {
        var self = this;
        var domain = self._getDomain();   
        var promise =  new Promise(function (resolve, reject) {
            var defs = [
                self._rpc({
                    model: self.modelName,
                    method: 'search_read',  
                    context: self.gantt.context,
                    domain: self.gantt.domain.concat(domain),
                    fields: _.uniq(self.fields),
                })
            ];
            if (self.showLinks === 'true'){
                defs.push(
                    self._rpc({
                        model: self.modelName,
                        method: 'search_read_links',
                        args: [self.gantt.domain.concat(domain)], 
                        context: self.gantt.context,
                    })
                );
            }
            Promise.all(defs).then(function (records) {
                self.gantt.data = records[0];
                
                var start_min_date = new Date(Math.min.apply(null, self.gantt.data.map(function(e) {
                    return new Date(e[self.dateStartField]);                
                })));
                if (start_min_date.valueOf()){
                    gantt.config.start_date = moment(start_min_date);
                }
                
                if (self.showLinks === 'true'){           
                    self.gantt.link = records[1];
                }
                resolve();                
            });
        });
        return promise;
    },

    _setFocusDate: function (focusDate, scale) {
        this.gantt.scale = scale;
        this.gantt.focus_date = focusDate;

        this.gantt.start_date = focusDate.clone().subtract(1, scale).startOf(scale);
        this.gantt.to_date = focusDate.clone().add(3, scale).endOf(scale);

        this.gantt.end_date = this.gantt.to_date.add(1, scale);
        this.gantt.date_display = this._dateReformat(focusDate, scale);
    },

    _dateReformat: function (date, scale) {
        switch(scale) {                                    
            case "year":
                return date.format("YYYY");
            case "month":
                return date.format("MMMM YYYY");
            case "week":
                var date_start = date.clone().startOf("week").format("D MMM");
                var date_end = date.clone().endOf("week").format("D MMM");
                return date_start + " - " + date_end;
            case "day":
                return date.format("D MMM");
        }
    },

});
return GanttModel;
});
