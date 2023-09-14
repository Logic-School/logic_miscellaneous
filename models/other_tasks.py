from odoo import models, fields, api
from datetime import date

class OtherTask(models.Model):
    _name = "logic.task.other"
    name = fields.Char(string="Name", required=True)
    description = fields.Text(string="Description")
    date = fields.Date(string="Date", default=date.today())
    manager = fields.Many2one('hr.employee',default = lambda self: self.env.user.employee_id.parent_id.id)
    task_creator = fields.Many2one('res.users',default = lambda self: self.env.user, string="Task Creator",readonly=True)
    task_creator_employee = fields.Many2one('hr.employee',default = lambda self: self.env.user.employee_id.id, string="Task Creator Employee",readonly=True)

    total_time = fields.Float(string="Time Taken")
    def _compute_is_creator_head(self):
        for record in self:
            if record.manager.user_id.id == self.env.user.id:
                record.is_creator_head = True
            else:
                record.is_creator_head = False
    is_creator_head = fields.Boolean(compute="_compute_is_creator_head")
    head_rating = fields.Selection(selection=[('0','No rating'),('1','Very Poor'),('2','Poor'),('3','Average'),('4','Good'),('5','Very Good')], string="Head Rating", default='0')

