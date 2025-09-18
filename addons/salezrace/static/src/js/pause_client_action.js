/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillStart, onMounted, onWillUnmount } from "@odoo/owl";

export class PauseClientAction extends Component {
    static template = "salezrace.PauseClientAction";

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");

        this.state = useState({
            checkpoints: [],
            selectedCheckpoint: null,
            onTrack: [],
            loading: false,
            livePause: {},
        });

        this.timer = null;
        this._refreshInFlight = false;
        this._refreshRequested = false;

        this.selectCheckpoint = this.selectCheckpoint.bind(this);
        this.backToCheckpoints = this.backToCheckpoints.bind(this);
        this.refreshSafe = this.refreshSafe.bind(this);
        this.refresh = this.refresh.bind(this);
        this.onPauseStart = this.onPauseStart.bind(this);
        this.onPauseEnd = this.onPauseEnd.bind(this);
        this.onPauseInvalidate = this.onPauseInvalidate.bind(this);
        this.onCustomTime = this.onCustomTime.bind(this);
        this.onConfirmCustomTime = this.onConfirmCustomTime.bind(this);
        this.onCancelCustomTime = this.onCancelCustomTime.bind(this);

        onWillStart(() => this.loadCheckpoints());
        onMounted(() => {
            this.timer = setInterval(() => this._updateLiveTimes(), 1000);
            this.refreshTimer = setInterval(() => this.refreshSafe(), 5000);
        });
        onWillUnmount(() => {
            clearInterval(this.timer);
            clearInterval(this.refreshTimer);
        });
    }

    async loadCheckpoints() {
        this.state.loading = true;
        try {
            const checkpoints = await this.orm.searchRead(
                "salezrace.checkpoint",
                [],
                ["id", "name"],
                { order: "sequence" }
            );
            this.state.checkpoints = checkpoints;
        } finally {
            this.state.loading = false;
        }
    }

    async selectCheckpoint(checkpoint) {
        this.state.selectedCheckpoint = checkpoint;
        await this.refresh();
    }

    async backToCheckpoints() {
        this.state.selectedCheckpoint = null;
    }

    async refreshSafe() {
        if (this._refreshInFlight) {
            this._refreshRequested = true;
            return;
        }
        this._refreshInFlight = true;
        try {
            await this.refresh();
        } finally {
            this._refreshInFlight = false;
            if (this._refreshRequested) {
                this._refreshRequested = false;
                this.refreshSafe();
            }
        }
    }

    async refresh() {
        if (!this.state.selectedCheckpoint) {
            return;
        }
        try {
            const onTrack = await this.orm.searchRead(
                "salezrace.racer",
                [["start_time", "!=", false], ["finish_time", "=", false]],
                ["id", "racer_no", "first_name", "last_name", "active_pause_log_id"],
                { order: "start_time asc, id asc" }
            );

            const racer_ids = onTrack.map(racer => racer.id);
            const pause_logs = await this.orm.searchRead(
                "salezrace.pause.log",
                [["racer_id", "in", racer_ids], ["checkpoint_id", "=", this.state.selectedCheckpoint.id], ["is_invalid", "=", false]],
                ["racer_id", "start_time", "end_time"]
            );

            for (const racer of onTrack) {
                const existing_racer = this.state.onTrack.find(r => r.id === racer.id);
                const racer_pause_logs = pause_logs.filter(log => log.racer_id[0] === racer.id);
                let checkpoint_pause_time = 0;
                for (const log of racer_pause_logs) {
                    if (log.start_time && log.end_time) {
                        const start = new Date(log.start_time + "Z");
                        const end = new Date(log.end_time + "Z");
                        const duration = (end - start) / 1000;
                        checkpoint_pause_time += duration;
                    }
                }
                if (existing_racer) {
                    existing_racer.checkpoint_pause_time = checkpoint_pause_time;
                    existing_racer.active_pause_log_id = racer.active_pause_log_id;
                } else {
                    this.state.onTrack.push({ ...racer, checkpoint_pause_time: checkpoint_pause_time, live_pause_time: 0, showCustomTimeInput: false, custom_time: 0 });
                }
            }
            this.state.onTrack = this.state.onTrack.filter(racer => onTrack.some(r => r.id === racer.id));

        } finally {
        }
    }

    _updateLiveTimes() {
        for (const racerId in this.state.livePause) {
            const pause = this.state.livePause[racerId];
            const liveTime = (new Date() - pause.startTime) / 1000;
            const racer = this.state.onTrack.find(r => r.id == racerId);
            if (racer) {
                racer.live_pause_time = liveTime;
            }
        }
    }

    async onPauseStart(racer) {
        this.state.livePause[racer.id] = { startTime: new Date() };
        await this.handlePauseAction("action_pause_start", racer);
    }

    async onPauseEnd(racer) {
        racer.live_pause_time = 0;
        delete this.state.livePause[racer.id];
        await this.handlePauseAction("action_pause_end", racer);
    }

    async onPauseInvalidate(racer) {
        if (racer.active_pause_log_id) {
            await this.onPauseEnd(racer);
        }
        await this.handlePauseAction("action_invalidate_logs", racer);
    }

    onCustomTime(racer) {
        racer.custom_time = racer.checkpoint_pause_time + racer.live_pause_time;
        racer.showCustomTimeInput = true;
    }

    onCancelCustomTime(racer) {
        racer.showCustomTimeInput = false;
    }

    async onConfirmCustomTime(racer) {
        await this.orm.call(
            "salezrace.racer",
            "action_custom_time",
            [racer.id, this.state.selectedCheckpoint.id, parseInt(racer.custom_time)]
        );
        racer.showCustomTimeInput = false;
        await this.refresh();
    }

    async handlePauseAction(action, racer) {
        this.state.loading = true;
        try {
            let args = [racer.id];
            if (action === 'action_pause_start' || action === 'action_invalidate_logs') {
                args.push(this.state.selectedCheckpoint.id);
            }
            await this.orm.call("salezrace.racer", action, args, {});
        } catch (e) {
            const errorMessage = e.data?.message || e.message || `Failed to ${action}.`;
            this.notification.add(errorMessage, { type: "danger" });
            if (action === 'action_pause_start') {
                delete this.state.livePause[racer.id];
            }
        } finally {
            this.state.loading = false;
            await this.refresh();
        }
    }
}

registry.category("actions").add("salezrace.pause_action", PauseClientAction);
