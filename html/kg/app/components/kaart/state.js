'use strict'
import {StoredState} from '../state.js'
import {Kleurschema, PlotMarkers} from '../constants.js'


export class KaartState extends StoredState {
    constructor(naam, {kleurschema, plotMarkers, active, scroll,
                       initialViewState} = {}) {
        super(naam)

        // fractie, ...?
        this.kleurschema = kleurschema ?? Kleurschema.FRACTIE

        // active / scroll
        this.plotMarkers = plotMarkers ?? PlotMarkers.ACTIVE

        // Set met IDs van gefilterde rijen.
        this.active = new Set(active)

        // Set met IDs van zichtbare rijen.
        this.scroll = new Set(scroll)

        // Een counter voor het tekenen van de kaart.
        this.wegingenRenderCount = 0

        // De kaart viewstate. Zie deck.gl documentatie.
        this.initialViewState = initialViewState
    }

    toJSON() {
        // In principe wordt dit bij initialisatie van de app allemaal opnieuw
        // bepaald vanuit de filter controls (op viewState na). Met name de rij-
        // IDs verliezen hun betekenis bij vernieuwde data dus die willen we
        // echt niet opslaan en de render count is goed terug op 0.
        const {longitude, latitude, zoom, minZoom, maxZoom} = this.initialViewState
        return {
            kleurschema: this.kleurschema,
            plotMarkers: this.plotMarkers,
            initialViewState: {longitude, latitude, zoom, minZoom, maxZoom},
        }
    }

    static restore(name, {initialViewState, ...defaultState}) {
        const str = localStorage.getItem(name)
        const obj = JSON.parse(str) ?? {}
        // Merge initialViewState.
        obj.initialViewState = {...initialViewState, ...obj.initialViewState}
        return new this(name, {...defaultState, ...obj})
    }
}
