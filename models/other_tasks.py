from odoo import models, fields, api
from datetime import date
import logging
from odoo.exceptions import UserError

class OtherTask(models.Model):
    _name = "logic.task.other"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Miscellaneous Task"

    name = fields.Char(string="Name", required=True)
    description = fields.Text(string="Description")
    date = fields.Date(string="Date", default=fields.Date.today())

    def _compute_manager_id(self):
        for record in self: 
            record.manager = record.task_creator_employee.parent_id.id
    manager = fields.Many2one('hr.employee',compute="_compute_manager_id")
    task_creator = fields.Many2one('res.users',default = lambda self: self.env.user, string="Task Creator",readonly=True)
    task_creator_employee = fields.Many2one('hr.employee',default = lambda self: self.env.user.employee_id.id, string="Task Creator Employee",readonly=True)
    state = fields.Selection(selection=[('draft','Draft'),('in_progress','In Progress'),('hold','On Hold'),('completed','Completed'),('cancel','Cancelled')])
    total_time = fields.Float(string="Time Taken")
    time_taken_days = fields.Integer(string="Days Taken")
    expected_days = fields.Integer(string="Expected Days")
    expected_time = fields.Float(string="Expected Time")
    remarks = fields.Text(string="Remarks")
    expected_completed_status = fields.Char(string="On Time Status", compute="_compute_expected_completed_difference")
    expected_completed_difference = fields.Float(string="Expected Completed Difference",compute="_compute_expected_completed_difference",store=True)
    
    @api.depends('expected_days','expected_time','time_taken_days','total_time')
    def _compute_expected_completed_difference(self):
        for record in self:
            expected_time = record.expected_days + (record.expected_time/24)
            taken_time = record.time_taken_days  + (record.total_time/24)
            difference = round(taken_time - expected_time,2)
            record.expected_completed_difference = difference

            if difference>0:
                record.expected_completed_status = "Delayed by "+ str(abs(difference)) + " Days"
            elif difference<0:
                record.expected_completed_status = "Ahead of Schedule by "+ str(abs(difference)) + " Days"
            else:
                record.expected_completed_status = "Completed exactly on expected time"
    department = fields.Many2one('hr.department',related='task_creator_employee.department_id',string="Department",store=True)

    date_completed = fields.Date(string="Date Completed")
    is_drag = fields.Boolean()
    def _compute_is_creator_head(self):
        for record in self:
            if record.manager.user_id.id == self.env.user.id or record.manager==False:
                record.is_creator_head = True
            else:
                record.is_creator_head = False
    is_creator_head = fields.Boolean(compute="_compute_is_creator_head")
    head_rating = fields.Selection(selection=[('0','No rating'),('1','Very Poor'),('2','Poor'),('3','Average'),('4','Good'),('5','Very Good')], string="Head Rating", default='0')

    @api.model
    def create(self,vals):
        vals['state'] = 'draft'
        return super(OtherTask,self).create(vals)
    
    def write(self,vals):
        if vals.get('state'):
            if vals['state']!=self.state:
                new_status = dict(self._fields['state']._description_selection(self.env))[vals['state']]
                previous_status = dict(self._fields['state']._description_selection(self.env))[self.state]
                self.message_post(body=f"Status Changed: {previous_status} -> {new_status}")
                
                if vals['state'] == 'completed':
                    vals['date_completed'] = fields.Date.today()
                else:
                    vals['date_completed'] = False
   
        return super(OtherTask,self).write(vals)

    
    # @api.onchange('state')
    # def on_state_change(self):
    #     logger = logging.getLogger("Test")
    #     logger.error(self._origin)
    #     previous_state = self._origin['state']
    #     previous_status = dict(self._fields['state']._description_selection(self.env))[previous_state]
    #     new_status = dict(self._fields['state']._description_selection(self.env))[self.state]
    #     self.message_post(body=f"Status Changed: {previous_status} -> {new_status}")

    def action_in_progress(self):
        # current_status = dict(self._fields['state']._description_selection(self.env))[self.state]

        # self.message_post(body=f"Status Changed: {current_status} -> In Progress")
        self.state = "in_progress"


    def action_hold(self):
        # current_status = dict(self._fields['state']._description_selection(self.env))[self.state]

        # self.message_post(body=f"Status Changed: {current_status} -> On Hold")
        self.state = "hold"


    def action_cancel(self):
        # current_status = dict(self._fields['state']._description_selection(self.env))[self.state]


        # self.message_post(body=f"Status Changed: {current_status} -> Cancelled")
        self.state = "cancel"


    def action_complete(self):
        # current_status = dict(self._fields['state']._description_selection(self.env))[self.state]

        # self.message_post(body=f"Status Changed: {current_status} -> Completed")
        self.state = "completed"
        self.date_completed = fields.Date.today()

    def action_ask_head(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Ask Question',
            'res_model': 'task.other.ask.wizard',
            'view_mode': 'form',
            'target': 'new',
            # 'context': {'default_action_type':'assign'}
        }