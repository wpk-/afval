'use strict'
import {Deck} from '@deck.gl/core'
import {BitmapLayer, PathLayer, PolygonLayer, ScatterplotLayer} from '@deck.gl/layers'
import {TileLayer} from '@deck.gl/geo-layers'

import {PlotMarkers} from '../constants.js'
import {KaartState} from './state.js'


export class Kaart {
    #state

    constructor(rootNode, {initialViewState, layerProps={}, kleurschemas}, data={}) {
        // config
        this.kleurschemas = kleurschemas

        // state
        this.#state = KaartState.restore(rootNode.id, {initialViewState})

        // object
        this.deck = new Deck({
            parent: rootNode,
            initialViewState: this.#state.initialViewState,
            layers: [],

            // Enable faster click action.
            // (See https://github.com/visgl/deck.gl/issues/3783)
            controller: {doubleClickZoom: false},

            onViewStateChange: this._onViewStateChange,

            // For cursor() and tooltip() see bottom of this file.
            ...cursor('wegingen', 'containers'),
            ...tooltip('wegingen', 'containers'),
        })

        this.layerProps = {
            kaart: {
                renderSubLayers: (props) => {
                    const {
                        bbox: {west, south, east, north}
                    } = props.tile
                    return new BitmapLayer(props, {
                        data: null,
                        image: props.data,
                        bounds: [west, south, east, north]
                    })
                },
                ...layerProps.kaart,
                id: 'kaart',
                // data voor de kaart zit in layerProps.
            },
            stadsdelen: {
                ...layerProps.stadsdelen,
                id: 'stadsdelen',
                data: data.stadsdelen ?? [],
                pickable: false,
            },
            wijken: {
                ...layerProps.wijken,
                id: 'wijken',
                data: data.wijken ?? [],
                pickable: true,
                onClick: this._onClick,
            },
            containers: {
                ...layerProps.containers,
                id: 'containers',
                data: data.containers ?? [],
                pickable: true,
                onClick: this._onClick,
            },
            wegingen: {
                ...layerProps.wegingen,
                id: 'wegingen',
                data: data.wegingen ?? [],
                pickable: true,
                onClick: this._onClick,
                updateTriggers: {
                    getFillColor: this.#state.kleurschema,
                    getPosition: this.#state.wegingenRenderCount,
                },
            },
            highlight: {
                ...layerProps.highlight,
                id: 'highlight',
                data: data.highlight ?? [],
                pickable: false,
            },
        }
    }

    get rootElement() {return this.deck.canvas.parentNode}

    _onClick = ({layer: {id: layerId} = {}, object, viewport}, event) => {
        if (layerId === 'containers' && (viewport?.zoom ?? 0) < 15) {
            return
        }

        event.preventDefault()
        event.stopPropagation()

        const detail = {
            ctrlKey: event.srcEvent.ctrlKey
                  || event.srcEvent.shiftKey,
            layer: layerId,
            object,
        }

        this.rootElement.dispatchEvent(new CustomEvent('click', {detail}))
    }

    _onViewStateChange = ({viewState}) => {
        const state = this.#state
        state.initialViewState = viewState
        this.rootElement.dispatchEvent(
            new CustomEvent('viewstatechange', {detail: state})
        )
    }

    render({kleurschema, plotMarkers, active, scroll, viewState}) {
        const state = this.#state

        let render = false

        if (kleurschema && kleurschema !== state.kleurschema) {
            state.kleurschema = kleurschema
            render = true
        }

        if (plotMarkers && plotMarkers !== state.plotMarkers) {
            state.plotMarkers = plotMarkers
            render = true
        }

        if (viewState && viewState !== state.initialViewState) {
            const {minZoom, maxZoom} = state.initialViewState
            state.initialViewState = {...viewState, minZoom, maxZoom}
            this.deck.setProps({initialViewState: state.initialViewState})
        }

        if (active) {
            state.active = active
            render ||= state.plotMarkers === PlotMarkers.ACTIVE
        }

        if (scroll) {
            state.scroll = scroll
            render ||= state.plotMarkers === PlotMarkers.SCROLL
        }

        if (render) {
            state.wegingenRenderCount += render
            this.renderState()
        }
    }

