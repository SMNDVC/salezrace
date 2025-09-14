from odoo import api, fields, models

class ResUsers(models.Model):
    _inherit = 'res.users'

    salezrace_role = fields.Selection(
        selection=[('registration','Registration'),
                   ('start_finish','Start/Finish'),
                   ('manager','Manager')],
        string='SalezRace Role',
        compute='_compute_salezrace_role',
        inverse='_inverse_salezrace_role',
        store=False,
    )

    def _compute_salezrace_role(self):
        gr = self.env.ref
        g_reg = gr('salezrace.group_salezrace_registration', raise_if_not_found=False)
        g_sf  = gr('salezrace.group_salezrace_start_finish', raise_if_not_found=False)
        g_mgr = gr('salezrace.group_salezrace_manager', raise_if_not_found=False)
        for user in self:
            role = False
            if g_mgr and g_mgr in user.groups_id:
                role = 'manager'
            elif g_sf and g_sf in user.groups_id:
                role = 'start_finish'
            elif g_reg and g_reg in user.groups_id:
                role = 'registration'
            user.salezrace_role = role

    def _inverse_salezrace_role(self):
        gr = self.env.ref
        groups = self.env['res.groups']
        g_reg = gr('salezrace.group_salezrace_registration', raise_if_not_found=False) or groups
        g_sf  = gr('salezrace.group_salezrace_start_finish', raise_if_not_found=False) or groups
        g_mgr = gr('salezrace.group_salezrace_manager', raise_if_not_found=False) or groups
        all_roles = g_reg | g_sf | g_mgr

        for user in self:
            # remove all three (mutually exclusive)
            user.groups_id -= all_roles
            # add selected one
            if user.salezrace_role == 'registration':
                user.groups_id |= g_reg
            elif user.salezrace_role == 'start_finish':
                user.groups_id |= g_sf
            elif user.salezrace_role == 'manager':
                user.groups_id |= g_mgr
