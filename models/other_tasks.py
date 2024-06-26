from odoo import models, fields, api
from datetime import date
import logging
from odoo.exceptions import UserError


class OtherTask(models.Model):
    _name = "logic.task.other"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Miscellaneous Task"
    _order = 'id desc'

    name = fields.Char(string="Name", required=True)
    description = fields.Text(string="Description")

    date = fields.Date(string="Date", default=lambda self: fields.Date.context_today(self))

    date = fields.Date(string="Date", default=date.today())
    tags_id = fields.Many2many('project.tags', string="Tags")
    task_types = fields.Selection(selection=[('meeting', 'Meeting'), ('telephone_discussion', 'Telephone Discussion'),
                                             ('clerical_works', 'Clerical Works'),
                                             ('day_to_day_works', 'Day To Day Works'),
                                             ('batch_related_works', 'Batch Related Works'),
                                             ('other', 'Other')], string="Task Type",
                                  required=1)
    meeting_type = fields.Selection(selection=[('internal', 'Internal'), ('external', 'External')],
                                    string="Meeting Type")
    meeting_ids = fields.Many2many('hr.employee', string="Meeting With")
    meeting = fields.Selection(selection=[('online', 'Online'), ('offline', 'Offline')], string="Meeting")
    meeting_with = fields.Char(string="Meeting With")

    # telephone discussion
    discussion_type = fields.Selection(selection=[('internal', 'Internal'), ('external', 'External')],
                                       string="Discussion Type")
    discussion_with = fields.Char(string="Discussion With")
    discussion_ids = fields.Many2many('res.users', string="Discussion With")
    discussion_duration = fields.Float(string="Discussion Duration")

    # clerical works
    clerical_work_type = fields.Selection(
        selection=[('technical', 'Technical'), ('documentation', 'Documentation'), ('communication', 'Communication')],
        string="Work Type")

    # day to day works
    day_to_day_work_type = fields.Selection(
        selection=[('communication_with_student', 'Communication With Student'), ('mail', 'Mail'),
                   ('whatsapp', 'Whatsapp'), ('odoo', 'Odoo')], string="Work Type")

    # batch related works
    batch_related_work_type = fields.Selection(
        selection=[('attendance', 'Attendance'), ('class_scheduling', 'Class Scheduling'),
                   ('communication', 'Communication')], string="Work Type"
    )
    batch_id = fields.Many2one('logic.base.batch', string="Batch")

    def _compute_manager_id(self):
        for record in self:
            record.manager = record.task_creator_employee.parent_id.id

    manager = fields.Many2one('hr.employee', compute="_compute_manager_id")
    task_creator = fields.Many2one('res.users', default=lambda self: self.env.user, string="Task Creator",
                                   readonly=True)
    task_creator_employee = fields.Many2one('hr.employee', default=lambda self: self.env.user.employee_id.id,
                                            string="Task Creator Employee", readonly=True)
    state = fields.Selection(
        selection=[('draft', 'Draft'), ('in_progress', 'In Progress'), ('hold', 'On Hold'), ('completed', 'Completed'),
                   ('cancel', 'Cancelled'), ('achievement', 'Achievement')], )
    total_time = fields.Float(string="Time Taken")
    time_taken_days = fields.Integer(string="Days Taken")
    expected_days = fields.Integer(string="Expected Days")
    expected_time = fields.Float(string="Expected Time")
    expected_completion = fields.Datetime(string="Expected Completion")
    remarks = fields.Text(string="Remarks")
    expected_completed_status = fields.Char(string="On Time Status", compute="_compute_expected_completed_difference")
    expected_completed_difference = fields.Float(string="Time Difference",
                                                 compute="_compute_expected_completed_difference", store=True,
                                                 digits=(12, 4))
    completion_datetime = fields.Datetime(string="Completed On")
    delayed_activity_send = fields.Boolean(string="Activty Send to Manager for Delay")
    delay_approved = fields.Boolean(string="Delay Approved")
    task_submission_status = fields.Selection(compute="_compute_task_submission_status", string="Submission Status",
                                              selection=[('on_time', 'On Time'), ('delayed', 'Delayed'),
                                                         ('delayed_approved', 'Delayed (Approved By Head)')], )

    def action_change_on_time_status_all(self):
        records = self.env['logic.task.other'].sudo().search([])
        for record in records:
            # expected_time = record.expected_days + (record.expected_time/24)
            # taken_time = record.time_taken_days  + (record.total_time/24)
            if record.completion_datetime and record.expected_completion:

                if record.completion_datetime > record.expected_completion:
                    difference = record.completion_datetime - record.expected_completion
                else:
                    difference = record.expected_completion - record.completion_datetime

                days_difference, hours_difference, minutes_difference = abs(difference.days), abs(
                    difference.seconds // 3600), abs(difference.seconds // 60 % 60)
                record.expected_completed_difference = days_difference + (hours_difference / 24) + (
                        minutes_difference / 1440)
                if record.completion_datetime > record.expected_completion:
                    record.expected_completed_status = "Delayed by " + str(days_difference) + " Days, " + str(
                        hours_difference) + " Hours, and " + str(minutes_difference) + " Minutes"
                    record.expected_completed_difference = abs(record.expected_completed_difference)

                elif record.completion_datetime < record.expected_completion:
                    record.expected_completed_status = "Ahead of schedule by " + str(
                        abs(days_difference)) + " Days, " + str(abs(hours_difference)) + " Hours, and " + str(
                        abs(minutes_difference)) + " Minutes"
                    record.expected_completed_difference = - abs(record.expected_completed_difference)

                else:
                    record.expected_completed_status = "Completed exactly on expected time"
            else:
                record.expected_completed_status = ''

    def _compute_task_submission_status(self):
        for record in self:
            record.task_submission_status = ''
            if record.completion_datetime and record.expected_completion:
                if record.completion_datetime <= record.expected_completion:
                    record.task_submission_status = 'on_time'
                else:
                    if record.delay_approved:
                        record.task_submission_status = 'delayed_approved'
                    else:
                        record.task_submission_status = 'delayed'

    @api.depends('completion_datetime', 'expected_completion')
    def _compute_expected_completed_difference(self):
        heads = self.env['hr.department'].sudo().search([])
        head = []
        for i in heads:
            if i.manager_id:
                print(i.manager_id.name,'manager')
                head.append(i.manager_id.user_id.id)

        logger = logging.getLogger("Debugger: ")
        for record in self:
            record.expected_completed_status = False
            record.expected_completed_difference = False

            # expected_time = record.expected_days + (record.expected_time/24)
            # taken_time = record.time_taken_days  + (record.total_time/24)
            if record.completion_datetime and record.expected_completion:
                if self.env.user.id in head:
                    record.expected_completed_status = ''
                else:
                    if record.completion_datetime > record.expected_completion:
                        difference = record.completion_datetime - record.expected_completion
                    else:
                        difference = record.expected_completion - record.completion_datetime

                    days_difference, hours_difference, minutes_difference = abs(difference.days), abs(
                        difference.seconds // 3600), abs(difference.seconds // 60 % 60)
                    record.expected_completed_difference = days_difference + (hours_difference / 24) + (
                            minutes_difference / 1440)
                    logger.error("days:" + str(days_difference) + " hrs: " + str(hours_difference) + "mins: " + str(
                        minutes_difference))
                    if record.completion_datetime > record.expected_completion:
                        record.expected_completed_status = "Delayed by " + str(days_difference) + " Days, " + str(
                            hours_difference) + " Hours, and " + str(minutes_difference) + " Minutes"
                        record.expected_completed_difference = abs(record.expected_completed_difference)

                    elif record.completion_datetime < record.expected_completion:
                        record.expected_completed_status = "Ahead of schedule by " + str(
                            abs(days_difference)) + " Days, " + str(abs(hours_difference)) + " Hours, and " + str(
                            abs(minutes_difference)) + " Minutes"
                        record.expected_completed_difference = - abs(record.expected_completed_difference)

                    else:
                        record.expected_completed_status = "Completed exactly on expected time"
            else:
                record.expected_completed_status = ''

    department = fields.Many2one('hr.department', related='task_creator_employee.department_id', string="Department",
                                 store=True)

    date_completed = fields.Date(string="Date Completed")
    is_drag = fields.Boolean()

    def _compute_is_creator_head(self):
        for record in self:
            if record.task_creator_employee.parent_id.user_id.id == self.env.user.id or record.task_creator_employee.parent_id.user_id.id == False:
                record.is_creator_head = True
            else:
                record.is_creator_head = False

    is_creator_head = fields.Boolean(compute="_compute_is_creator_head")
    head_rating = fields.Selection(
        selection=[('0', 'No rating'), ('1', 'Very Poor'), ('2', 'Poor'), ('3', 'Average'), ('4', 'Good'),
                   ('5', 'Very Good')], string="Head Rating", default='0')

    def _compute_is_hr_manager(self):
        for record in self:
            record.is_hr_manager = self.env.user.has_group('logic_miscellaneous.group_logic_other_task_hr_manager')

    is_hr_manager = fields.Boolean(compute="_compute_is_hr_manager")
    badge = fields.Selection([('bronze', 'Bronze'), ('silver', 'Silver'), ('gold', 'Gold')], string="Badge")

    def action_add_to_achievement(self):
        self.env['logic.achievements'].sudo().create({
            'misc_id': self.id,
            'name': self.name,
            'department_id': self.department.id,
            'task_types': self.task_types,
            'date': self.date,
            'tags_id': self.tags_id.ids,
            'description': self.description,
            'owner_id': self.task_creator.id,
            'manager_id': self.manager.id,
            'expected_completion': self.expected_completion,
            'completed_on': self.completion_datetime,
            'time_difference': self.expected_completed_difference,
            'expected_completed_status': self.expected_completed_status,
            'remarks': self.remarks,
            'meeting': self.meeting,
            'meeting_type': self.meeting_type,
            'discussion_type': self.discussion_type,
            'discussion_duration': self.discussion_duration,
            'clerical_work_type': self.clerical_work_type,
            'day_to_day_work_type': self.day_to_day_work_type,
            'batch_related_work_type': self.batch_related_work_type,
            'batch_id': self.batch_id.id,

        })
        print("add to achievement")
        self.added_achievement = True
        self.state = 'achievement'

    added_achievement = fields.Boolean(default=False)

    @api.onchange('expected_completion')
    def on_expected_completion(self):
        if self.expected_completion:
            self.expected_completion = self.expected_completion.replace(second=0, microsecond=0)

    @api.model
    def create(self, vals):
        vals['state'] = 'draft'
        return super(OtherTask, self).create(vals)

    def write(self, vals):
        if vals.get('state'):
            if vals['state'] != self.state:
                new_status = dict(self._fields['state']._description_selection(self.env))[vals['state']]
                previous_status = dict(self._fields['state']._description_selection(self.env))[self.state]
                self.message_post(body=f"Status Changed: {previous_status} -> {new_status}")

                if vals['state'] == 'completed':
                    vals['date_completed'] = fields.Date.context_today(self)
                else:
                    vals['date_completed'] = False

        return super(OtherTask, self).write(vals)

    # @api.onchange('state')
    # def on_state_change(self):
    #     logger = logging.getLogger("Test")
    #     logger.error(self._origin)
    #     previous_state = self._origin['state']
    #     previous_status = dict(self._fields['state']._description_selection(self.env))[previous_state]
    #     new_status = dict(self._fields['state']._description_selection(self.env))[self.state]
    #     self.message_post(body=f"Status Changed: {previous_status} -> {new_status}")
    def check_task_delayed(self):
        tasks = self.env['logic.task.other'].sudo().search(
            [('state', '=', 'completed'), ('expected_completion', '!=', False), ('completion_datetime', '!=', False),
             ('delayed_activity_send', '=', False)])
        # for task in tasks:
        #     if task.expected_completion < task.completion_datetime:
        #         task.activity_schedule('logic_miscellaneous.mail_activity_type_misc_task_delayed',
        #                                user_id=task.task_creator.employee_id.parent_id.user_id.id,
        #                                summary=f'To Approve: Delayed Task by {task.task_creator.name}')
        #         task.write({
        #             'delayed_activity_send': True
        #         })

    def action_approve_delay(self):
        delayed_activity = self.activity_ids.filtered(
            lambda activity: activity.activity_type_id.name == "Miscellaneous Task Delayed")
        delayed_activity.unlink()
        self.message_post(body=f"Task Delay Approved by Manager")
        self.delay_approved = True

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
        self.date_completed = fields.Date.context_today(self)
        self.completion_datetime = (fields.Datetime.now()).replace(second=0, microsecond=0)
        return {
            'effect': {
                'fadeout': 'slow',
                'message': 'Completed',
                'type': 'rainbow_man',
            }
        }

    def action_ask_head(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Ask Question',
            'res_model': 'task.other.ask.wizard',
            'view_mode': 'form',
            'target': 'new',
            # 'context': {'default_action_type':'assign'}
        }