    renderState() {
        const state = this.#state
        const layerProps = this.layerProps
        const kleurschema = state.kleurschema
        const kleuren = this.kleurschemas[kleurschema]
        const renderCount = state.wegingenRenderCount
        const plotIds = state.plotMarkers === PlotMarkers.SCROLL
            ? state.scroll
            : state.active

        Object.assign(layerProps.wegingen, {
            getFillColor: ({[kleurschema]: k}) => kleuren[k] ?? [80, 80, 80],
            getPosition: ({id, lon, lat}) => plotIds.has(id) ? [lon, lat] : null,
            updateTriggers: {
                getFillColor: kleurschema,
                getPosition: renderCount,
            }
        })

        this.deck.setProps({
            layers: [
                new TileLayer(layerProps.kaart),
                new PathLayer(layerProps.stadsdelen),
                new PolygonLayer(layerProps.wijken),
                new ScatterplotLayer(layerProps.wegingen),
                new ScatterplotLayer(layerProps.containers),
                new ScatterplotLayer(layerProps.highlight),
            ],
        })
    }

    setData({kaart, stadsdelen, wijken, containers, wegingen, highlight} = {}) {
        const layerProps = this.layerProps

        if (kaart) {
            layerProps.kaart.data = kaart
        }
        if (stadsdelen) {
            layerProps.stadsdelen.data = stadsdelen
        }
        if (wijken) {
            layerProps.wijken.data = wijken
        }
        if (containers) {
            layerProps.containers.data = containers
        }
        if (wegingen) {
            layerProps.wegingen.data = wegingen
        }
        if (highlight) {
            layerProps.highlight.data = highlight
        }

        this.renderState()
    }
}


/**
 * Generates the configuration for a meaningful cursor on the map.
 * 
 * Two layer IDs are needed to properly parse hover event data:
 *  - wegingenLayerId: The layer ID for the wegingen layer.
 *  - contianersLayerId: The layer ID for the containers layer.
 */
const cursor = (wegingenLayerId, containersLayerId) => {
    let hoverCursor = 'grab'

    const getCursor = ({isDragging, isHovering}) =>
        isDragging ? 'grabbing' : isHovering ? hoverCursor : 'grab'

    const onHover = ({layer, viewport}) => {
        if (layer?.id === wegingenLayerId || (
            layer?.id === containersLayerId && viewport?.zoom >= 15)) {
            hoverCursor = 'pointer'
        }
        else {
            hoverCursor = 'grab'
        }
    }

    return {
        getCursor,
        onHover,
    }
}


/**
 * Generates the configuration to render tooltips.
 * The same two layer IDs are needed as for the cursor function.
 */
const tooltip = (wegingenLayerId, containersLayerId) => {
    const containerTooltip = ({adres, code, fractie, persend, type, volume}) => `
${adres}
${code}${persend ? ', persend' : ''}
${volume}m³ ${fractie}
${type === 'ABOVE_GROUND' ? 'bovengronds' : ''}
`.trim()

    const wegingTooltip = ({adres, datum_str, eerste_weging, fractie, kenteken,
                            netto_gewicht, tijd_str, tweede_weging, systeem_id}
                            ) => `
${adres}
Op ${datum_str} om ${tijd_str}
${fractie}: ${netto_gewicht}kg (${eerste_weging} - ${tweede_weging})
Voertuig ${kenteken} (${systeem_id})
`.trim()

    return {
        getTooltip: ({layer, object, viewport}) =>
            (layer?.id === containersLayerId && viewport?.zoom >= 15)
            ? (object && containerTooltip(object))
            : (layer?.id === wegingenLayerId)
            ? (object && wegingTooltip(object))
            : null
    }
}