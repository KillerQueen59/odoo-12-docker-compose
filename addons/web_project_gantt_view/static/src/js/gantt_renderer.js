odoo.define('web_project_gantt_view.GanttRenderer', function (require) {
    "use strict";
    
    var AbstractRenderer = require('web.AbstractRenderer');
    var core = require('web.core');
    var field_utils = require('web.field_utils');
    var time = require('web.time');
    
    var _lt = core._lt;

    var GanttRenderer = AbstractRenderer.extend({
        className: "o_gantt_view",

        init: function (parent, state, params) {
            this._super.apply(this, arguments);
            var self = this;
            var mapping = this.state.mapping;
            this.gantt_events = [];
            this.modelName = params.modelName;
            this.dateStartField = params.dateStartField;
            this.dateStopField = params.dateStopField;
            this.progressField = params.progressField;
            this.colorField = params.colorField;
            this.taskType = params.taskType;
            this.taskPriority = params.taskPriority;
            this.deadLine = params.deadLine;
            this.showLinks = params.showLinks;
            this.roundDndDates = params.roundDndDates;
        },
        
        _configGantt: function () {
            var self = this;          
            //Gantt Configurations
            gantt.config.autosize = "y";
            gantt.config.drag_links = self.showLinks === 'true' ?  true : false;
            gantt.config.drag_progress = false;
            gantt.config.drag_resize = true;
            gantt.config.grid_width = 350;
            gantt.config.row_height = 35;
            gantt.config.duration_unit = "day";
            gantt.config.initial_scroll = true;
            gantt.config.preserve_scroll = true;
            gantt.config.start_on_monday = moment().startOf("week").day();
            gantt.config.start_date = this.state.start_date;
            gantt.config.end_date = this.state.end_date;
            gantt.config.round_dnd_dates = !!this.roundDndDates;
            gantt.config.drag_move = this.edit ? JSON.parse(this.edit) : true;
            gantt.config.sort = true;
            gantt.config.work_time = true;
            gantt.config.skip_off_time = true;

            gantt.plugins({ 
                tooltip: true,
                fullscreen: true,
                marker: true,
                drag_timeline: true,
                fullscreen: true
            });

            gantt.config.columns = [    
                {
                    name: "text",
                    label: _lt("Gantt View"),
                    tree: true,
                    width: "*",
                    resize: true,
                    template: function(task) {
                        var html = '';
                        if (task.deadline) {
                            var deadline = new Date(task.deadline);
                            if (deadline && task.end_date > deadline) {
                                html += '<div class="deadline_alert fa fa-exclamation-triangle"></div>';
                            }
                        }
                        if ((Math.round(task.progress * 100) == 100)) {
                            html += "<div class='progress_alert fa fa-check'></div>";
                        }
                        return html + task.text;
                    },
                },   
                {
                    name: "duration", 
                    label: _lt("Duration(d)"),
                    align: "center", 
                    width: 80, 
                },                                             
            ];
        
            gantt.templates.grid_indent = function () {
                return "<div class='gantt_tree_indent' style='width:20px;'></div>";
            };

            gantt.templates.task_class = function (start, end, task) {
                var classes = ["o_gantt_color" + task.color + "_0"];               
                if (task.is_group) {
                    classes.push("has_child");
                } else {
                    classes.push("is_leaf");
                }
                return classes.join(" ");
            };

            gantt.templates.task_row_class = function (start, end, task) {
                var classes = ["level_" + task.$level];
                return classes;
            };

            gantt.templates.timeline_cell_class = function (item, date) {
                var classes = "date_" + date.getTime();
                var today = new Date();
                if (self.state.scale !== "year" && (date.getDay() === 0 || date.getDay() === 6)) {
                    classes += " weekend_task";
                }
                if (self.state.scale !== "day" && date.getDate() === today.getDate() && date.getMonth() === today.getMonth() && date.getYear() === today.getYear()) {
                    classes += " today";
                }
                return classes;
            };     

            gantt.templates.task_text = function (start, end, task) {                      
                return task.text  + "<span style='text-align:left;'> (" + Math.round(task.progress * 100) + "%)</span>";
            };

            gantt.templates.tooltip_text = function(start,end,task){            
                return "<b>Task:</b> "+task.text+"<br/>" + 
                    "<b>Start date:</b>" + gantt.templates.tooltip_date_format(start) + 
                    "<br/><b>End date:</b> "+gantt.templates.tooltip_date_format(end) +
                    "<br/><b>Progress:</b> "+ (Math.round(task.progress * 100)) + "%";
            };
            
            gantt.templates.grid_folder = function(item) {
                return "<div class='gantt_tree_icon gantt_folder_" +
                (item.$open ? "open" : "closed") + "'></div>";
            };
    
            gantt.templates.grid_file = function(task) {
                var html = '';
                if (!task.is_group){
                    if (task.priority === 'high') {
                        html += "<div class='gantt_tree_icon gantt_file priority_high'></div>";
                    }
                    else if(task.priority === 'low'){
                        html += "<div class='gantt_tree_icon gantt_file priority_low'></div>";
                    }
                    else{
                        html += "<div class='gantt_tree_icon gantt_file priority_normal'></div>";
                    }                           
                }
                return html;
            };

            gantt.templates.link_class = function (link) {
                var types = gantt.config.links;
                switch (link.type) {
                    case types.finish_to_start:
                        return "finish_to_start";
                        break;
                    case types.start_to_start:
                        return "start_to_start";
                        break;
                    case types.finish_to_finish:
                        return "finish_to_finish";
                        break;
                }
            };

            gantt.templates.rightside_text = function (start, end, task) {
                if (task.deadline) {
                    if (end.valueOf() > new Date(task.deadline).valueOf()) {
                        var endTime = Math.abs(( new Date(end).getTime() ));
                        var deadLine = Math.abs(( new Date(task.deadline).getTime() ));
                        var overdue = Math.ceil((endTime - deadLine) / (24 * 60 * 60 * 1000));
                        var text = "<b>Overdue: " + overdue + " days</b>";
                        return text;
                    }                   
                }                
            };
        },

        _setScaleConfig: function (value) {            
            gantt.config.min_column_width = 48;
            gantt.config.scale_height = 48;
            gantt.config.step = 1;
                                
            switch (value) {
                case "day":                    
                    gantt.config.scale_unit = "day";
                    gantt.config.date_scale = "%d %M";
                    gantt.templates.scale_cell_class = getcss;
                    gantt.config.subscales = [{unit:"hour", step:1, date:"%H h"}];
                    gantt.config.scale_height = 27;
                    break;
                case "week":
                    var weekScaleTemplate = function (date){
                        var dateToStr = gantt.date.date_to_str("%d %M %Y");
                        var endDate = gantt.date.add(gantt.date.add(date, 1, "week"), -1, "day");
                        return dateToStr(date) + " - " + dateToStr(endDate);
                    };
                    gantt.config.scale_unit = "week";
                    gantt.templates.date_scale = weekScaleTemplate;
                    gantt.config.subscales = [{unit:"day", step:1, date:"%d, %D", css:getcss}];
                    break;
                case "month":
                    gantt.config.scale_unit = "month";
                    gantt.config.date_scale = "%F, %Y";
                    gantt.config.subscales = [{unit:"day", step:1, date:"%d", css:getcss}];
                    gantt.config.min_column_width = 25;
                    break;
                case "year":
                    gantt.config.scale_unit = "year";
                    gantt.config.date_scale = "%Y";
                    gantt.config.subscales = [{unit:"month", step:1, date:"%M"}];
                    break;
            }
            function getcss(date) {
                var today = new Date();
                if(date.getDay() === 0 || date.getDay() === 6){
                    return "weekend_scale";
                }
                if(date.getMonth() === today.getMonth() && date.getDate() === today.getDate()){
                    return "today";
                } 
            }
        },

        _render: function () {            
            this._configGantt();
            this._renderGantt();
            return $.when();
        },
        on_attach_callback: function() {
            this._super();
            if(!this.events_set){
                var self = this;
                this._configureGanttEvents();
                this.events_set = true;
            }
            this._renderGantt();
        },

        _renderGantt: function () {
            var self = this;
            
            var mapping = this.state.mapping;
            var grouped_by = this.state.groupedBy;
            
            var links = _.compact(_.map(this.state.link, function (link) {
                link = _.clone(link);
                return link;            
            }));

            var tasks = _.compact(_.map(this.state.data, function (task) {
                task = _.clone(task);

                var task_start;
                if (task[self.dateStartField]) {
                    task_start = time.auto_str_to_date(task[self.dateStartField]);
                }                
                else{
                    return false;
                }
                task.task_start = task_start;
                
                var task_stop;
                if (task[self.dateStopField]) {
                    task_stop = time.auto_str_to_date(task[self.dateStopField]);
                    if (self.state.fields[self.dateStopField].type === 'datetime' || self.state.fields[self.dateStopField].type === 'date') {
                        task_stop.setTime(task_stop.getTime() + 86400000);
                    }
                    if (!task_stop) {
                        task_stop = moment(task_start).clone().add(1, 'hours').toDate();
                    }
                }
                task.task_stop = task_stop;

                var percent;
                if (_.isNumber(task[self.progressField])) {
                    percent = task[self.progressField] || 0;
                } 
                else {
                    percent = 0;
                }
                task.percent = percent;
    
                
                if (self.min_date && task_stop < new Date(self.min_date)) {
                    return false;
                }
    
                var color;
                if (task[self.colorField]) {
                    if (task[self.colorField] == '1'){
                        color = '#F06050';
                    }
                    if (task[self.colorField] == '2'){
                        color = '#F4A460';
                    }
                    if (task[self.colorField] == '3'){
                        color = '#F7CD1F';
                    }
                    if (task[self.colorField] == '4'){
                        color = '#6CC1ED';
                    }
                    if (task[self.colorField] == '5'){
                        color = '#814968';
                    }
                    if (task[self.colorField] == '6'){
                        color = '#EB7E7F';
                    }
                    if (task[self.colorField] == '7'){
                        color = '#2C8397';
                    }
                    if (task[self.colorField] == '8'){
                        color = '#475577';
                    }
                    if (task[self.colorField] == '9'){
                        color = '#D6145F';
                    }
                    if (task[self.colorField] == '10'){
                        color = '#30C381';
                    }
                    if (task[self.colorField] == '11'){
                        color = '#9365B8';
                    }
                }else{
                    color = "#7C7BAD";
                }
                task.color = color;
    
                var type;
                if (task[self.taskType]) {
                    type = task[self.taskType];
                }else{
                    type = 'task';
                }
                task.type = type;

                var deadline;
                if (task[self.deadLine]) {
                    deadline = task[self.deadLine];
                }
                task.deadline = deadline;

                
                var priority;
                if (task[self.taskPriority]) {
                    priority = task[self.taskPriority];
                }
                task.priority = priority;
    
                return task;
            }));
    

            var split_groups = function (tasks, grouped_by) {
                if (grouped_by.length === 0) {
                    return tasks;
                }
                
                var groups = [];
                _.each(tasks, function (task) {
                    var group_name = task[_.first(grouped_by)];                    
                    var group = _.find(groups, function (group) {
                        return _.isEqual(group.name, group_name);
                    });

                    if (group === undefined) {
                        group = {
                            name:group_name, 
                            tasks: [], 
                            __is_group: true,
                            group_start: false, 
                            group_stop: false, 
                            percent: [],
                            open: true
                        };
                        group.create = [_.first(grouped_by), task[_.first(grouped_by)]];
                        groups.push(group);
                    }
                    if (!group.group_start || group.group_start > task.task_start) {
                        group.group_start = task.task_start;
                    }
                    if (!group.group_stop || group.group_stop < task.task_stop) {
                        group.group_stop = task.task_stop;
                    }
                    group.percent.push(task.percent);
                    group.tasks.push(task);
                });
                _.each(groups, function (group) {
                    group.tasks = split_groups(group.tasks, _.rest(grouped_by));
                });
                return groups;
            };
            var groups = split_groups(tasks, grouped_by);
    
            if (groups.length === 0) {
                groups = [{
                    'id': 0,
                    'display_name': '',
                    'task_start': this.state.focus_date.toDate(),
                    'task_stop': this.state.focus_date.toDate(),
                    'percent': 0,
                }];
            }

            var gantt_tasks = [];
            var gantt_tasks_data = []
            var gantt_tasks_links = []
    
            var build_tasks = function (task, level, parent_id) {
                if ((task.__is_group && !task.group_start) || (!task.__is_group && !task.task_start)) {
                    return;
                }

                if (task.__is_group) {
                    if (level > 0 && task.tasks.length === 0){
                        return;
                    }
                    var project_id = _.uniqueId("gantt_project_");
                    var field = self.state.fields[grouped_by[level]];

                    var group_name = task[mapping.name] ? field_utils.format[field.type](task[mapping.name], field) : "-";
                    
                    var sum = _.reduce(task.percent, function (acc, num) { return acc+num; }, 0);
                    var progress = sum / task.percent.length / 100 || 0;
                    
                    var t = {
                        'id': project_id,
                        'text': group_name,
                        'is_group': true,
                        'start_date': task.group_start,
                        'duration': gantt.calculateDuration(task.group_start, task.group_stop),
                        'progress': progress,
                        'create': task.create,
                        'open': true,
                        'index': gantt_tasks_data.length,
                        'color': '#f4f7f4',
                        'textColor': '#000000'
                    };
                    
                    if (parent_id) { 
                        t.parent = parent_id; 
                    }
                    gantt_tasks_data.push(t);
                    
                    _.each(task.tasks, function (subtask) {
                        build_tasks(subtask, level+1, project_id);
                    });
                }
                else {
                    var parent;
                    if (task.parent_id){
                        parent = "gantt_task_" + task.parent_id[0];
                    }else{
                        parent = parent_id;
                    }
                    gantt_tasks_data.push({
                        'id': "gantt_task_" + task.id,
                        'text': task.display_name || '',
                        'active': task.active || true,
                        'start_date': task.task_start,
                        'end_date': task.task_stop,
                        'progress': task.percent / 100,
                        'parent': parent,
                        'open': true,
                        'color': task.color || 0,
                        'index': gantt_tasks.length,
                        'type':task.type,
                        'rollup': true,
                        'deadline': task.deadline,
                        'priority': task.priority,                        
                    });
                }
            };
            gantt_tasks['data'] = gantt_tasks_data;            
            
            _.each(groups, function (group) {
                build_tasks(group, 0); 
            });
            
            var build_links = function (link) {
                if (link){
                    gantt_tasks_links.push({
                        'id': "gantt_link_" + link.id, 
                        'source': "gantt_task_" + link.source,
                        'target': "gantt_task_" + link.target, 
                        'type': link.type,
                    });
                }
            };

            gantt_tasks['links'] = gantt_tasks_links;
            if (self.showLinks === 'true'){
                _.each(links, function (link) {
                    build_links(link); 
                });
            }

            this._renderGanttData(gantt_tasks);
            this._configureGanttEvents(tasks, grouped_by, gantt_tasks);
        },

        _renderGanttData: function (gantt_tasks) {            
            var self = this;            
            var container_height = $('.o_main_navbar').height() + $('.o_control_panel').height() + 80;
            this.$el.get(0).style.minHeight = (window.outerHeight - container_height) + "px";
          
            while (this.gantt_events.length) {
                gantt.detachEvent(this.gantt_events.pop());
            }
            this._setScaleConfig(this.state.scale);            

            gantt.init(this.$el.get(0));
            gantt.clearAll();
            
            gantt.showDate(this.state.focus_date);
            gantt.parse(gantt_tasks);
            
            var dateToStr = gantt.date.date_to_str(gantt.config.task_date);
            var markerId = gantt.addMarker({  
                start_date: new Date(), 
                css: "today", 
                text: "Now", 
                title: dateToStr(new Date()) 
            }); 

            var scroll_state = gantt.getScrollState();
            gantt.scrollTo(scroll_state.x, scroll_state.y);
        },
        
        _configureGanttEvents: function (tasks, grouped_by, groups) {
            var self = this;
            
            this.gantt_events.push(gantt.attachEvent("onTaskClick", function (id, e) {                    
                if(gantt.getTask(id).is_group) {
                    return true;
                }
                if (id.indexOf("unused") >= 0) {
                    var task = gantt.getTask(id);
                    var key = "default_"+task.create[0];
                    var context = {};
                    context[key] = task.create[1][0];
                    self.trigger_up('task_create', context);
                } 
				else {
                    self.trigger_up('task_display', gantt.getTask(id));
                }
                return true;
            }));
    
            this.gantt_events.push(gantt.attachEvent("onTaskDblClick", function (){ 
                return false; 
            }));
            
            this.gantt_events.push(gantt.attachEvent("onBeforeTaskSelected", function (id) {
                if(gantt.getTask(id).is_group){   
                    if($("[task_id="+id+"] .gantt_tree_icon")){
                        $("[task_id="+id+"] .gantt_tree_icon").click();
                        return false;
                    }                                        
                }
                return true;
            }));

            var parent_date_update = function (id) {
                var start_date, stop_date;
                var clicked_task = gantt.getTask(id);
                
                if (!clicked_task.parent) {
                    return;
                }
    
                var parent = gantt.getTask(clicked_task.parent);
    
                _.each(gantt.getChildren(parent.id), function (task_id){
                    var task_start_date = gantt.getTask(task_id).start_date;
                    var task_stop_date = gantt.getTask(task_id).end_date;
                    if(!start_date){
                        start_date = task_start_date;
                    }
                    if(!stop_date){
                        stop_date = task_stop_date;
                    }
                    if(start_date > task_start_date){
                        start_date = task_start_date;
                    }
                    if(stop_date < task_stop_date){
                        stop_date = task_stop_date;
                    }
                });

                parent.start_date = start_date;
                parent.end_date = stop_date;
                gantt.updateTask(parent.id);
                if (parent.parent) parent_date_update(parent.id);
            };
            
            this.gantt_events.push(gantt.attachEvent("onBeforeTaskDrag", function (id, mode, e){
                var task = gantt.getTask(id);
                task._start_date_original = task.start_date;
                task._end_date_original = task.end_date;
                this.lastX = e.pageX;
                
                if (task.is_group) {
                    var attr = e.target.attributes.getNamedItem("consolidation_ids");
                    if (attr) {
                        var children = attr.value.split(" ");
                        this.drag_child = children;
                        _.each(this.drag_child, function (child_id) {
                            var child = gantt.getTask(child_id);
                            child._start_date_original = child.start_date;
                            child._end_date_original = child.end_date;
                        });
                    }
                }
                return true;
            }));
            
            this.gantt_events.push(gantt.attachEvent("onTaskDrag", function (id, mode, task, original, e){
                if(gantt.getTask(id).is_group){
                    var day;                                                        
                    if (self.state.scale === "year") {
                        day = 51840000;
                    }
                    if (self.state.scale === "month") {
                        day = 3456000;
                    }
                    if (self.state.scale === "week") {
                        day = 1728000;
                    }
                    if (self.state.scale === "day") {
                        day = 72000;
                    }
                    
                    var diff = (e.pageX - this.lastX) * day;
                    this.lastX = e.pageX;
    
                    if (task.start_date > original.start_date){ 
                        task.start_date = original.start_date; 
                    }
                    if (task.end_date < original.end_date){ 
                        task.end_date = original.end_date; 
                    }
    
                    if (this.drag_child){
                        _.each(this.drag_child, function (child_id){
                            var child = gantt.getTask(child_id);
                            var new_start = +child.start_date + diff;
                            var new_stop = +child.end_date + diff;
                            if (new_start < gantt.config.start_date || new_stop > gantt.config.end_date){
                                return false;
                            }
                            child.start_date = new Date(new_start);
                            child.end_date = new Date(new_stop);
                            gantt.updateTask(child.id);
                            parent_date_update(child_id);
                        });
                    }
                    gantt.updateTask(task.id);
                    return false;
                }
                parent_date_update(id);
                return true;
            }));
    
            this.gantt_events.push(gantt.attachEvent("onAfterTaskDrag", function (id){
                var update_task = function (task_id) {
                    var task = gantt.getTask(task_id);
                    self.trigger_up('task_update', {
                        task: task,
                        success: function () {
                            parent_date_update(task_id);
                        },
                        fail: function () {
                            task.start_date = task._start_date_original;
                            task.end_date = task._end_date_original;
                            gantt.updateTask(task_id);
                            delete task._start_date_original;
                            delete task._end_date_original;
                            parent_date_update(task_id);
                        }});
                };
    
                if (gantt.getTask(id).is_group && this.drag_child) {
                    _.each(this.drag_child, function (child_id) {
                        update_task(child_id);
                    });
                }
                update_task(id);
            }));
                       
            this.gantt_events.push(gantt.attachEvent("onAfterLinkAdd", function(id,item){                
                var crate_link = function (item) {
                    self.trigger_up('crate_link', {
                        link: item,
                        success: function (newID) {
                            if (newID){
                                var newID = "gantt_task_" + newID;
                                gantt.changeLinkId(item.id, newID);
                            }                            
                        },
                        fail: function () {},
                    });
                };
                crate_link(item);
            }));  

            this.gantt_events.push(gantt.attachEvent("onAfterLinkDelete", function(id,item){
                var delete_link = function (item) {
                    self.trigger_up('delete_link', {
                        link: item,
                        success: function (delete_links) {

                        },
                        fail: function () {

                        }
                    });
                };
                delete_link(item);
            }));  
			
			this.gantt_events.push(gantt.attachEvent("onBeforeLinkAdd", function(id,item){
				var sourceTask = gantt.getTask(item.source);
                var targetTask = gantt.getTask(item.target);
				if (sourceTask.is_group) {
                    gantt.message({type:"error", text:"You can't create link task with group."});
					return false;
				}
                if(sourceTask.parent != targetTask.parent){
                    gantt.message({type:"error", text:"You can't create link with other project task / parent task."});
                    return false;
                }
				return true;
			}));            
        },

        destroy: function () {
            while (this.gantt_events.length) {
                gantt.detachEvent(this.gantt_events.pop());
            }
            this._super();
        },
    });
    return GanttRenderer;
});
