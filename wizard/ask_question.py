from odoo import models,fields,api

class TaskAskQuestion(models.Model):
    _name="task.other.ask.wizard"
    question = fields.Html(string="Question")
    task_id = fields.Many2one("logic.task.other",string="Task ID",default=lambda self: self.env.context.get('active_id'))

    def action_head_ask(self):
        self.task_id.activity_schedule('logic_miscellaneous.mail_activity_type_misc_task', user_id=self.task_id.task_creator.id,
                               summary=f'Query from {self.task_id.manager.name}',
                               note=self.question)