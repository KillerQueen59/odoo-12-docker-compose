odoo.define('rnet_project_management_dashboard.dashboard', function (require) {
    "use strict";

    var AbstractAction = require('web.AbstractAction');
    var core = require('web.core');
    var rpc = require('web.rpc');
    var QWeb = core.qweb;

    var Dashboard = AbstractAction.extend({
        template: 'rnet_project_management_dashboard.DashboardTemplate',
        hasControlPanel: false,
        events: {
            // --- FIX: Events are split into Global and Local ---
            'change #db_project_filter, #db_employee_filter, #db_date_range_picker': '_onGlobalFilterChange',
            // Note: toggle_all_projects is removed as it's not in the correct template
            
            // Events for the Advanced Review Table
            'keyup #review_search_bar': '_onReviewSearchInput',
            'click .rating-filter-item': '_onRatingClick',
            'click .sortable_header': '_onSortClick',
            'click #prev_page_btn': '_onPrevPageClick',
            'click #next_page_btn': '_onNextPageClick',
            
            // Other events (unchanged)
            'click #project_progress_body .clickable-row': '_onProjectProgressRowClick',
            'click #progress_prev_page_btn': '_onProgressPrevPageClick',
            'click #progress_next_page_btn': '_onProgressNextPageClick',
            'click .chart-toggle-btn': '_onChartTypeChange',
        },

        init: function (parent, context) {
            this._super(parent, context);
            // This is your correct init block, augmented with the new review state
            this.model = 'project.management.dashboard';
            this.filter_data = null;
            
            // State for Advanced Review Table
            this.reviewCurrentPage = 1; this.reviewLimit = 10; this.reviewTotalRecords = 0;
            this.reviewCurrentSort = 'employee_name asc'; // Default sort for new table
            this.currentRatingFilters = [];
            
            // State for the rest of the dashboard (from your correct version)
            this.progressCurrentPage = 1; this.progressLimit = 10; this.progressTotalRecords = 0;
            this.showAllProjects = false;
            this.isInitialLoad = true;
            this.cashflowChart = null;
            this.sCurveChart = null;
            this.cashInOutChart = null;
            this.invoiceChart = null;
            this.manhourChart = null;
            this.cashInOutChartType = 'line';
            this.invoiceChartType = 'line';
            this.manhourChartType = 'line';
            this.dashboardData = {};
            // Debounce the search input handler
            this._onReviewSearchInput = _.debounce(this._onReviewSearchInput, 300);
        },

        willStart: function() {
            var self = this;
            return this._super.apply(this, arguments).then(function() {
                return self._fetchFilterData();
            });
        },

        start: function() {
            var self = this;
            this.set("title", 'Dashboard');
            return this._super.apply(this, arguments).then(function() {
                self._renderFilters();
            });
        },

        on_attach_callback: function() {
            this._super.apply(this, arguments);
            // --- FIX: Load data for both sections on attach ---
            this._loadAllData(); // Loads KPIs, Progress table, Charts
            this._fetchReviewData(); // Loads the new review table
        },
        
        _fetchFilterData: function() {
            var self = this;
            return rpc.query({
                model: self.model,
                method: 'get_dashboard_filters',
            }).then(function (result) {
                self.filter_data = result;
            });
        },

        _loadAllData: function() {
            var self = this;
            var filters = this._getGlobalFilters();
            var kpiPromise = rpc.query({ model: this.model, method: 'get_kpi_data', kwargs: { filters: filters }});
            var progressPromise = rpc.query({ model: this.model, method: 'get_project_progress_data', kwargs: { filters: filters, page: this.progressCurrentPage, limit: this.progressLimit }});
            var cashflowPromise = rpc.query({ model: this.model, method: 'get_cashflow_chart_data', kwargs: { filters: filters }});
            var sCurvePromise = rpc.query({ model: this.model, method: 'get_s_curve_data', kwargs: { filters: filters }});
            var cashInOutPromise = rpc.query({ model: this.model, method: 'get_cash_in_vs_plan_out_data', kwargs: { filters: filters }});
            var invoicePromise = rpc.query({ model: this.model, method: 'get_invoice_data', kwargs: { filters: filters }});
            var manhourPromise = rpc.query({ model: this.model, method: 'get_manhour_data', kwargs: { filters: filters }});
            
            return Promise.all([kpiPromise, progressPromise, cashflowPromise, sCurvePromise, cashInOutPromise, invoicePromise, manhourPromise]).then(function(results) {
                // Store and render the global components
                self.dashboardData.kpiAndCharts = results[0];
                self.dashboardData.progress = results[1];
                self.dashboardData.cashflow = results[2];
                self.dashboardData.sCurve = results[3];
                self.dashboardData.cashInOut = results[4];
                self.dashboardData.invoice = results[5];
                self.dashboardData.manhour = results[6];

                // self.$('.kpi_cards_container').html(QWeb.render('rnet_project_management_dashboard.KpiCards', { kpis: self.dashboardData.kpiAndCharts.kpis }));
                self.progressTotalRecords = self.dashboardData.progress.total;
                self.$('#project_progress_body').html(QWeb.render('rnet_project_management_dashboard.ProjectProgressTable', { widget: self, progress_data: self.dashboardData.progress.progress_data }));
                self._updateProgressVisualIndicators();
                self._renderCashflowChart(self.dashboardData.cashflow);
                self._renderSCurveChart(self.dashboardData.sCurve);
                self._renderCashInOutChart(self.dashboardData.cashInOut);
                self._renderInvoiceChart(self.dashboardData.invoice);
                self._renderManhourChart(self.dashboardData.manhour);
            });
        },

        // --- NEW: Dedicated function to fetch and render the review table ---
        _fetchReviewData: function() {
            var self = this;
            var reviewFilters = {
                search_term: this.$('#review_search_bar').val(),
                ratings: this.currentRatingFilters,
            };
            return rpc.query({
                model: this.model,
                method: 'get_advanced_review_data',
                kwargs: { filters: reviewFilters, page: this.reviewCurrentPage, limit: this.reviewLimit, sort: this.reviewCurrentSort }
            }).then(function(data) {
                self._renderReviewTable(data);
            });
        },

        _onChartTypeChange: function(ev) {
            ev.preventDefault();
            var $target = $(ev.currentTarget);
            var chartName = $target.data('chart');
            var chartType = $target.data('type');
            this[chartName + 'ChartType'] = chartType;
            if (chartName === 'cashInOut') { this._renderCashInOutChart(this.dashboardData.cashInOut); }
            if (chartName === 'invoice') { this._renderInvoiceChart(this.dashboardData.invoice); }
            if (chartName === 'manhour') { this._renderManhourChart(this.dashboardData.manhour); }
        },

        _renderCashflowChart: function(chartData) {
            if (this.cashflowChart) { this.cashflowChart.destroy(); }
            var formattedLabels = chartData.labels.map(label => moment(label, "YYYY-MM").format("MMM YYYY"));
            var datasets = [ { label: 'Accumulative Cash Flow', data: chartData.accum_flow, type: 'line', borderColor: 'rgb(124, 17, 88)', backgroundColor: 'rgba(0,0,0,0)', fill: false, yAxisID: 'y-axis-line', }, { label: 'Actual Cash In', data: chartData.actual_in, backgroundColor: 'rgb(26, 83, 255)', yAxisID: 'y-axis-bar', }, { label: 'Actual Cash Out', data: chartData.actual_out, backgroundColor: 'rgb(255, 163, 0)', yAxisID: 'y-axis-bar', }, ];
            this.cashflowChart = new Chart(this.$('#cashflow_summary_chart'), { type: 'bar', data: { labels: formattedLabels, datasets: datasets }, options: { responsive: true, maintainAspectRatio: false, layout: { padding: { bottom: 20 } }, scales: { xAxes: [{ ticks: { autoSkip: false, maxRotation: 45, minRotation: 45 } }], yAxes: [ { id: 'y-axis-bar', position: 'left', ticks: { beginAtZero: true, callback: function(value) { return value.toLocaleString(); } } }, { id: 'y-axis-line', position: 'right', gridLines: { drawOnChartArea: false }, ticks: { callback: function(value) { return value.toLocaleString(); } } } ] }, tooltips: { callbacks: { label: function(tooltipItem, data) { return data.datasets[tooltipItem.datasetIndex].label + ': ' + tooltipItem.yLabel.toLocaleString(); } } } } });
        },
        
        _renderSCurveChart: function(chartData) {
            if (this.sCurveChart) { this.sCurveChart.destroy(); }
            var formattedLabels = chartData.labels.map(label => moment(label, "YYYY-MM").format("MMM YYYY"));
            this.sCurveChart = new Chart(this.$('#s_curve_chart'), { type: 'line', data: { labels: formattedLabels, datasets: [ { label: 'Plan S-Curve (%)', data: chartData.plan_data, borderColor: 'rgb(179, 212, 255)', fill: false }, { label: 'Actual S-Curve (%)', data: chartData.actual_data, borderColor: 'rgb(26, 83, 255)', fill: false }, ] },
                options: { responsive: true, maintainAspectRatio: false, scales: { yAxes: [{ ticks: { beginAtZero: true, suggestedMax: 100, callback: v => v + ' %' } }] },
                    // S-Curve tooltips should show percentage
                    tooltips: { callbacks: { label: function(tooltipItem, data) { return data.datasets[tooltipItem.datasetIndex].label + ': ' + tooltipItem.yLabel + ' %'; } } }
                }
            });
        },
        
        // --- FIX: Added formatted tooltips to the three charts below ---
        _renderCashInOutChart: function(chartData) {
            if (this.cashInOutChart) { this.cashInOutChart.destroy(); }
            var formattedLabels = chartData.labels.map(label => moment(label, "YYYY-MM").format("MMM YYYY"));
            this.cashInOutChart = new Chart(this.$('#cash_in_out_chart'), {
                type: this.cashInOutChartType, data: { labels: formattedLabels, datasets: [ { label: 'Plan Cash Out', data: chartData.plan_out_data, borderColor: 'rgb(255, 163, 0)', backgroundColor: 'rgba(255, 163, 0, 0.5)', fill: false }, { label: 'Actual Cash In', data: chartData.actual_in_data, borderColor: 'rgb(28, 163, 68)', backgroundColor: 'rgba(28, 163, 68, 0.5)', fill: false }, ] },
                options: { responsive: true, maintainAspectRatio: false, scales: { yAxes: [{ ticks: { beginAtZero: true, callback: v => v.toLocaleString() } }] },
                    tooltips: { callbacks: { label: function(tooltipItem, data) { return data.datasets[tooltipItem.datasetIndex].label + ': ' + tooltipItem.yLabel.toLocaleString(); } } }
                }
            });
            this.$('.chart-toggle-btn[data-chart="cashInOut"]').removeClass('active').filter('[data-type="' + this.cashInOutChartType + '"]').addClass('active');
        },
        _renderInvoiceChart: function(chartData) {
            if (this.invoiceChart) { this.invoiceChart.destroy(); }
            var formattedLabels = chartData.labels.map(label => moment(label, "YYYY-MM").format("MMM YYYY"));
            this.invoiceChart = new Chart(this.$('#invoice_chart'), {
                type: this.invoiceChartType, data: { labels: formattedLabels, datasets: [ { label: 'Plan Invoice', data: chartData.plan_data, borderColor: 'rgb(179, 212, 255)', backgroundColor: 'rgba(179, 212, 255, 0.5)', fill: false }, { label: 'Actual Invoice', data: chartData.actual_data, borderColor: 'rgb(26, 83, 255)', backgroundColor: 'rgba(26, 83, 255, 0.5)', fill: false }, ] },
                options: { responsive: true, maintainAspectRatio: false, scales: { yAxes: [{ ticks: { beginAtZero: true, callback: v => v.toLocaleString() } }] },
                    tooltips: { callbacks: { label: function(tooltipItem, data) { return data.datasets[tooltipItem.datasetIndex].label + ': ' + tooltipItem.yLabel.toLocaleString(); } } }
                }
            });
            this.$('.chart-toggle-btn[data-chart="invoice"]').removeClass('active').filter('[data-type="' + this.invoiceChartType + '"]').addClass('active');
        },
        _renderManhourChart: function(chartData) {
            if (this.manhourChart) { this.manhourChart.destroy(); }
            var formattedLabels = chartData.labels.map(label => moment(label, "YYYY-MM").format("MMM YYYY"));
            this.manhourChart = new Chart(this.$('#manhour_chart'), {
                type: this.manhourChartType, data: { labels: formattedLabels, datasets: [ { label: 'Plan Manhour', data: chartData.plan_data, borderColor: 'rgb(253, 220, 120)', backgroundColor: 'rgba(253, 220, 120, 0.5)', fill: false }, { label: 'Actual Manhour', data: chartData.actual_data, borderColor: 'rgb(233, 124, 48)', backgroundColor: 'rgba(233, 124, 48, 0.5)', fill: false }, ] },
                options: { responsive: true, maintainAspectRatio: false, scales: { yAxes: [{ ticks: { beginAtZero: true, callback: v => v.toLocaleString() } }] },
                    tooltips: { callbacks: { label: function(tooltipItem, data) { return data.datasets[tooltipItem.datasetIndex].label + ': ' + tooltipItem.yLabel.toLocaleString(); } } }
                }
            });
            this.$('.chart-toggle-btn[data-chart="manhour"]').removeClass('active').filter('[data-type="' + this.manhourChartType + '"]').addClass('active');
        },

        _getGlobalFilters: function () {
            var project_val = this.$('#db_project_filter').val();
            var employee_val = this.$('#db_employee_filter').val();
            var project_ids = (project_val && project_val !== 'all') ? [parseInt(project_val, 10)] : [];
            var employee_ids = (employee_val && employee_val !== 'all') ? [parseInt(employee_val, 10)] : [];
            var date_range_val = this.$('#db_date_range_picker').val();
            var date_from = false, date_to = false;
            if (date_range_val) {
                var dates = date_range_val.split(' - ');
                date_from = moment(dates[0], 'MM/DD/YYYY').format('YYYY-MM-DD');
                date_to = moment(dates[1], 'MM/DD/YYYY').format('YYYY-MM-DD');
            }
            return { date_from, date_to, project_ids, employee_ids, ratings: this.currentRatingFilters };
        },
        
        _renderFilters: function() {
            this._updateProjectFilterOptions();
            this._updateEmployeeFilterOptions();
            this.$('#db_project_filter').select2({ placeholder: "Filter by Project..." });
            this.$('#db_employee_filter').select2({ placeholder: "Filter by Employee..." });
            this.$('#db_project_filter').val('all').trigger('change.select2');
            this.$('#db_employee_filter').val('all').trigger('change.select2');
            this._onGlobalFilterChange();
            var date_picker = this.$('#db_date_range_picker');
            date_picker.daterangepicker({ autoUpdateInput: false, locale: { cancelLabel: 'Clear', format: 'MM/DD/YYYY' } });
            date_picker.on('apply.daterangepicker', (ev, picker) => { $(ev.currentTarget).val(picker.startDate.format('MM/DD/YYYY') + ' - ' + picker.endDate.format('MM/DD/YYYY')).trigger('change'); });
            date_picker.on('cancel.daterangepicker', (ev, picker) => $(ev.currentTarget).val('').trigger('change'));
            var rating_stars_html = this.filter_data.rating_options.map(opt => `<div class="rating-filter-item" title="${_.escape(opt.label)}" data-key="${opt.key}">${Array(parseInt(opt.key) + 2).join('<i class="fa fa-star"></i>')}</div>`).join('');
            this.$('.rating_filters_stars').html(rating_stars_html);
        },
        
        _updateProjectFilterOptions: function() {
            var $project_filter = this.$('#db_project_filter');
            var currentVal = $project_filter.val();
            $project_filter.empty();
            $project_filter.append(new Option('All My Projects', 'all'));
            if (this.filter_data && this.filter_data.projects) {
                this.filter_data.projects.forEach(p => $project_filter.append(new Option(p.name, p.id)));
            }
            $project_filter.val(currentVal);
        },
        _updateEmployeeFilterOptions: function() {
            var $employee_filter = this.$('#db_employee_filter');
            var currentVal = $employee_filter.val();
            $employee_filter.empty();
            $employee_filter.append(new Option('All Employees', 'all'));
            if (this.filter_data && this.filter_data.employees) {
                this.filter_data.employees.forEach(e => $employee_filter.append(new Option(e.name, e.id)));
            }
            $employee_filter.val(currentVal);
        },

        _updateProgressVisualIndicators: function() {
            var totalPages = Math.ceil(this.progressTotalRecords / this.progressLimit) || 1;
            var pageInfo = `Page ${this.progressCurrentPage} of ${totalPages}`;
            if (this.progressTotalRecords === 0) { pageInfo = "No records found"; }
            this.$('#progress_page_info').text(pageInfo);
            this.$('#progress_prev_page_btn').prop('disabled', this.progressCurrentPage === 1);
            this.$('#progress_next_page_btn').prop('disabled', this.progressCurrentPage >= totalPages);
        },
        
        _renderReviewTable: function(data) {
            this.reviewTotalRecords = data.total_employees;
            this.$('#review_list_body').html(QWeb.render('rnet_project_management_dashboard.RecentReviewsTable', {
                widget: this,
                reviews: data.employee_ratings
            }));
            this._updateReviewVisualIndicators();
        },
        
        _updateReviewVisualIndicators: function() {
            var totalPages = Math.ceil(this.reviewTotalRecords / this.reviewLimit) || 1;
            var pageInfo = `Page ${this.reviewCurrentPage} of ${totalPages} (${this.reviewTotalRecords} employees)`;
            if (this.reviewTotalRecords === 0) { pageInfo = "No records found"; }
            this.$('#page_info').text(pageInfo);
            this.$('#prev_page_btn').prop('disabled', this.reviewCurrentPage === 1);
            this.$('#next_page_btn').prop('disabled', this.reviewCurrentPage >= totalPages);
            this.$('.sortable_header').removeClass('sort_asc sort_desc').find('.fa').attr('class', 'fa fa-sort');
            var sortField = this.reviewCurrentSort.split(' ')[0];
            var direction = this.reviewCurrentSort.endsWith('desc') ? 'desc' : 'asc';
            this.$(`.sortable_header[data-sort="${sortField}"]`).addClass(`sort_${direction}`).find('.fa').attr('class', `fa fa-sort-${direction}`);
            this.$('.rating-filter-item').removeClass('active');
            this.currentRatingFilters.forEach(key => this.$(`.rating-filter-item[data-key="${key}"]`).addClass('active'));
        },
        
        _onProjectProgressRowClick: function(ev) {
            ev.preventDefault();
            var record_id = $(ev.currentTarget).data('id');
            if (record_id) {
                this.do_action({
                    type: 'ir.actions.act_window',
                    res_model: 'project.progress.plan',
                    res_id: record_id,
                    views: [[false, 'form']],
                    target: 'current',
                });
            }
        },
        _onGlobalFilterChange: function () {
            this.progressCurrentPage = 1;
            // This function now ONLY reloads the global components
            this._loadAllData();
        },
        _onFilterChange: function () {
            this.reviewCurrentPage = 1;
            this.progressCurrentPage = 1;
            this._loadAllData();
        },
        _onRatingClick: function (ev) {
            var ratingKey = $(ev.currentTarget).data('key').toString();
            var index = this.currentRatingFilters.indexOf(ratingKey);
            index > -1 ? this.currentRatingFilters.splice(index, 1) : this.currentRatingFilters.push(ratingKey);
            this._onFilterChange();
        },
        _onSortClick: function(ev) {
            var sortField = $(ev.currentTarget).data('sort');
            var direction = this.reviewCurrentSort.endsWith('desc') ? 'asc' : 'desc';
            this.reviewCurrentSort = `${sortField} ${this.reviewCurrentSort.startsWith(sortField) ? direction : 'asc'}`;
            this._onFilterChange();
        },
        _onPrevPageClick: function() {
            if (this.reviewCurrentPage > 1) {
                this.reviewCurrentPage--;
                this._loadAllData();
            }
        },
        _onNextPageClick: function() {
            if (this.reviewCurrentPage < Math.ceil(this.reviewTotalRecords / this.reviewLimit)) {
                this.reviewCurrentPage++;
                this._loadAllData();
            }
        },
        _onToggleAllProjects: function(ev) {
            ev.preventDefault();
            var self = this;
            this.showAllProjects = !this.showAllProjects;
            this._fetchFilterData().then(function() {
                self._updateProjectFilterOptions();
                self.$('#db_project_filter').val(null).trigger('change');
            });
        },
        _onProgressPrevPageClick: function() {
            if (this.progressCurrentPage > 1) {
                this.progressCurrentPage--;
                this._loadAllData();
            }
        },
        _onProgressNextPageClick: function() {
            if (this.progressCurrentPage < Math.ceil(this.progressTotalRecords / this.progressLimit)) {
                this.progressCurrentPage++;
                this._loadAllData();
            }
        },

        _onReviewSearchInput: function() {
            this.reviewCurrentPage = 1;
            this._fetchReviewData();
        },
        _onRatingClick: function (ev) {
            this.reviewCurrentPage = 1;
            var ratingKey = $(ev.currentTarget).data('key').toString();
            var index = this.currentRatingFilters.indexOf(ratingKey);
            index > -1 ? this.currentRatingFilters.splice(index, 1) : this.currentRatingFilters.push(ratingKey);
            this._fetchReviewData();
        },
        _onSortClick: function(ev) {
            this.reviewCurrentPage = 1;
            var sortField = $(ev.currentTarget).data('sort');
            var direction = this.reviewCurrentSort.endsWith('desc') ? 'asc' : 'desc';
            this.reviewCurrentSort = `${sortField} ${this.reviewCurrentSort.startsWith(sortField) ? direction : 'asc'}`;
            this._fetchReviewData();
        },
        _onPrevPageClick: function() {
            if (this.reviewCurrentPage > 1) {
                this.reviewCurrentPage--;
                this._fetchReviewData();
            }
        },
        _onNextPageClick: function() {
            if (this.reviewCurrentPage < Math.ceil(this.reviewTotalRecords / this.reviewLimit)) {
                this.reviewCurrentPage++;
                this._fetchReviewData();
            }
        },
        _onNextPageClick: function() {
            if (this.reviewCurrentPage < Math.ceil(this.reviewTotalRecords / this.reviewLimit)) {
                this.reviewCurrentPage++;
                this._fetchReviewData();
            }
        },
    });

    core.action_registry.add('rnet_pm_dashboard', Dashboard);
    return Dashboard;
});