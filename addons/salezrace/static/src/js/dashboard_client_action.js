/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillStart } from "@odoo/owl";

export class DashboardClientAction extends Component {
    static template = "salezrace.DashboardClientAction";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            loading: true,
            categoryPairs: [],
        });

        onWillStart(() => this.fetchDashboardData());
    }

    print() {
        this.action.doAction('salezrace.action_report_salezrace_dashboard');
    }

    async fetchDashboardData() {
        this.state.loading = true;
        const racers = await this.orm.searchRead(
            "salezrace.racer",
            [["finish_time", "!=", false], ["final_time", "!=", false]],
            ["age", "first_name", "last_name", "final_time", "category"],
            { order: "final_time asc" }
        );

        const top3_ids = racers.slice(0, 3).map(r => r.id);

        const categoryGroups = {};
        racers.forEach(racer => {
            const rank = top3_ids.indexOf(racer.id);
            if (rank !== -1) {
                racer.overall_rank = rank + 1;
            }

            if (!categoryGroups[racer.category]) {
                categoryGroups[racer.category] = [];
            }
            if (categoryGroups[racer.category].length < 3) {
                categoryGroups[racer.category].push(racer);
            }
        });

        const categoryPairOrder = [
            ["MU6", "FU6"],
            ["M6", "F6"],
            ["M10", "F10"],
            ["M14", "F14"],
            ["M18", "F18"],
            ["M31", "F31"],
            ["M45", "F45"],
        ];

        const categoryAges = {
            'U6': '< 6',
            '6': '6-9',
            '10': '10-13',
            '14': '14-17',
            '18': '18-30',
            '31': '31-44',
            '45': '45+',
        };

        this.state.categoryPairs = categoryPairOrder.map(([maleCat, femaleCat]) => {
            const maleRacers = categoryGroups[maleCat] || [];
            const femaleRacers = categoryGroups[femaleCat] || [];

            while (maleRacers.length < 3) {
                maleRacers.push({});
            }
            while (femaleRacers.length < 3) {
                femaleRacers.push({});
            }

            return {
                male: { category: maleCat, racers: maleRacers, age_range: categoryAges[maleCat.substring(1)] },
                female: { category: femaleCat, racers: femaleRacers, age_range: categoryAges[femaleCat.substring(1)] },
            };
        }).filter(pair => {
            const hasMaleRacers = pair.male.racers.some(racer => Object.keys(racer).length > 0);
            const hasFemaleRacers = pair.female.racers.some(racer => Object.keys(racer).length > 0);
            return hasMaleRacers || hasFemaleRacers;
        });

        this.state.loading = false;
    }


}

registry.category("actions").add("salezrace.dashboard_action", DashboardClientAction);
