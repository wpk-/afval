'use strict'
import {DataStreams} from '../data/index.js'
import {Controls} from '../header/index.js'
import {Kaart} from '../kaart/index.js'
import {Tabel} from '../tabel/index.js'
import {Weergave} from '../constants.js'

import {AppState} from './state.js'


/**
 * De app coordineert interactie tussen de controls.
 * 
 * Controls genereren events op hun rootNode op basis van interactie met de
 * gebruiker. De app gebruik vervolgens event.detail om het event verder door te
 * werken naar de andere controls.
 * 
 * Controls hebben een aantal methodes beschikbaar voor de app om hun interne
 * state aan te passen en te renderen. Deze methodes genereren geen events maar
 * geven in plaats daarvan een returnwaarde.
 * 
 * De controls beheren hun eigen state. De app heeft daar toegang tot.
 */
export class App {
    #state

    constructor(rootNode, config) {
        this.rootNodeRef = new WeakRef(rootNode)

        rootNode.addEventListener('datachange', this._onDataChange)

        const controlsElement = rootNode.querySelector('#controls')
        controlsElement.addEventListener('displaychange', this._onControlsDisplayChange)
        controlsElement.addEventListener('filterchange', this._onControlsFilterChange)
        controlsElement.addEventListener('download', this._onControlsDownloadClick)
        
        const kaartElement = rootNode.querySelector('#kaart')
        kaartElement.addEventListener('click', this._onKaartClick)

        const tabelElement = rootNode.querySelector('#lijst')
        tabelElement.addEventListener('change', this._onTabelChange)
        tabelElement.addEventListener('scroll', this._onTabelScroll)
        tabelElement.addEventListener('rowover', this._onTabelMouseEnter)
        tabelElement.addEventListener('rowout', this._onTabelMouseLeave)

        this.#state = AppState.restore(rootNode.id, {})

        this.data = new DataStreams(rootNode, {sources: config.data.bronnen})
        this.tabel = new Tabel(tabelElement, config.tabel)
        this.kaart = new Kaart(kaartElement, config.kaart)
        this.controls = new Controls(controlsElement, config.controls)
    }

    get rootElement() {return this.rootNodeRef.deref()}

    _onControlsDisplayChange = (event) => {
        const {kleurschema, plotMarkers, weergave} = event.detail

        const root = this.rootElement
        root.classList.toggle('hideKaart', !weergave.has(Weergave.KAART))
        root.classList.toggle('hideLijst', !weergave.has(Weergave.LIJST))

        this.kaart.render({plotMarkers, kleurschema})
    }

    _onControlsDownloadClick = (event) => {
        this.tabel.download()
    }

    _onControlsFilterChange = (event) => {
        const filter = event.detail
        this.tabel.setFilter(filter)
    }

    _onDataChange = (event) => {
        const {key, data} = event.detail

        if (key === 'containers') {
            this.setContainers(data)
        }
        else if (key === 'gebieden') {
            this.setGebieden(data)
        }
        else if (key === 'wegingen') {
            this.setWegingen(data)
        }
        else if (key === 'wegingenDelta') {
            this.updateWegingen(data)
        }
        else {
            console.warn(`Onbekende bron: "${key}"`)
        }
    }

    _onKaartClick = (event) => {
        const {ctrlKey, layer, object} = event.detail

        if (layer === 'wijken') {
            this.tabel.setFilter(
                this.controls.filterWijk(object, ctrlKey)
            )
        }
        else if (layer === 'wegingen') {
            this.tabel.setFilter(
                this.controls.filterRoute(object)
            )
        }
        else if (layer === 'containers') {
            this.tabel.setFilter(
                this.controls.filterCluster(object, ctrlKey)
            )
        }
    }

    _onTabelChange = (event) => {
        const {active} = event.detail
        this.controls.setText(`${active.size} wegingen`)
        this.kaart.render({active})
    }

    _onTabelScroll = (event) => {
        const {scroll} = event.detail
        this.kaart.render({scroll})
    }

    _onTabelMouseEnter = (event) => {
        clearTimeout(this._tid)
        const row = event.detail
        this.kaart.setData({highlight: [row]})
    }

    _onTabelMouseLeave = (event) => {
        const row = event.detail
        this._tid = setTimeout(() => this.kaart.setData({highlight: []}), 50)
    }

    renderState() {
        const state = this.#state
        this.tabel.setData(state.wegingen.data)
        this.kaart.setData({wegingen: state.wegingen.data})
    }

    setContainers({data}) {
        this.kaart.setData({containers: data})
    }

    setGebieden({stadsdelen, wijken}) {
        const fixGeometrie = (gebied) => {
            let {lon, lat} = gebied
            delete gebied.lon
            delete gebied.lat
            gebied.geometrie = lon.map((loni, i) => [loni, lat[i]])
        }
        stadsdelen.forEach(fixGeometrie)
        wijken.forEach(fixGeometrie)

        this.controls.setData({stadsdelen, wijken})
        this.kaart.setData({stadsdelen, wijken})
    }

    setWegingen({data, last_change}) {
        const state = this.#state
        state.wegingen = {
            last_change,
            data: data.map(completeRow),
        }
        this.renderState()
    }

    updateWegingen({data, last_change, last_delta}) {
        const state = this.#state

        if (last_change === state.wegingen.last_change) {
            // console.log('De wegingen update heeft niks nieuws.')
            return
        }
        else if (last_delta === state.wegingen.last_change) {
            // console.log('Update met nieuwe data.')
            state.wegingen = {
                last_change,
                data: [...state.wegingen.data, ...data.map(completeRow)],
            }
            this.renderState()
        }
        else if (state.wegingen?.data?.length) {
            // console.log('We hebben een of meer updates gemist. Opnieuw hele dataset halen...')
            this.data.fetchJson('wegingen')
        }
        else {
            // console.log('Eerste delta kunnen we rustig negeren.')
        }
    }
}


const completeRow = (row) => ({
    // Een rij-index om data gemakkelijk terug te vinden
    id: `${row.systeem_id}-${row.volgnummer}`,
    uur: Math.floor(row.tijd_ms / 3600_000),
    // Een week index rolt over 5 weken (omdat de data max 5 weken overspant)
    // https://stackoverflow.com/a/64293860
    week_mod5: Math.floor((row.datum_ms + 345_600_000) / 604_800_000) % 5,
    ...row,
})