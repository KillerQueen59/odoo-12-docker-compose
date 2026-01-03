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
            gantt.config.drag_links = self.showLinks === 'true' ? true : false;
            gantt.config.show_links = self.showLinks === 'true' ? true : false; // Enable link display
            gantt.config.drag_progress = false;
            gantt.config.drag_resize = true;
            gantt.config.grid_width = 350;
            gantt.config.row_height = 50;
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
                drag_timeline: true
            });

            // Disable built-in click handlers to prevent double modals
            gantt.config.details_on_click = false;
            gantt.config.details_on_dblclick = false;

            // Always show actual functionality - no toggle option
            gantt.config.show_actual = true;

            // Enable critical path functionality
            gantt.config.highlight_critical_path = false;

            gantt.config.columns = [
                {
                    name: "wbs",
                    label: _lt("WBS"),
                    width: 60,
                    align: "center",
                    template: function(obj) {
                        return obj.wbs_code || "";
                    },
                    tree: false
                },
                {
                    name: "text",
                    label: _lt("Gantt View"),
                    tree: true,
                    width: "*",
                    resize: true,
                    template: function (task) {
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
                // Add baseline and delay classes
                if (task.has_actual) {
                    classes.push("has_actual");
                }
                if (task.is_delayed) {
                    classes.push("is_delayed");
                }
                // Hide actual task bar if no actual dates are provided OR if task has children (parent tasks)
                if (!task.has_actual || task.$has_child) {
                    classes.push("hide_actual_bar");
                }
                // Add critical path class if enabled
                if (gantt.config.highlight_critical_path && gantt.isCriticalTask && gantt.isCriticalTask(task)) {
                    classes.push('gantt_critical_task');
                }
                return classes.join(" ");
            };

            gantt.templates.task_row_class = function (start, end, task) {
                var classes = ["level_" + task.$level, "gantt_task_row_with_custom_bar"];
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
                return task.text + "<span style='text-align:left;'> (" + Math.round(task.progress * 100) + "%)</span>";
            };

            gantt.templates.tooltip_text = function (start, end, task) {
                var tooltip = "<b>Task:</b> " + task.text + "<br/>";

                // Safe date formatting with null checks
                if (start) {
                    tooltip += "<b>Start date:</b> " + gantt.templates.tooltip_date_format(start) + "<br/>";
                } else {
                    tooltip += "<b>Start date:</b> Not set<br/>";
                }

                if (end) {
                    tooltip += "<b>End date:</b> " + gantt.templates.tooltip_date_format(end) + "<br/>";
                } else {
                    tooltip += "<b>End date:</b> Not set<br/>";
                }

                tooltip += "<b>Progress:</b> " + (Math.round(task.progress * 100)) + "%";

                // Add baseline information if available
                if (task.has_actual && task.actual_start_date && task.actual_end_date) {
                    tooltip += "<div class='gantt_tooltip_baseline'>";
                    tooltip += "<b>Actual:</b><br/>";

                    var actualStart = new Date(task.actual_start_date);
                    var actualEnd = new Date(task.actual_end_date);

                    if (!isNaN(actualStart.getTime())) {
                        tooltip += "Start: " + gantt.templates.tooltip_date_format(actualStart) + "<br/>";
                    }
                    if (!isNaN(actualEnd.getTime())) {
                        tooltip += "End: " + gantt.templates.tooltip_date_format(actualEnd);
                    }

                    if (task.is_delayed && end && !isNaN(actualEnd.getTime())) {
                        var delayDays = Math.ceil((end - actualEnd) / (1000 * 60 * 60 * 24));
                        tooltip += "<br/><span class='gantt_tooltip_delay'>Delayed by " + delayDays + " days</span>";
                    }
                    tooltip += "</div>";
                }

                return tooltip;
            };

            gantt.templates.grid_folder = function (item) {
                return "<div class='gantt_tree_icon gantt_folder_" +
                    (item.$open ? "open" : "closed") + "'></div>";
            };

            gantt.templates.grid_file = function (task) {
                var html = '';
                if (!task.is_group) {
                    if (task.priority === 'high') {
                        html += "<div class='gantt_tree_icon gantt_file priority_high'></div>";
                    }
                    else if (task.priority === 'low') {
                        html += "<div class='gantt_tree_icon gantt_file priority_low'></div>";
                    }
                    else {
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
                        var endTime = Math.abs((new Date(end).getTime()));
                        var deadLine = Math.abs((new Date(task.deadline).getTime()));
                        var overdue = Math.ceil((endTime - deadLine) / (24 * 60 * 60 * 1000));
                        var text = "<b>Overdue: " + overdue + " days</b>";
                        return text;
                    }
                }
                return "";
            };

            // Add custom template for additional bar/text below task
            gantt.templates.task_bottom_text = function (start, end, task) {
                return "Test";
            };

            // Override the task rendering to add custom element below
            gantt.attachEvent("onTaskCreated", function (task) {
                return true;
            });

            // Custom task rendering to add bottom bar integrated with the task
            gantt.attachEvent("onGanttRender", function () {
                setTimeout(function () {
                    var taskRows = document.querySelectorAll('.gantt_task_row');
                    taskRows.forEach(function (taskRow) {
                        if (!taskRow.querySelector('.custom_task_bottom_bar')) {
                            var taskLine = taskRow.querySelector('.gantt_task_line');
                            if (taskLine) {
                                // Create a wrapper for the task content
                                var taskWrapper = document.createElement('div');
                                taskWrapper.className = 'gantt_task_wrapper';

                                // Move the existing task line into the wrapper
                                var taskLineClone = taskLine.cloneNode(true);
                                taskRow.removeChild(taskLine);
                                taskWrapper.appendChild(taskLineClone);

                                // Create the custom bottom bar
                                var customBar = document.createElement('div');
                                customBar.className = 'custom_task_bottom_bar';
                                customBar.innerHTML = 'Test';
                                taskWrapper.appendChild(customBar);

                                // Add the wrapper back to the task row
                                taskRow.appendChild(taskWrapper);

                            }
                        }
                    });
                }, 100);
                return true;
            });
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
                    gantt.config.subscales = [{ unit: "hour", step: 1, date: "%H h" }];
                    gantt.config.scale_height = 27;
                    break;
                case "week":
                    var weekScaleTemplate = function (date) {
                        var dateToStr = gantt.date.date_to_str("%d %M %Y");
                        var endDate = gantt.date.add(gantt.date.add(date, 1, "week"), -1, "day");
                        return dateToStr(date) + " - " + dateToStr(endDate);
                    };
                    gantt.config.scale_unit = "week";
                    gantt.templates.date_scale = weekScaleTemplate;
                    gantt.config.subscales = [{ unit: "day", step: 1, date: "%d, %D", css: getcss }];
                    break;
                case "month":
                    gantt.config.scale_unit = "month";
                    gantt.config.date_scale = "%F, %Y";
                    gantt.config.subscales = [{ unit: "day", step: 1, date: "%d", css: getcss }];
                    gantt.config.min_column_width = 25;
                    break;
                case "year":
                    gantt.config.scale_unit = "year";
                    gantt.config.date_scale = "%Y";
                    gantt.config.subscales = [{ unit: "month", step: 1, date: "%M" }];
                    break;
            }
            function getcss(date) {
                var today = new Date();
                if (date.getDay() === 0 || date.getDay() === 6) {
                    return "weekend_scale";
                }
                if (date.getMonth() === today.getMonth() && date.getDate() === today.getDate()) {
                    return "today";
                }
            }
        },

        _render: function () {
            this._configGantt();
            this._setupActualRendering();
            // Only render if data is available
            if (this.state && this.state.data) {
                this._renderGantt();
            } else {
            }
            return $.when();
        },
        on_attach_callback: function () {
            // Only render if data is available
            if (this.state && this.state.data) {
                this._renderGantt();
                this._configureGanttEvents(this.state.data, this.state.grouped_by, this.state.groups);
            } this._setupActualRendering();
        },

        _setupActualRendering: function () {
            var self = this;

            // Custom task rendering to show baseline bars
            gantt.attachEvent("onGanttRender", function () {
                // Add baseline bars after gantt renders
                setTimeout(function () {
                    self._renderActualBars();
                }, 200);
            });

            // Also render baselines after task updates
            gantt.attachEvent("onAfterTaskUpdate", function (id, task) {
                setTimeout(function () {
                    self._renderActualBars();
                }, 100);
            });

            // Re-render actual bars after data refresh (when tasks are reloaded from backend)
            gantt.attachEvent("onParse", function () {
                setTimeout(function () {
                    self._renderActualBars();
                }, 200);
            });

            // Add baseline legend after gantt is ready
            gantt.attachEvent("onGanttReady", function () {
                setTimeout(function () {
                    self._addActualLegend();
                    // Initial render of baseline bars
                    self._renderActualBars();

                }, 300);
            });
        },

        /**
         * Update actual delayed status for a specific task
         * Compares current task dates with actual dates to determine if delayed
         */
        _updateActualStatus: function (taskId) {
            var task = gantt.getTask(taskId);
            if (!task || !task.has_actual || !task.actual_start_date || !task.actual_end_date) {
                return;
            }

            // Calculate if task is delayed by comparing actual end date with baseline end date
            var actualEndDate = moment(task.end_date);
            var actualEndDate = moment(task.actual_end_date);
            var wasDelayed = task.is_delayed;

            // Task is delayed if actual end date is after baseline end date
            task.is_delayed = actualEndDate.isAfter(task.actual_end_date);

            // If status changed, re-render baseline bars to update colors
            if (wasDelayed !== task.is_delayed) {
                this._renderActualBars();
            }
        },

        _renderActualBars: function () {
            var self = this;

            // Remove existing baseline bars
            document.querySelectorAll('.gantt_task_baseline').forEach(function (el) {
                el.remove();
            });

            // Always show actual bars - no toggle option

            var actualCount = 0;
            var rowHeight = gantt.config.row_height || 50; // Default to 50px if not configured

            gantt.eachTask(function (task) {
                // Skip parent tasks - only show actual bars for leaf tasks (tasks without children)
                if (task.$has_child) {
                    return;
                }

                if (task.has_actual && task.actual_start_date && task.actual_end_date) {
                    var taskElement = gantt.getTaskNode(task.id);

                    if (taskElement) {
                        var startPos = gantt.posFromDate(task.actual_start_date);
                        var endPos = gantt.posFromDate(task.actual_end_date);
                        var width = endPos - startPos;

                        // Get the vertical position from the task element itself
                        // This ensures it aligns with the task bar regardless of hierarchy changes
                        var verticalOffset = 0;
                        var taskPosition = gantt.getTaskPosition(task, task.start_date, task.end_date);

                        if (taskPosition && taskPosition.top !== undefined) {
                            // Use the gantt API to get the exact vertical position
                            verticalOffset = taskPosition.top;
                        } else {
                            // Fallback: Use the taskElement's offsetTop relative to the timeline
                            var timelineElement = document.querySelector('.gantt_task');
                            if (taskElement.offsetParent && timelineElement) {
                                // Calculate position relative to timeline container
                                var rect = taskElement.getBoundingClientRect();
                                var timelineRect = timelineElement.getBoundingClientRect();
                                verticalOffset = rect.top - timelineRect.top + timelineElement.scrollTop;
                            } else {
                                // Last resort: calculate from task index
                                var taskIndex = gantt.getTaskIndex(task.id);
                                verticalOffset = taskIndex * rowHeight;
                            }
                        }

                        if (width > 0) {
                            var baselineBar = document.createElement('div');

                            // Compare actual dates with baseline dates to determine color
                            var actualStart = moment(task.actual_start_date);
                            var actualEnd = moment(task.actual_end_date);
                            var baselineStart = moment(task.start_date);
                            var baselineEnd = moment(task.end_date);

                            var colorClass = 'gantt_task_baseline';
                            var statusText = '';

                            // Determine color based on comparison with baseline
                            if (actualStart.isSame(baselineStart, 'day') && actualEnd.isSame(baselineEnd, 'day')) {
                                // Grey: Actual matches baseline exactly
                                colorClass += ' same_as_baseline';
                                statusText = 'ON SCHEDULE';
                            } else if (actualEnd.isAfter(baselineEnd)) {
                                // Red: Actual end is after baseline end (delayed)
                                colorClass += ' over_baseline';
                                var delayDays = actualEnd.diff(baselineEnd, 'days');
                                statusText = 'DELAYED (' + delayDays + ' days)';
                            } else if (actualEnd.isBefore(baselineEnd) || actualStart.isAfter(baselineStart)) {
                                // Green: Actual is ahead of baseline or finishes early
                                colorClass += ' ahead_of_baseline';
                                var aheadDays = baselineEnd.diff(actualEnd, 'days');
                                statusText = 'AHEAD (' + aheadDays + ' days)';
                            } else {
                                // Default grey for other cases
                                colorClass += ' same_as_baseline';
                                statusText = 'ON SCHEDULE';
                            }

                            baselineBar.className = colorClass;
                            baselineBar.style.left = startPos + 'px';
                            baselineBar.style.width = width + 'px';
                            baselineBar.style.position = 'absolute';
                            // Position baseline bar at the bottom of the task row
                            baselineBar.style.top = (verticalOffset + rowHeight - 15) + 'px';
                            baselineBar.style.height = '12px';
                            baselineBar.style.zIndex = '1';

                            // Add tooltip to show baseline information
                            var tooltipText = 'Actual: ' +
                                actualStart.format('MMM DD') + ' - ' +
                                actualEnd.format('MMM DD') + '\n' +
                                'Baseline: ' +
                                baselineStart.format('MMM DD') + ' - ' +
                                baselineEnd.format('MMM DD') + '\n' +
                                'Status: ' + statusText;
                            baselineBar.title = tooltipText;

                            taskElement.parentNode.appendChild(baselineBar);
                            actualCount++;
                        }
                    }
                }
            });

        },


        _addActualLegend: function () {
            var ganttContainer = document.querySelector('.gantt_container');
            if (ganttContainer && !document.querySelector('.gantt_baseline_legend')) {
                var legend = document.createElement('div');
                legend.className = 'gantt_baseline_legend';
                legend.innerHTML = `
                    <div class="gantt_baseline_legend_item">
                        <div class="gantt_baseline_legend_color baseline"></div>
                        <span>Actual</span>
                    </div>
                    <div class="gantt_baseline_legend_item">
                        <div class="gantt_baseline_legend_color actual"></div>
                        <span>Actual</span>
                    </div>
                    <div class="gantt_baseline_legend_item">
                        <div class="gantt_baseline_legend_color delayed"></div>
                        <span>Delayed</span>
                    </div>
                `;
                ganttContainer.appendChild(legend);
            }
        },

        /**
         * Setup critical path functionality
         * Implements critical path calculation using longest path algorithm
         */
        _setupCriticalPath: function () {
            var self = this;

            this.criticalPathCache = {
                tasks: new Set(),
                links: new Set(),
                lastCalculated: null
            };

            gantt.isCriticalTask = function (task) {
                return self.criticalPathCache.tasks.has(task.id);
            };

            gantt.isCriticalLink = function (link) {
                return self.criticalPathCache.links.has(link.id);
            };

            // Note: task_class template is already defined above with critical path support merged in
            // No need to redefine it here

            gantt.templates.link_class = function (link) {
                var classes = [];
                if (gantt.config.highlight_critical_path && gantt.isCriticalLink && gantt.isCriticalLink(link)) {
                    classes.push('gantt_critical_link');
                }

                return classes.join(' ');
            };

            // Calculate critical path using longest path algorithm
            this._calculateCriticalPath();
        },

        /**
         * Calculate critical path using topological sort and longest path algorithm
         * Based on Microsoft Project's critical path methodology
         */
        _calculateCriticalPath: function () {
            var self = this;
            var tasks = gantt.getTaskByTime();
            var links = gantt.getLinks();
            if (!tasks.length) {
                return;
            }
            this.criticalPathCache.tasks.clear();
            this.criticalPathCache.links.clear();

            var graph = {};
            var inDegree = {};
            var taskDurations = {};
            var earliestStart = {};
            var earliestFinish = {};
            var latestStart = {};
            var latestFinish = {};

            tasks.forEach(function (task) {
                if (!task.is_group) {
                    graph[task.id] = [];
                    inDegree[task.id] = 0;
                    taskDurations[task.id] = gantt.calculateDuration(task.start_date, task.end_date);
                    earliestStart[task.id] = 0;
                    earliestFinish[task.id] = 0;
                    latestStart[task.id] = Infinity;
                    latestFinish[task.id] = Infinity;
                }
            });

            links.forEach(function (link) {
                var sourceTask = gantt.getTask(link.source);
                var targetTask = gantt.getTask(link.target);

                if (sourceTask && targetTask && !sourceTask.is_group && !targetTask.is_group) {
                    graph[link.source] = graph[link.source] || [];
                    graph[link.source].push({
                        target: link.target,
                        linkId: link.id,
                        type: link.type || "0"
                    });
                    inDegree[link.target] = (inDegree[link.target] || 0) + 1;
                }
            });

            var queue = [];
            Object.keys(inDegree).forEach(function (taskId) {
                if (inDegree[taskId] === 0) {
                    queue.push(taskId);
                    earliestStart[taskId] = 0;
                    earliestFinish[taskId] = taskDurations[taskId];
                }
            });

            while (queue.length > 0) {
                var currentTask = queue.shift();
                var dependencies = graph[currentTask] || [];

                dependencies.forEach(function (dep) {
                    var targetId = dep.target;
                    var linkType = dep.type;
                    var newEarliestStart = 0;

                    if (linkType === "0" || !linkType) { // Finish-to-start
                        newEarliestStart = earliestFinish[currentTask];
                    }

                    if (newEarliestStart > earliestStart[targetId]) {
                        earliestStart[targetId] = newEarliestStart;
                        earliestFinish[targetId] = newEarliestStart + taskDurations[targetId];
                    }

                    inDegree[targetId]--;
                    if (inDegree[targetId] === 0) {
                        queue.push(targetId);
                    }
                });
            }

            var projectEndTime = Math.max.apply(Math, Object.values(earliestFinish));

            Object.keys(latestFinish).forEach(function (taskId) {
                if (earliestFinish[taskId] === projectEndTime) {
                    latestFinish[taskId] = projectEndTime;
                    latestStart[taskId] = projectEndTime - taskDurations[taskId];
                }
            });

            var processed = new Set();
            var reverseQueue = Object.keys(earliestFinish).filter(function (taskId) {
                return earliestFinish[taskId] === projectEndTime;
            });

            while (reverseQueue.length > 0) {
                var currentTask = reverseQueue.shift();
                if (processed.has(currentTask)) continue;
                processed.add(currentTask);

                links.forEach(function (link) {
                    if (link.target === currentTask) {
                        var sourceId = link.source;
                        var sourceTask = gantt.getTask(sourceId);

                        if (sourceTask && !sourceTask.is_group) {
                            var newLatestFinish = latestStart[currentTask];

                            if (newLatestFinish < latestFinish[sourceId]) {
                                latestFinish[sourceId] = newLatestFinish;
                                latestStart[sourceId] = newLatestFinish - taskDurations[sourceId];

                                if (!processed.has(sourceId)) {
                                    reverseQueue.push(sourceId);
                                }
                            }
                        }
                    }
                });
            }

            Object.keys(earliestStart).forEach(function (taskId) {
                var slack = latestStart[taskId] - earliestStart[taskId];
                if (Math.abs(slack) < 0.001) { // Account for floating point precision
                    self.criticalPathCache.tasks.add(taskId);
                }
            });

            links.forEach(function (link) {
                var sourceTask = gantt.getTask(link.source);
                var targetTask = gantt.getTask(link.target);

                if (sourceTask && targetTask &&
                    !sourceTask.is_group && !targetTask.is_group &&
                    self.criticalPathCache.tasks.has(link.source) &&
                    self.criticalPathCache.tasks.has(link.target)) {
                    self.criticalPathCache.links.add(link.id);
                }
            });

            this.criticalPathCache.lastCalculated = new Date();
        },

        /**
         * Add critical path toggle button to gantt toolbar
         */
        _addCriticalPathToggle: function () {
            // Skip if toggle already exists
            if (document.querySelector('.gantt_critical_path_toggle')) {
                return;
            }

            var toolbarSelectors = [
                '.o_gantt_button_dates',
                '.o_control_panel .btn-group',
                '.o_control_panel .o_gantt_button_dates',
                '.o_cp_buttons',
                '.o_cp_left'
            ];

            var toolbar = null;
            for (var i = 0; i < toolbarSelectors.length; i++) {
                toolbar = document.querySelector(toolbarSelectors[i]);
                if (toolbar) {
                    console.log('Found toolbar for critical path toggle using selector:', toolbarSelectors[i]);
                    break;
                }
            }

            if (toolbar) {

                // Create a button group container for the toggle (matching baseline style)
                var buttonGroup = document.createElement('div');
                buttonGroup.className = 'btn-group ml-2';
                buttonGroup.setAttribute('role', 'group');
                buttonGroup.setAttribute('aria-label', 'Critical path controls');

                var toggleBtn = document.createElement('button');
                toggleBtn.className = 'gantt_critical_path_toggle btn btn-secondary';
                toggleBtn.textContent = 'Critical Path';
                toggleBtn.type = 'button';
                toggleBtn.title = 'Toggle critical path highlighting';

                var self = this;
                toggleBtn.addEventListener('click', function () {
                    self._toggleCriticalPath();
                });

                buttonGroup.appendChild(toggleBtn);
                toolbar.appendChild(buttonGroup);
            } else {
                toolbarSelectors.forEach(function (selector) {
                    var element = document.querySelector(selector);
                    console.log('  ' + selector + ':', !!element);
                });
            }
        },

        /**
         * Toggle critical path display on/off
         */
        _toggleCriticalPath: function () {
            var self = this;
            var isEnabled = gantt.config.highlight_critical_path;
            gantt.config.highlight_critical_path = !isEnabled;

            // Find the toggle button
            var toggleBtn = document.querySelector('.gantt_critical_path_toggle');
            if (toggleBtn) {
                // Update button state and text (matching baseline toggle behavior)
                toggleBtn.classList.toggle('active', gantt.config.highlight_critical_path);
                toggleBtn.textContent = gantt.config.highlight_critical_path ? 'Hide Critical Path' : 'Critical Path';
            }

            // Recalculate critical path if enabling
            if (gantt.config.highlight_critical_path) {
                this._calculateCriticalPath();
            } else {
                // Clear critical path cache when disabling
                this.criticalPathCache.tasks.clear();
                this.criticalPathCache.links.clear();
            }

            // Force complete refresh to apply/remove critical path classes
            gantt.refreshData();
            gantt.refreshLink();

            // Re-render actual bars after refresh to ensure they persist
            setTimeout(function () {
                self._renderActualBars();
            }, 100);
        },

        /**
         * Update renderer state with new data
         */
        updateState: function (state, params) {
            this.state = state;
            return Promise.resolve();
        },

        /**
         * Trigger rendering after data is loaded
         * This method should be called by the controller after model data loading completes
         */
        renderAfterDataLoad: function () {
            var self = this;

            // The model's get() method returns the gantt object directly
            if (this.state && this.state.data && this.state.data.length > 0) {
                this._renderGantt();
                this._configureGanttEvents(this.state.data, this.state.grouped_by || this.state.groupedBy, this.state.groups);
                // Re-setup actual rendering events after data reload to ensure actual bars persist after save
                this._setupActualRendering();

                // Force immediate re-render of actual bars after data load
                // This ensures child task actual date updates are visible immediately
                setTimeout(function () {
                    self._renderActualBars();
                }, 300);
            }
        },

        _renderGantt: function () {
            var self = this;

            // Check if state and data are properly loaded
            if (!this.state || !this.state.data) {
                return;
            }

            var tasks = this.state.data;
            var grouped_by = this.state.grouped_by || [];
            var groups = this.state.groups;
            var links = _.compact(_.map(this.state.link || [], function (link) {
                link = _.clone(link);
                return link;
            }));
            var gantt_tasks = { 'data': [], 'links': [] };
            var gantt_tasks_data = gantt_tasks['data'];
            var gantt_links_data = gantt_tasks['links'];
            var gantt_tasks_links = [];
            var mapping = this.state.mapping;

            var tasks = _.compact(_.map(this.state.data, function (task) {
                task = _.clone(task);

                var task_start;
                if (task[self.dateStartField]) {
                    task_start = time.auto_str_to_date(task[self.dateStartField]);
                }
                else {
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
                    if (task[self.colorField] == '1') {
                        color = '#F06050';
                    }
                    if (task[self.colorField] == '2') {
                        color = '#F4A460';
                    }
                    if (task[self.colorField] == '3') {
                        color = '#F7CD1F';
                    }
                    if (task[self.colorField] == '4') {
                        color = '#6CC1ED';
                    }
                    if (task[self.colorField] == '5') {
                        color = '#814968';
                    }
                    if (task[self.colorField] == '6') {
                        color = '#EB7E7F';
                    }
                    if (task[self.colorField] == '7') {
                        color = '#2C8397';
                    }
                    if (task[self.colorField] == '8') {
                        color = '#475577';
                    }
                    if (task[self.colorField] == '9') {
                        color = '#D6145F';
                    }
                    if (task[self.colorField] == '10') {
                        color = '#30C381';
                    }
                    if (task[self.colorField] == '11') {
                        color = '#9365B8';
                    }
                } else {
                    color = "#7C7BAD";
                }
                task.color = color;


                var type;
                if (task[self.taskType]) {
                    type = task[self.taskType];
                } else {
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

                // Add baseline data processing
                var actual_start_date, actual_end_date;

                if (task.actual_start_date) {
                    // Try different date parsing methods
                    if (typeof task.actual_start_date === 'string') {
                        actual_start_date = new Date(task.actual_start_date);
                        // If invalid date, try time.auto_str_to_date
                        if (isNaN(actual_start_date.getTime())) {
                            actual_start_date = time.auto_str_to_date(task.actual_start_date);
                        }
                    } else {
                        actual_start_date = time.auto_str_to_date(task.actual_start_date);
                    }
                }
                if (task.actual_end_date) {
                    // Try different date parsing methods
                    if (typeof task.actual_end_date === 'string') {
                        actual_end_date = new Date(task.actual_end_date);
                        // If invalid date, try time.auto_str_to_date
                        if (isNaN(actual_end_date.getTime())) {
                            actual_end_date = time.auto_str_to_date(task.actual_end_date);
                        }
                    } else {
                        actual_end_date = time.auto_str_to_date(task.actual_end_date);
                    }
                }
                task.actual_start_date = actual_start_date;
                task.actual_end_date = actual_end_date;
                task.has_actual = !!(actual_start_date && actual_end_date && !isNaN(actual_start_date.getTime()) && !isNaN(actual_end_date.getTime()));

                // Check if task is delayed
                if (task.has_actual && task.task_stop) {
                    task.is_delayed = task.task_stop > actual_end_date;
                } else {
                    task.is_delayed = false;
                }


                return task;
            }));


            var split_groups = function (tasks, grouped_by) {
                if (!grouped_by || grouped_by.length === 0) {
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
                            name: group_name,
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
                    if (level > 0 && task.tasks.length === 0) {
                        return;
                    }
                    var project_id = _.uniqueId("gantt_project_");
                    var field = self.state.fields[grouped_by[level]];

                    var group_name = task[mapping.name] ? field_utils.format[field.type](task[mapping.name], field) : "-";

                    var sum = _.reduce(task.percent, function (acc, num) { return acc + num; }, 0);
                    var progress = sum / task.percent.length / 100 || 0;

                    var t = {
                        'id': project_id,
                        'text': group_name,
                        'wbs_code': '',
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
                        build_tasks(subtask, level + 1, project_id);
                    });
                }
                else {
                    var parent;
                    if (task.parent_id) {
                        parent = "gantt_task_" + task.parent_id[0];
                    } else {
                        parent = parent_id;
                    }
                    gantt_tasks_data.push({
                        'id': "gantt_task_" + task.id,
                        'text': task.display_name || '',
                        'wbs_code': task.wbs_code || '',
                        'active': task.active || true,
                        'start_date': task.task_start,
                        'end_date': task.task_stop,
                        'progress': task.percent / 100,
                        'parent': parent,
                        'open': true,
                        'color': task.color || 0,
                        'index': gantt_tasks.length,
                        'type': task.type,
                        'rollup': true,
                        'deadline': task.deadline,
                        'priority': task.priority,
                        // Baseline data for dual-bar rendering
                        'actual_start_date': task.actual_start_date,
                        'actual_end_date': task.actual_end_date,
                        'has_actual': !!(task.actual_start_date && task.actual_end_date),
                        'is_delayed': task.is_delayed || false,
                        // Store original task id for WBS lookups
                        'odoo_id': task.id,
                    });
                }
            };
            gantt_tasks['data'] = gantt_tasks_data;

            _.each(groups, function (group) {
                build_tasks(group, 0);
            });

            var build_links = function (link) {
                if (link) {
                    gantt_tasks_links.push({
                        'id': "gantt_link_" + link.id,
                        'source': "gantt_task_" + link.source,
                        'target': "gantt_task_" + link.target,
                        'type': link.type,
                    });
                }
            };

            gantt_tasks['links'] = gantt_tasks_links;
            if (self.showLinks === 'true') {
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

            // Setup critical path functionality after gantt is initialized
            this._setupCriticalPath();

            // Add critical path toggle button
            setTimeout(function () {
                self._addCriticalPathToggle();
            }, 100);
        },

        _configureGanttEvents: function (tasks, grouped_by, groups) {
            var self = this;

            // Clear any existing event handlers to prevent duplicates
            if (this.gantt_events && this.gantt_events.length > 0) {
                this.gantt_events.forEach(function (eventId) {
                    gantt.detachEvent(eventId);
                });
                this.gantt_events = [];
            }

            // Detach all existing onTaskClick handlers
            gantt.detachAllEvents();


            this.gantt_events.push(gantt.attachEvent("onTaskClick", function (id, e) {
                var task = gantt.getTask(id);

                // Check if click is on tree icon (expand/collapse)
                if (e && e.target) {
                    var target = e.target;
                    // Check if clicked element is tree icon or within tree icon
                    if (target.classList.contains('gantt_tree_icon') ||
                        target.classList.contains('gantt_tree_content') ||
                        target.closest('.gantt_tree_icon')) {
                        // Let DHtmlXGantt handle the expand/collapse
                        return true;
                    }
                }

                // If clicking on a parent task (not on tree icon), toggle expand/collapse
                if (task.$has_child || task.is_group) {
                    // Toggle the task open/close state using DHtmlXGantt API
                    if (task.$open) {
                        gantt.close(id);
                    } else {
                        gantt.open(id);
                    }
                    return false; // Prevent modal from opening on parent tasks
                }

                // Handle special "unused" task creation
                if (id.indexOf("unused") >= 0) {
                    var key = "default_" + task.create[0];
                    var context = {};
                    context[key] = task.create[1][0];
                    self.trigger_up('task_create', context);
                }
                else {
                    // Open modal for leaf tasks only
                    self.trigger_up('task_display', task);
                }
                return true;
            }));

            this.gantt_events.push(gantt.attachEvent("onTaskDblClick", function () {
                return false;
            }));

            this.gantt_events.push(gantt.attachEvent("onBeforeTaskSelected", function (id) {
                var task = gantt.getTask(id);
                // Prevent selection of parent tasks (they should only expand/collapse)
                if (task.$has_child || task.is_group) {
                    return false;
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

                _.each(gantt.getChildren(parent.id), function (task_id) {
                    var task_start_date = gantt.getTask(task_id).start_date;
                    var task_stop_date = gantt.getTask(task_id).end_date;
                    if (!start_date) {
                        start_date = task_start_date;
                    }
                    if (!stop_date) {
                        stop_date = task_stop_date;
                    }
                    if (start_date > task_start_date) {
                        start_date = task_start_date;
                    }
                    if (stop_date < task_stop_date) {
                        stop_date = task_stop_date;
                    }
                });

                parent.start_date = start_date;
                parent.end_date = stop_date;
                gantt.updateTask(parent.id);
                if (parent.parent) parent_date_update(parent.id);
            };

            this.gantt_events.push(gantt.attachEvent("onBeforeTaskDrag", function (id, mode, e) {
                var task = gantt.getTask(id);

                // Store original dates for ALL tasks (parent or leaf)
                task._start_date_original = task.start_date;
                task._end_date_original = task.end_date;

                // Store original actual dates if they exist
                if (task.actual_start_date) {
                    task._actual_start_date_original = task.actual_start_date;
                }
                if (task.actual_end_date) {
                    task._actual_end_date_original = task.actual_end_date;
                }

                this.lastX = e.pageX;

                // If this is a parent task (has children), prepare to drag all children together
                if (task.$has_child && !task.is_group) {
                    // Collect all child IDs recursively
                    var collectChildIds = function(parentId) {
                        var children = [];
                        gantt.eachTask(function(childTask) {
                            children.push(childTask.id);
                        }, parentId);
                        return children;
                    };

                    this.drag_children = collectChildIds(id);

                    // Store original dates for all children
                    _.each(this.drag_children, function (child_id) {
                        var child = gantt.getTask(child_id);
                        child._start_date_original = child.start_date;
                        child._end_date_original = child.end_date;
                        if (child.actual_start_date) {
                            child._actual_start_date_original = child.actual_start_date;
                        }
                        if (child.actual_end_date) {
                            child._actual_end_date_original = child.actual_end_date;
                        }
                    });
                }

                // Handle special 'is_group' tasks (existing logic for consolidated groups)
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

                return true; // Allow dragging for ALL tasks (parents and children)
            }));

            this.gantt_events.push(gantt.attachEvent("onTaskDrag", function (id, mode, task, original, e) {
                // Handle special 'is_group' tasks (existing logic)
                if (gantt.getTask(id).is_group) {
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

                    if (task.start_date > original.start_date) {
                        task.start_date = original.start_date;
                    }
                    if (task.end_date < original.end_date) {
                        task.end_date = original.end_date;
                    }

                    if (this.drag_child) {
                        _.each(this.drag_child, function (child_id) {
                            var child = gantt.getTask(child_id);
                            var new_start = +child.start_date + diff;
                            var new_stop = +child.end_date + diff;
                            if (new_start < gantt.config.start_date || new_stop > gantt.config.end_date) {
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

                // NEW: Handle parent task with children drag
                if (task.$has_child && this.drag_children) {
                    // Calculate time delta based on current drag position vs original
                    var startDelta = task.start_date - task._start_date_original;
                    var endDelta = task.end_date - task._end_date_original;

                    // Update all children by the same delta
                    _.each(this.drag_children, function (child_id) {
                        var child = gantt.getTask(child_id);

                        // Shift baseline dates
                        if (child._start_date_original) {
                            child.start_date = new Date(child._start_date_original.getTime() + startDelta);
                        }
                        if (child._end_date_original) {
                            child.end_date = new Date(child._end_date_original.getTime() + endDelta);
                        }

                        // Shift actual dates (if they exist)
                        if (child._actual_start_date_original) {
                            child.actual_start_date = new Date(child._actual_start_date_original.getTime() + startDelta);
                        }
                        if (child._actual_end_date_original) {
                            child.actual_end_date = new Date(child._actual_end_date_original.getTime() + endDelta);
                        }

                        // Update the gantt display for this child
                        gantt.updateTask(child.id);
                    });
                }

                // Existing parent date update logic
                parent_date_update(id);
                return true;
            }));

            this.gantt_events.push(gantt.attachEvent("onAfterTaskDrag", function (id) {
                var self_gantt = this;

                // Function to update a single task
                var update_task = function (task_id, is_child_of_dragged_parent) {
                    var task = gantt.getTask(task_id);

                    self.trigger_up('task_update', {
                        task: task,
                        is_child_of_parent: is_child_of_dragged_parent || false,
                        success: function () {
                            // Clean up temporary properties
                            delete task._start_date_original;
                            delete task._end_date_original;
                            delete task._actual_start_date_original;
                            delete task._actual_end_date_original;

                            // Update parent dates
                            parent_date_update(task_id);

                            // Update baseline status
                            self._updateActualStatus(task_id);

                            // Recalculate critical path if enabled
                            if (gantt.config.highlight_critical_path) {
                                self._calculateCriticalPath();
                            }
                        },
                        fail: function () {
                            // Revert to original dates
                            task.start_date = task._start_date_original;
                            task.end_date = task._end_date_original;

                            if (task._actual_start_date_original) {
                                task.actual_start_date = task._actual_start_date_original;
                            }
                            if (task._actual_end_date_original) {
                                task.actual_end_date = task._actual_end_date_original;
                            }

                            gantt.updateTask(task_id);

                            // Clean up
                            delete task._start_date_original;
                            delete task._end_date_original;
                            delete task._actual_start_date_original;
                            delete task._actual_end_date_original;

                            parent_date_update(task_id);
                            self._updateActualStatus(task_id);

                            if (gantt.config.highlight_critical_path) {
                                self._calculateCriticalPath();
                            }
                        }
                    });
                };

                // Handle 'is_group' special case (existing logic)
                if (gantt.getTask(id).is_group && self_gantt.drag_child) {
                    _.each(self_gantt.drag_child, function (child_id) {
                        update_task(child_id, false);
                    });
                    self_gantt.drag_child = null;
                }
                // NEW: Handle parent task with children
                else if (gantt.getTask(id).$has_child && self_gantt.drag_children) {
                    // Update all children first
                    _.each(self_gantt.drag_children, function (child_id) {
                        update_task(child_id, true);
                    });

                    // Clean up drag state
                    self_gantt.drag_children = null;
                }

                // Update the parent/main task last
                update_task(id, false);
            }));

            this.gantt_events.push(gantt.attachEvent("onAfterLinkAdd", function (id, item) {
                var crate_link = function (item) {
                    self.trigger_up('crate_link', {
                        link: item,
                        success: function (newID) {
                            if (newID) {
                                var newID = "gantt_task_" + newID;
                                gantt.changeLinkId(item.id, newID);
                            }
                            // Recalculate critical path when link is added
                            if (gantt.config.highlight_critical_path) {
                                self._calculateCriticalPath();
                            }
                        },
                        fail: function () { },
                    });
                };
                crate_link(item);
            }));

            this.gantt_events.push(gantt.attachEvent("onAfterLinkDelete", function (id, item) {
                var delete_link = function (item) {
                    self.trigger_up('delete_link', {
                        link: item,
                        success: function (delete_links) {
                            // Recalculate critical path when link is deleted
                            if (gantt.config.highlight_critical_path) {
                                self._calculateCriticalPath();
                            }
                        },
                        fail: function () {

                        }
                    });
                };
                delete_link(item);
            }));

            this.gantt_events.push(gantt.attachEvent("onBeforeLinkAdd", function (id, item) {
                var sourceTask = gantt.getTask(item.source);
                var targetTask = gantt.getTask(item.target);

                // Prevent linking from/to parent tasks (tasks with children)
                if (sourceTask.$has_child || sourceTask.is_group) {
                    gantt.message({ type: "error", text: "You can't create link from a parent task. Only child tasks can have links." });
                    return false;
                }
                if (targetTask.$has_child || targetTask.is_group) {
                    gantt.message({ type: "error", text: "You can't create link to a parent task. Only child tasks can have links." });
                    return false;
                }

                // Allow links between tasks with different parents
                // (Removed the parent constraint to enable cross-parent linking)

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

