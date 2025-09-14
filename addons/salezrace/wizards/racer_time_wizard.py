# -*- coding: utf-8 -*-
from __future__ import annotations

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SalezRaceRacerTimeWizard(models.TransientModel):
    _name = "salezrace.racer.time.wizard"
    _description = "Edit Start/Finish Times"

    racer_id = fields.Many2one("salezrace.racer", required=True, readonly=True)
    start_time = fields.Datetime(string="Start Time")
    finish_time = fields.Datetime(string="Finish Time")
    final_time = fields.Char(string="Final Time", compute="_compute_final_time", readonly=True)

    @api.depends("start_time", "finish_time")
    def _compute_final_time(self):
        for w in self:
            w.final_time = False
            if w.start_time and w.finish_time and w.finish_time >= w.start_time:
                delta = fields.Datetime.to_datetime(w.finish_time) - fields.Datetime.to_datetime(w.start_time)
                total_seconds = int(delta.total_seconds())
                m, s = divmod(total_seconds, 60)
                w.final_time = f"{m:02d}:{s:02d}"

    def action_apply(self):
        """Write start/finish times back to the racer."""
        self.ensure_one()
        racer = self.racer_id
        vals = {}
        # Allow manager to set/clear either field
        vals["start_time"] = self.start_time or False
        vals["finish_time"] = self.finish_time or False
        racer.write(vals)
        return {"type": "ir.actions.act_window_close"}
