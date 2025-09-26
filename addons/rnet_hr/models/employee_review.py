from odoo import api, fields, models, _
from odoo.exceptions import UserError

class HrEmployeeReview(models.Model):
    _name = "hr.employee.review"
    _inherit = ['mail.thread', 'mail.activity.mixin'] 
    _description = "Review Campaign"
    _order = "date desc"

    # --- All fields are correct and do not need to be changed ---
    name = fields.Char(string="Campaign Name", required=True, tracking=True, default="New Review Campaign")
    date = fields.Date(string="Date", default=fields.Date.context_today, tracking=True, required=True)
    state = fields.Selection([('draft', 'Draft'), ('in_progress', 'In Progress'), ('done', 'Done')], string='Status', default='draft', tracking=True)
    project_id = fields.Many2one('project.project', string="Project Context", tracking=True)
    employee_to_review_ids = fields.Many2many('hr.employee', 'review_campaign_employee_rel', 'campaign_id', 'employee_id', string="Employees to Review", domain=[('status_karyawan.name', '=', 'PKWT Project')])
    reviewer_ids = fields.Many2many('hr.employee', 'review_campaign_reviewer_rel', 'campaign_id', 'reviewer_id', string="Designated Reviewers")
    review_line_ids = fields.One2many('hr.employee.review.line', 'review_id', string="Feedback Lines")
    company_id = fields.Many2one('res.company', 'Company',)

    @api.onchange('project_id')
    def _onchange_project_id(self):
        # This onchange is correct and does not need to be changed
        if self.project_id and self.project_id.manpower_line_ids:
            self.employee_to_review_ids = self.project_id.manpower_line_ids.mapped('employee_id')
        else:
            self.employee_to_review_ids = False
    
    # --- THIS METHOD CONTAINS THE FINAL, CORRECTED LOGIC ---
    @api.multi
    def action_generate_review_lines(self):
        self.ensure_one()
        if not self.employee_to_review_ids or not self.reviewer_ids:
            raise UserError(_("You must have at least one 'Employee to Review' and one 'Designated Reviewer' before generating lines."))

        # 1. Get a set of all (employee_id, reviewer_id) pairs that SHOULD exist
        all_required_pairs = set(
            (emp.id, rev.id) for emp in self.employee_to_review_ids for rev in self.reviewer_ids
        )

        # 2. Use sudo() to bypass the record rule and get a complete, unfiltered list of ALL existing lines.
        #    This is the crucial step that prevents the crash for non-admin users.
        existing_pairs = set(
            (line.employee_id.id, line.reviewer_id.id) for line in self.sudo().review_line_ids
        )
        
        # 3. Calculate which pairs are missing
        missing_pairs = all_required_pairs - existing_pairs

        # 4. Create new lines ONLY for the missing pairs
        lines_to_create = []
        for emp_id, rev_id in missing_pairs:
            lines_to_create.append({
                'review_id': self.id,
                'employee_id': emp_id,
                'reviewer_id': rev_id,
            })
        
        if lines_to_create:
            # Use sudo() again here to ensure the user has the rights to create the lines,
            # as defined by the logic of this button.
            self.env['hr.employee.review.line'].sudo().create(lines_to_create)
        
        return True


class HrEmployeeReviewLine(models.Model):
    # This class is correct and does not need any changes
    _name = "hr.employee.review.line"
    _description = "Employee Review Feedback Line"
    _order = "employee_id, reviewer_id"

    review_id = fields.Many2one('hr.employee.review', string="Campaign", required=True, ondelete='cascade')
    employee_id = fields.Many2one('hr.employee', string="Employee Being Reviewed", required=True)
    reviewer_id = fields.Many2one('hr.employee', string="Reviewer", required=True)
    job_id = fields.Many2one('hr.job', string='Job Position', related='employee_id.job_id', store=True, readonly=True)
    rating = fields.Selection([
        ('0', '1 - Poor'), ('1', '2 - Needs Improvement'), ('2', '3 - Meets Expectations'),
        ('3', '4 - Exceeds Expectations'), ('4', '5 - Outstanding')
    ], string="Rating", required=False)
    description = fields.Text(string="Feedback Notes")

    _sql_constraints = [
        ('employee_reviewer_review_uniq', 'unique(review_id, employee_id, reviewer_id)', 
         'A reviewer can only submit one feedback for this employee within this campaign!')
    ]