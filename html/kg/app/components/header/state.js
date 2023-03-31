'use strict'
import {StoredState} from '../state.js'
import {Kleurschema, PlotMarkers, Weergave} from '../constants.js'


export class ControlsState extends StoredState {
    constructor(naam, {fractie, week, tijd, weekdag, stadsdeel, wijk,
                       extrafilters, weergave, plotMarkers, kleurschema} = {}) {
        super(naam)

        // Set van fractie strings, 'Rest', 'Papier', 'Glas', ...
        this.fractie = new Set(fractie)

        // [start, end]
        // start = timestamp in ms, afgerond op middernacht maandag.
        // end = timestamp in ms, afgerond op middernacht maandag.
        this.week = (week ?? [NaN, NaN]).map(v => v ?? NaN)

        // [start, end]
        // start = ms sinds middernacht.
        // end = ms sinds middernacht.
        this.tijd = (tijd ?? [0, 0]).map(v => v ?? NaN)

        // Set van strings, '1', '2', '3', ... '6', '0'
        // Maandag = 1, dinsdag = 2, etc.
        this.weekdag = new Set(weekdag)

        // Set van strings met namen van stadsdelen
        this.stadsdeel = new Set(stadsdeel)

        // Set van strings met namen van wijken
        this.wijk = new Set(wijk)

        // Lijst met data property namen + filterwaarde.
        // = [[veldnaam, Set([...])], ...]
        this.extrafilters = (extrafilters ?? []).map(([k, v]) => [k, new Set(v)])

        this.weergave = new Set(weergave ?? [Weergave.LIJST, Weergave.KAART])

        this.plotMarkers = plotMarkers ?? PlotMarkers.ACTIVE

        this.kleurschema = kleurschema ?? Kleurschema.FRACTIE
    }

    toJSON() {
        return {
            fractie: [...this.fractie],
            week: this.week,
            tijd: this.tijd,
            weekdag: [...this.weekdag],
            stadsdeel: [...this.stadsdeel],
            wijk: [...this.wijk],
            externalfilters: this.extrafilters.map(([k, v]) => [k, [...v]]),
            weergave: [...this.weergave],
            plotMarkers: this.plotMarkers,
            kleurschema: this.kleurschema,
        }
    }
}
