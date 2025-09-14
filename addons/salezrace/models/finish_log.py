# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import List, Optional

from odoo import api, fields, models, _
from odoo.exceptions import UserError


GENDER_SELECTION = [("male", "Male"), ("female", "Female")]


class SalezRaceFinishLog(models.Model):
    """Running log of finish timestamps and assignment to racers.

    Users press 'Log time' to create a row (server time).
    Then they input a racer number; the row resolves the racer and allows assignment.
    """

    _name = "salezrace.finish.log"
    _description = "SalezRace Finish Log"
    _order = "time desc, id desc"

    time: fields.Datetime = fields.Datetime(required=True)
    racer_no_input: fields.Integer = fields.Integer(
        help="Type racer number to resolve the racer."
    )
    racer_id: fields.Many2one = fields.Many2one(
        "salezrace.racer",
        compute="_compute_racer_id",
        inverse="_inverse_racer_id",
        store=True,
        readonly=False,
    )

    # Helper (transient) fields for display in the Finish table
    first_name: fields.Char = fields.Char(compute="_compute_helper_fields")
    last_name: fields.Char = fields.Char(compute="_compute_helper_fields")
    age: fields.Integer = fields.Integer(compute="_compute_helper_fields")
    gender: fields.Selection = fields.Selection(
        selection=GENDER_SELECTION, compute="_compute_helper_fields"
    )

    assigned: fields.Boolean = fields.Boolean(default=False)
    assigned_time: fields.Datetime = fields.Datetime()

    @api.depends("racer_no_input")
    def _compute_racer_id(self) -> None:
        """Resolve racer_id from racer_no_input and store it."""
        Racer = self.env["salezrace.racer"]
        for rec in self:
            rec.racer_id = False
            if rec.racer_no_input:
                rec.racer_id = Racer.search(
                    [("racer_no", "=", rec.racer_no_input)], limit=1
                )

    def _inverse_racer_id(self) -> None:
        """Keep racer_no_input in sync when racer_id is set."""
        for rec in self:
            rec.racer_no_input = rec.racer_id.racer_no if rec.racer_id else False

    @api.depends("racer_id", "racer_id.first_name", "racer_id.last_name", "racer_id.age", "racer_id.gender")
    def _compute_helper_fields(self) -> None:
        """Compute helper display fields from racer_id."""
        for rec in self:
            rec.first_name = rec.racer_id.first_name or False
            rec.last_name = rec.racer_id.last_name or False
            rec.age = rec.racer_id.age if rec.racer_id else False
            rec.gender = rec.racer_id.gender or False

    @api.model
    def action_log_now(self) -> int:
        """Create a new log row with the current server time.

        :return: ID of the created log row.
        """
        rec = self.create({"time": fields.Datetime.now()})
        return rec.id

    def action_assign(self) -> None:
        """Assign the log's time to the related racer's finish_time.

        Resolution: prefer racer_id; if missing, try racer_no_input.
        :raises UserError: if no racer resolved or racer already has finish_time.
        """
        self.ensure_one()
        racer = self.racer_id
        if not racer and self.racer_no_input:
            racer = self.env["salezrace.racer"].search(
                [("racer_no", "=", self.racer_no_input)], limit=1
            )
        if not racer:
            raise UserError(_("No racer resolved for this log row."))

        if racer.finish_time:
            raise UserError(_("This racer already has a finish time."))

        # Write finish_time to racer and mark this log row as assigned.
        now = fields.Datetime.now()
        racer.write({"finish_time": self.time})
        self.write({"assigned": True, "assigned_time": now})
