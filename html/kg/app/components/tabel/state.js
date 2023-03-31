'use strict'
import {StoredState} from '../state.js'


export class TabelState extends StoredState {
    constructor(naam, {active, scroll, sort} = {}) {
        super(naam)

        // Set met IDs van alle gefilterde rijen.
        this.active = new Set(active)

        // Set met IDs van alle zichtbare rijen.
        this.scroll = new Set(scroll)

        // Veldnaam en richting.
        this.sort = sort // [{column, dir}]
    }

    toJSON() {
        // active en scroll worden bij nieuwe initialisatie van de app
        // automatisch weer opgebouwd vanuit de filter controls.
        return {sort: this.sort}
    }
}
