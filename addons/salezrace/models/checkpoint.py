# -*- coding: utf-8 -*-
from odoo import fields, models

class SalezRaceCheckpoint(models.Model):
    _name = "salezrace.checkpoint"
    _description = "SalezRace Checkpoint"
    _order = "sequence"

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
