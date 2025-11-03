# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class GanttTaskDeleteWizard(models.TransientModel):
    _name = 'gantt.task.delete.wizard'
    _description = 'Gantt Task Cascade Delete Confirmation'

    task_id = fields.Many2one('gantt.task', string='Task to Delete', required=True, readonly=True)
    task_count = fields.Integer(string='Total Tasks to Delete', readonly=True)
    task_tree = fields.Text(string='Task Hierarchy', readonly=True)
    confirm = fields.Boolean(string='I understand this action cannot be undone')

    def action_confirm_delete(self):
        """Confirm and execute cascade delete"""
        self.ensure_one()
        if not self.confirm:
            raise models.UserError(_('Please confirm that you understand this action cannot be undone.'))

        if self.task_id:
            # Perform cascade delete
            self.task_id.action_delete_cascade_confirmed()

        return {'type': 'ir.actions.act_window_close'}

    def action_cancel(self):
        """Cancel the delete operation"""
        return {'type': 'ir.actions.act_window_close'}
