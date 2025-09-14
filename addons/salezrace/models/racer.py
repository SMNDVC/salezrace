# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import List, Tuple

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression 

class SalezRaceRacer(models.Model):
    """Racer registration model."""

    _name = "salezrace.racer"
    _description = "SalezRace Racer"
    _order = "id desc"  # newest first so new inline rows show on top

    first_name: fields.Char = fields.Char(required=True)
    last_name: fields.Char = fields.Char(required=True)
    age: fields.Integer = fields.Integer(required=True)
    gender: fields.Selection = fields.Selection(
        selection=[("male", "Male"), ("female", "Female")], required=True
    )
    # 0 = unassigned; positive integers are real race numbers
    racer_no: fields.Integer = fields.Integer(
        default=0,
        index=True,
        copy=False,
        help="0 means unassigned; use 'Assign Number' to get the next available number.",
    )
    start_time: fields.Datetime = fields.Datetime(readonly=True)
    finish_time: fields.Datetime = fields.Datetime(readonly=True)
    final_time: fields.Char = fields.Char(
        string="Final Time",
        compute="_compute_final_time",
        store=True,
        help="Computed as finish_time - start_time in mm:ss.",
    )
    email = fields.Char()
    search_key = fields.Char(
        string="Search Key",
        compute="_compute_search_key",
        store=True,
        index=True,
        help="Concatenation of First, Last, Age, Gender, and Racer No for easier searching",
    )

    @api.depends("first_name", "last_name", "age", "gender", "racer_no")
    def _compute_search_key(self):
        for rec in self:
            parts = []
            if rec.first_name:
                parts.append(rec.first_name.strip())
            if rec.last_name:
                parts.append(rec.last_name.strip())
            if rec.age:
                parts.append(str(rec.age))
            if rec.gender:
                parts.append(dict(rec._fields["gender"].selection).get(rec.gender, rec.gender))
            if rec.racer_no and rec.racer_no > 0:
                parts.append(f"#{rec.racer_no}")
            else:
                parts.append("no racer number")
            rec.search_key = ", ".join(parts) if parts else ""
        # NOTE: we allow multiple 0s, so we DO NOT put a SQL unique constraint on racer_no.
        # Uniqueness for positive numbers is enforced in Python below.
        _sql_constraints = [
            ("racer_no_unique", "unique(racer_no)", "Racer number must be unique."),
        ]


    category = fields.Selection(
        selection=[
            # Male categories
            ("MU6", "MU6"),
            ("M6", "M6"),
            ("M10", "M10"),
            ("M14", "M14"),
            ("M18", "M18"),
            ("M31", "M31"),
            ("M45", "M45"),
            # Female categories
            ("FU6", "FU6"),
            ("F6", "F6"),
            ("F10", "F10"),
            ("F14", "F14"),
            ("F18", "F18"),
            ("F31", "F31"),
            ("F45", "F45"),
        ],
        string="Category",
        compute="_compute_category",
        store=True,
        index=True,
        help="Computed race category like MU6, M6, M10... or FU6, F6, F10... based on age and gender.",
    )

    @api.depends("age", "gender")
    def _compute_category(self):
        def bucket(age: int) -> str | None:
            if age is None:
                return None
            if age < 6:
                return "U6"
            if 6 <= age <= 9:
                return "6"
            if 10 <= age <= 13:
                return "10"
            if 14 <= age <= 17:
                return "14"
            if 18 <= age <= 30:
                return "18"
            if 31 <= age <= 44:
                return "31"
            return "45"  # 45+

        for rec in self:
            if not rec.age or not rec.gender:
                rec.category = False
                continue

            b = bucket(rec.age)
            if not b:
                rec.category = False
                continue

            # prefix male/female
            prefix = "M" if rec.gender == "male" else "F"
            rec.category = f"{prefix}{b}"

    # -----------------------
    # CRUD
    # -----------------------
    @api.model_create_multi
    def create(self, vals_list: List[dict]) -> "SalezRaceRacer":
        """Create racers with validation:
        - Default racer_no to 0 if not provided.
        - Allow multiple 0s.
        - Validate integer and non-negative.
        """
        for vals in vals_list:
            if "racer_no" not in vals or vals.get("racer_no") in (None, ""):
                vals["racer_no"] = 0
            try:
                vals["racer_no"] = int(vals["racer_no"])
            except (TypeError, ValueError):
                raise ValidationError(_("Racer number must be an integer."))
            if vals["racer_no"] < 0:
                raise ValidationError(_("Racer number cannot be negative."))
        recs = super().create(vals_list)
        recs._check_racer_no_unique_nonzero()
        return recs

    def write(self, vals: dict) -> bool:
        res = super().write(vals)
        self._check_racer_no_unique_nonzero()
        return res

    def unlink(self) -> bool:
        # No bus notifications anymore; just delete.
        return super().unlink()

    def name_search(self, name="", args=None, operator="ilike", limit=100):
        args = args or []
        if not name:
            recs = self.search(args, limit=limit)
            return recs.name_get()

        domain_parts = [
            ("first_name", operator, name),
            ("last_name", operator, name),
        ]
        if name.isdigit():
            domain_parts.append(("racer_no", "=", int(name)))

        or_domain = []
        for i, cond in enumerate(domain_parts):
            if i:
                or_domain = ["|"] + or_domain
            or_domain += [cond]

        recs = self.search(expression.AND([args, or_domain]), limit=limit)
        return recs.name_get()

    # -----------------------
    # Constraints
    # -----------------------
    @api.constrains("racer_no")
    def _check_racer_no_unique_nonzero(self) -> None:
        """Ensure that for racer_no > 0, the number is unique. Allow multiple 0s."""
        for rec in self:
            if rec.racer_no and rec.racer_no > 0:
                dup = self.search_count([("id", "!=", rec.id), ("racer_no", "=", rec.racer_no)])
                if dup:
                    raise ValidationError(_("Racer number %s is already used.") % rec.racer_no)

    # -----------------------
    # Computations
    # -----------------------
    @api.depends("start_time", "finish_time")
    def _compute_final_time(self) -> None:
        """Compute mm:ss from finish_time - start_time."""
        for rec in self:
            rec.final_time = False
            if rec.start_time and rec.finish_time and rec.finish_time >= rec.start_time:
                delta = fields.Datetime.to_datetime(rec.finish_time) - fields.Datetime.to_datetime(rec.start_time)
                total_seconds = int(delta.total_seconds())
                minutes, seconds = divmod(total_seconds, 60)
                rec.final_time = f"{minutes:02d}:{seconds:02d}"

    @api.depends("first_name", "last_name", "racer_no")
    def _compute_display_name(self) -> None:
        """Compute display name as 'First Last (#<racer_no>)'."""
        for rec in self:
            number = rec.racer_no if rec.racer_no is not None else "?"
            rec.display_name = f"{(rec.first_name or '').strip()} {(rec.last_name or '').strip()} (#{number})".strip()

    # -----------------------
    # Helpers for numbering
    # -----------------------
    @api.model
    def _next_racer_no_locked(self) -> int:
        """
        Return max(racer_no) + 1 while holding a table-level lock to serialize
        concurrent assignments. This respects manual assignments naturally.
        """
        # Serialize concurrent "next number" computations
        self.env.cr.execute("LOCK TABLE salezrace_racer IN SHARE ROW EXCLUSIVE MODE")
        self.env.cr.execute("SELECT COALESCE(MAX(racer_no), 0) FROM salezrace_racer")
        current_max = self.env.cr.fetchone()[0] or 0
        return int(current_max) + 1

    # -----------------------
    # Actions
    # -----------------------
    def action_start(self) -> None:
        """Record the start time as the current server time.

        :raises UserError: if start_time is already set or racer_no is 0.
        """
        self.ensure_one()
        if self.racer_no == 0:
            raise UserError(_("Cannot start a racer with number 0. Please assign a number first."))
        if self.start_time:
            raise UserError(_("This racer has already started."))
        self.write({"start_time": fields.Datetime.now()})

    def action_finish_now(self) -> None:
        """Mark this racer as finished at server time 'now'."""
        self.ensure_one()
        if not self.start_time:
            raise UserError(_("This racer has not started yet."))
        if self.finish_time:
            raise UserError(_("This racer already has a finish time."))
        self.write({"finish_time": fields.Datetime.now()})

    def action_assign_number(self) -> None:
        """
        Assign the next available sequential number to records that have racer_no == 0.
        - Works in batch if multiple records are selected.
        - Atomic and robust against concurrent assignments.
        - Manual numbers are respected (we always compute from MAX in DB).
        """
        records = self.sorted("id")
        if not records:
            return

        to_assign = records.filtered(lambda r: not r.racer_no)
        if not to_assign:
            # Nothing to do (all already numbered)
            return

        # Single savepoint & table lock; compute once and assign consecutively.
        with self.env.cr.savepoint():
            base = self._next_racer_no_locked()
            next_no = base
            for rec in to_assign:
                rec.write({"racer_no": next_no})
                next_no += 1

    # -----------------------
    # Display helpers
    # -----------------------
    def name_get(self) -> List[Tuple[int, str]]:
        """Return display names matching the UI requirement."""
        result: List[Tuple[int, str]] = []
        for rec in self:
            number = rec.racer_no if rec.racer_no is not None else "?"
            name = f"{(rec.first_name or '').strip()} {(rec.last_name or '').strip()} (#{number})".strip()
            result.append((rec.id, name))
        return result

    def action_open_time_wizard(self):
        """Open the manager wizard for editing start/finish times."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Edit Times"),
            "res_model": "salezrace.racer.time.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_racer_id": self.id,
                "default_start_time": self.start_time,
                "default_finish_time": self.finish_time,
            },
        }

    def action_assign_smallest_numbers(self):
        """
        Assign the smallest positive unused integer to each selected racer that
        does not have a number yet (0 or False). Existing numbers are preserved.
        Fills gaps (1,2,3,...) and is deterministic (processes by id).

        Usage (from UI): select rows in the list view → Action ▸ Assign Numbers.
        """
        # Work only on unnumbered records; deterministic order
        to_fill = self.filtered(lambda r: not r.racer_no or r.racer_no <= 0).sorted(key=lambda r: r.id)
        if not to_fill:
            return True

        cr = self.env.cr
        # Lock the set of used numbers so concurrent actions won't collide
        cr.execute("""
            SELECT racer_no
              FROM salezrace_racer
             WHERE racer_no IS NOT NULL AND racer_no > 0
             FOR UPDATE
        """)
        used = {row[0] for row in cr.fetchall()}

        # Find the smallest free number and assign it, updating the set as we go
        next_candidate = 1
        for rec in to_fill:
            while next_candidate in used:
                next_candidate += 1
            rec.write({"racer_no": next_candidate})
            used.add(next_candidate)
            next_candidate += 1

        return True
