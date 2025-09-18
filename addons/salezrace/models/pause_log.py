# -*- coding: utf-8 -*-
from odoo import fields, models, api
from datetime import timedelta

class SalezRacePauseLog(models.Model):
    _name = "salezrace.pause.log"
    _description = "SalezRace Pause Log"

    racer_id = fields.Many2one("salezrace.racer", required=True, ondelete="cascade")
    checkpoint_id = fields.Many2one("salezrace.checkpoint", required=True, ondelete="cascade")
    start_time = fields.Datetime()
    end_time = fields.Datetime()
    user_id = fields.Many2one("res.users", string="Started By", default=lambda self: self.env.user)
    session_id = fields.Char("Session ID")
    is_invalid = fields.Boolean(default=False)
    is_custom = fields.Boolean(default=False)

    duration = fields.Float(string="Duration (s)", compute="_compute_duration", store=True)

    @api.depends("start_time", "end_time")
    def _compute_duration(self):
        for log in self:
            if log.start_time and log.end_time:
                delta = log.end_time - log.start_time
                log.duration = delta.total_seconds()
            else:
                log.duration = 0

    @api.model
    def _cron_revert_old_pauses(self):
        one_minute_ago = fields.Datetime.now() - timedelta(minutes=1)
        old_pauses = self.search([
            ("start_time", "<=", one_minute_ago),
            ("end_time", "=", False),
        ])
        old_pauses.unlink()
