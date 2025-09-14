/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillStart, onMounted, onWillUnmount } from "@odoo/owl";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

export class FinishClientAction extends Component {
    static template = "salezrace.FinishClientAction";

    setup() {
        // Core services only
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.dialog = useService("dialog");

        this.state = useState({
            onTrack: [],
            finishers: [],
            loading: false,
        });

        // internals
        this._timer = null;
        this._refreshInFlight = false;
        this._refreshRequested = false;

        // bind methods
        this.refreshBoth = this.refreshBoth.bind(this);
        this.refreshBothSafe = this.refreshBothSafe.bind(this);
        this.fetchOnTrack = this.fetchOnTrack.bind(this);
        this.fetchFinishers = this.fetchFinishers.bind(this);
        this.onFinishNow = this.onFinishNow.bind(this);
        this.formatDuration = this.formatDuration.bind(this);
        
        // Initial load before first render
        onWillStart(this.refreshBothSafe);

        // Start simple 2s polling after mount (no bus, no heuristics)
        onMounted(() => {
            this._timer = setInterval(this.refreshBothSafe, 2000);
        });

        // Cleanup
        onWillUnmount(() => {
            if (this._timer) {
                clearInterval(this._timer);
                this._timer = null;
            }
        });
    }

    async refreshBothSafe() {
        if (this._refreshInFlight) {
            this._refreshRequested = true;
            return;
        }
        this._refreshInFlight = true;
        try {
            await Promise.all([this.fetchOnTrack(), this.fetchFinishers()]);
        } finally {
            this._refreshInFlight = false;
            if (this._refreshRequested) {
                this._refreshRequested = false;
                this.refreshBothSafe();
            }
        }
    }

    // Legacy alias
    async refreshBoth() {
        return this.refreshBothSafe();
    }

    onRevertFinish(row) {
        this.dialog.add(ConfirmationDialog, {
            title: "Revert finish?",
            body: `Remove finish time for racer #${row.racer_no}?`,
            confirm: async () => {
                try {
                    await this.orm.write("salezrace.racer", [row.id], {
                        finish_time: false,
                        final_time: false,
                    });
                    await this.refreshBothSafe();
                } catch (e) {
                    this.notification.add(e?.message || "Failed to revert finish.", { type: "danger" });
                }
            },
        });
    }
    
    async fetchOnTrack() {
        const rows = await this.orm.searchRead(
            "salezrace.racer",
            [["start_time", "!=", false], ["finish_time", "=", false]],
            ["id", "racer_no", "first_name", "last_name", "age", "gender", "start_time"],
            { order: "start_time asc, id asc" }
        );
        this.state.onTrack = rows;
    }

    async fetchFinishers() {
        const rows = await this.orm.searchRead(
            "salezrace.racer",
            [["start_time", "!=", false], ["finish_time", "!=", false]],
            ["id", "racer_no", "first_name", "last_name", "age", "gender", "start_time", "finish_time", "final_time"],
            { order: "finish_time desc, id desc" }
        );
        this.state.finishers = rows;
    }

    // Client-side fallback (mm:ss) if server didn't compute final_time
    formatDuration(row) {
        const toMs = (dt) => (dt ? Date.parse(String(dt).replace(" ", "T")) || 0 : 0);
        const diff = Math.max(0, toMs(row.finish_time) - toMs(row.start_time)) / 1000;
        const m = String(Math.floor(diff / 60)).padStart(2, "0");
        const s = String(Math.floor(diff % 60)).padStart(2, "0");
        return `${m}:${s}`;
    }

    async onFinishNow(row) {
        try {
            await this.orm.call("salezrace.racer", "action_finish_now", [row.id], {});
            await this.refreshBothSafe(); // immediate feedback
        } catch (e) {
            this.notification.add(e?.message || "Failed to finish racer.", { type: "danger" });
        }
    }
}

registry.category("actions").add("salezrace.finish_action", FinishClientAction);
