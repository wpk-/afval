'use strict'
import {StoredState} from '../state.js'


export class AppState extends StoredState {
    constructor(naam, {wegingen} = {}) {
        super(naam)

        // Laatste versie van de opgehaalde wegingen. Dit is ook exact de data
        // die naar de tabel en kaart gestuurd is zodat alle componenten in
        // sync zijn.
        this.wegingen = wegingen ?? {last_change: null, data: []}
    }

    toJSON() {
        return {}
    }
}
