/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillStart } from "@odoo/owl";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

export class StartClientAction extends Component {
    static template = "salezrace.StartClientAction";

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.dialog = useService("dialog");

        this.state = useState({
            racerNo: "",
            racer: null,
            loading: false,
            error: null,          // keep null style from your first file
            // additions from the second file:
            recentStarted: [],
            nextToStart: [],
        });

        this._debounceTimer = null;

        // new: pre-load the two summary lists on mount
        onWillStart(async () => {
            await this.fetchLists();
        });
    }

    // ---------- Derived ----------
    get canStart() {
        // from the second file: require a number and no start_time
        const r = this.state.racer;
        return !!(r && r.racer_no && r.racer_no !== 0 && !r.start_time);
    }

    // ---------- Data fetch ----------
    async fetchLists() {
        try {
            const started = await this.orm.searchRead(
                "salezrace.racer",
                [["start_time", "!=", false]],
                ["id", "racer_no", "first_name", "last_name", "start_time"],
                { order: "start_time desc", limit: 10 }
            );
            const waiting = await this.orm.searchRead(
                "salezrace.racer",
                [["start_time", "=", false]],
                ["id", "racer_no", "first_name", "last_name"],
                { order: "racer_no asc", limit: 10 }
            );
            this.state.recentStarted = started;
            this.state.nextToStart = waiting;
        } catch (e) {
            this.notification.add(e?.message || "Failed to load summary lists.", { type: "danger" });
        }
    }

    onInputChange(ev) {
        this.state.racerNo = ev.target.value;
        clearTimeout(this._debounceTimer);
        // keep your debounce (200ms)
        this._debounceTimer = setTimeout(() => this.fetchRacer(), 200);
    }

    async fetchRacer() {
        this.state.error = null;
        const noVal = parseInt(this.state.racerNo, 10);
        if (!Number.isFinite(noVal) || noVal <= 0) {
            this.state.racer = null;
            return;
        }
        this.state.loading = true;
        try {
            // upgraded fields from the second file (include id + racer_no)
            const res = await this.orm.searchRead(
                "salezrace.racer",
                [["racer_no", "=", noVal]],
                ["id", "first_name", "last_name", "age", "gender", "category", "racer_no", "start_time"]
            );
            this.state.racer = res.length ? res[0] : null;
            if (!this.state.racer) {
                this.state.error = "Racer not found.";
            }
        } catch (e) {
            this.state.error = e?.message || "Failed to fetch racer.";
        } finally {
            this.state.loading = false;
        }
    }

    // ---------- UI handlers ----------
    async onClickStart() {
        if (!this.state.racer) return;
        try {
            await this.orm.call("salezrace.racer", "action_start", [this.state.racer.id], {});
            await this.fetchRacer();
            await this.fetchLists();
        } catch (e) {
            this.notification.add(e?.message || "Cannot start.", { type: "danger" });
        }
    }

    // new: Revert action for the left summary table
    onClickRevert(row) {
        this.dialog.add(ConfirmationDialog, {
            title: "Revert start?",
            body: `Remove start time for racer #${row.racer_no} ${row.first_name} ${row.last_name}?`,
            confirm: async () => {
                try {
                    await this.orm.write("salezrace.racer", [row.id], { start_time: false });
                    if (this.state.racer && this.state.racer.id === row.id) {
                        this.state.racer.start_time = false;
                    }
                    await this.fetchLists();
                    this.notification.add("Start time removed.", { type: "warning" });
                } catch (e) {
                    this.notification.add(e?.message || "Failed to revert.", { type: "danger" });
                }
            },
        });
    }

    // new: Load action for the right summary table
    async onClickLoad(row) {
        try {
            this.state.racerNo = String(row.racer_no || "");
            await this.fetchRacer();
        } catch (e) {
            this.notification.add(e?.message || "Failed to load racer.", { type: "danger" });
        }
    }
}

registry.category("actions").add("salezrace.start_action", StartClientAction);
