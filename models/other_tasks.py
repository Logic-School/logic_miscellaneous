from odoo import models, fields, api
from datetime import date

class OtherTask(models.Model):
    _name = "logic.task.other"
    name = fields.Char(string="Name", required=True)
    description = fields.Text(string="Description")
    date = fields.Date(string="Date", default=date.today())
    manager = fields.Many2one('hr.employee',default = lambda self: self.env.user.employee_id.parent_id.id)
    task_creator = fields.Many2one('res.users',default = lambda self: self.env.user, string="Task Creator")
    total_time = fields.Float(string="Time Taken")

