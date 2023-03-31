'use strict'
import {Weergave} from '../constants.js'
import {LabelsList} from '../labelslist/index.js'
import {ControlsState} from './state.js'
import {interval, member} from './filtertools.js'
import {
    parseChecks,
    parseRadios,
    parseRange,
    parseSelect,
    renderChecks,
    renderRadios,
    renderRange,
    renderSelect,
    renderSelectDisabled,
} from './controltools.js'


/**
 * Controls definieert twee events voor de app:
 *  - displaychange (event.detail = state)
 *  - filterchange (event.detail = functie)
 *
 * De enige functies de events genereren beginnen met _on. Ze vertalen interne
 * events van de gebruiker naar bovengenoemde events voor de app. (+ de
 * constructor genereert aan het einde beide events.)
 *  - _onChange = De gebruiker heeft een selectie/invoer aangepast.
 *  - _onClick = De gebruiker heeft een shortcut link of een x op een label
 *               geklikt. De actie is uitgevoerd: de state is aangepast en de
 *               aanpassing is gerenderd. Daarna wordt een event gegenereerd.
 * 
 * Functies die van buitenaf beschikbaar zijn om controls aan te passen
 * gebruiken de input om de state aan te passen en te renderen. Er gaat geen
 * event vanuit omdat de functie door code is aangeroepen in plaats van door
 * gebruikersinteractie. In plaats daarvan geven ze een returnwaarde:
 *  - filterCluster (return filter functie)
 *  - filterRoute (return filter functie)
 *  - filterWijk (return filter functie)
 *  - setText (geen returnwaarde)
 */
export class Controls {
    #state

    constructor(rootNode) {
        this.formRef = new WeakRef(rootNode)
        this.aantalRef = new WeakRef(rootNode.querySelector('#aantal'))

        this.filterLabels = new LabelsList(
            rootNode.querySelector('#extrafilters'),
            ([_, set]) => [...set].join(', ')
        )

        rootNode.querySelectorAll(':scope > section').forEach((section) => {
            section.addEventListener('change', this.#_onChange)
            section.addEventListener('click', this.#_onClick)
        })

        rootNode.querySelector('#download')
        .addEventListener('click', this.#_onDownloadClick)

        const state = this.#state = ControlsState.restore(rootNode.id)
        const filter = filterFunction(state)

        this.renderState()
        rootNode.dispatchEvent(new CustomEvent('displaychange', {detail: state}))
        rootNode.dispatchEvent(new CustomEvent('filterchange', {detail: filter}))
    }

    get formElement() {return this.formRef.deref()}
    get aantalElement() {return this.aantalRef.deref()}

    #_onChange = (event) => {
        const target = event.target
        const form = this.formElement
        const state = this.#state

        event.stopPropagation()

        Object.assign(state, {
            fractie: parseSelect(form.fractie),
            week: parseRange(form.weekvan, form.weektot),
            tijd: parseRange(form.tijdvan, form.tijdtot),
            weekdag: parseChecks(form.querySelectorAll('[name="weekdag"]')),
            stadsdeel: parseSelect(form.stadsdeel),
            wijk: parseSelect(form.wijk),
            extrafilters: this.filterLabels.labels,
            weergave: parseChecks(form.querySelectorAll('[name="weergave"]')),
            plotMarkers: parseRadios(form.querySelectorAll('[name="plotmarkers"]')),
            kleurschema: parseSelect(form.kleurschema),
        })
    
        if (['weergave', 'plotmarkers', 'kleurschema'].includes(target.name)) {
            if (state.weergave.size < 1) {
                state.weergave.add(
                    target.value === Weergave.LIJST
                    ? Weergave.KAART : Weergave.LIJST
                )
                renderChecks(form.querySelectorAll('[name="weergave"]'), state.weergave)
            }
            form.dispatchEvent(new CustomEvent('displaychange', {detail: state}))
        }
        else {
            if (target.name === 'stadsdeel') {
                const stadsdelen = parseSelect(form.stadsdeel)
                renderSelectDisabled(form.wijk, 'stadsdeel', stadsdelen)
            }
            form.dispatchEvent(new CustomEvent('filterchange', {detail: filterFunction(state)}))
        }
    }

    #_onClick = (event) => {
        const target = event.target
        const form = this.formElement
        const state = this.#state

        if (target.classList.contains('shortcut')) {
            event.preventDefault()
            event.stopPropagation()
            const actionName = new URL(target.href).hash
            this.applyShortcut(actionName)
        }
        else if (target.classList.contains('action')) {
            event.preventDefault()
            event.stopPropagation()
            this.removeLabel(target)
        }
        else {
            return
        }

        form.dispatchEvent(new CustomEvent('filterchange', {detail: filterFunction(state)}))
    }

    #_onDownloadClick = (event) => {
        const form = this.formElement
        event.preventDefault()
        event.stopPropagation()
        form.dispatchEvent(new CustomEvent('download'))
    }

    render(stateUpdates = {}) {
        const form = this.formElement
        const state = this.#state

        if (Object.keys(stateUpdates).length === 0) {
            return this.renderState()
        }
        
        const {fractie, week, tijd, weekdag, stadsdeel, wijk, extrafilters,
               plotMarkers, kleurschema, weergave} = stateUpdates

        if (weergave && weergave.size === 0) {
            weergave.add(
                state.weergave.has(Weergave.LIJST)
                ? Weergave.KAART
                : Weergave.LIJST
            )
        }

        Object.assign(state, stateUpdates)

        if (fractie !== undefined) {
            renderSelect(form.fractie, state.fractie)
        }
        if (week !== undefined) {
            renderRange(form.weekvan, form.weektot, state.week)
        }
        if (tijd !== undefined) {
            renderRange(form.tijdvan, form.tijdtot, state.tijd)
        }
        if (weekdag !== undefined) {
            renderChecks(form.querySelectorAll('[name="weekdag"]'), state.weekdag)
        }
        if (stadsdeel !== undefined) {
            renderSelect(form.stadsdeel, state.stadsdeel)
            renderSelectDisabled(form.wijk, 'stadsdeel', state.stadsdeel)
        }
        if (wijk !== undefined) {
            renderSelect(form.wijk, state.wijk)
        }
        if (extrafilters !== undefined) {
            this.filterLabels.labels = state.extrafilters
        }
        if (weergave !== undefined) {
            renderChecks(form.querySelectorAll('[name="weergave"]'), state.weergave)
        }
        if (plotMarkers !== undefined) {
            renderRadios(form.querySelectorAll('[name="plotmarkers"]'), state.plotMarkers)
        }
        if (kleurschema !== undefined) {
            renderSelect(form.kleurschema, state.kleurschema)
        }
    }

    renderState() {
        const form = this.formElement
        const state = this.#state

        renderSelect(form.fractie, state.fractie)
        renderRange(form.weekvan, form.weektot, state.week)
        renderRange(form.tijdvan, form.tijdtot, state.tijd)
        renderChecks(form.querySelectorAll('[name="weekdag"]'), state.weekdag)
        renderSelect(form.stadsdeel, state.stadsdeel)
        renderSelectDisabled(form.wijk, 'stadsdeel', state.stadsdeel)
        renderSelect(form.wijk, state.wijk)
        this.filterLabels.labels = state.extrafilters
        renderChecks(form.querySelectorAll('[name="weergave"]'), state.weergave)
        renderRadios(form.querySelectorAll('[name="plotmarkers"]'), state.plotMarkers)
        renderSelect(form.kleurschema, state.kleurschema)
    }

    setData({stadsdelen, wijken}) {
        const form = this.formElement

        const sortFn = ({code: a}, {code: b}) => a > b ? 1 : a < b ? -1 : 0
        stadsdelen.sort(sortFn)
        wijken.sort(sortFn)

        form.stadsdeel
        .replaceChildren(
            new Option('[ alle ]', '', true, true),
            ...stadsdelen.map(({naam, code}) =>
                new Option(`${code} - ${naam}`, naam))
        )

        form.wijk
        .replaceChildren(
            new Option('[ alle ]', '', true, true),
            ...wijken.map(({naam, code, ligt_in}) => {
                const option = new Option(`${code} - ${naam}`, naam)
                option.dataset.stadsdeel = ligt_in
                return option
            })
        )

        this.renderState()
    }

    applyShortcut(actionName) {
        const uur_ms = 60 * 60 * 1000
        const week_ms = 7 * 24 * uur_ms
    
        const shortcutPresets = {
            '#vorige-week': -week_ms,
            '#deze-week': 0,
            '#een-week-terug': -week_ms,
            '#een-week-verder': week_ms,
            '#dag':   [ 6 * uur_ms, 15 * uur_ms],
            '#avond': [15 * uur_ms, 22 * uur_ms],
            '#nacht': [22 * uur_ms,  6 * uur_ms],
            '#24uur': [0, 0],
            '#werkweek': ['1', '2', '3', '4', '5'],
            '#weekend': ['6', '0'],
        }
    
        const maandag = (date) => {
            date.setDate(date.getDate() - (date.getDay() || 7) + 1)
            date.setUTCHours(0, 0, 0, 0)
            return date.valueOf()
        }
    
        const update = {}

        switch (actionName) {
            case '#vorige-week':
            case '#deze-week':
                update.week = (() => {
                    const now = maandag(new Date())
                    const offset = shortcutPresets[actionName]
                    return [now + offset, now + week_ms + offset]
                })()
                break
            case '#een-week-terug':
            case '#een-week-verder':
                update.week = (() => {
                    const [start, end] = this.#state.week
                    const offset = shortcutPresets[actionName]
                    return [start + offset, end + offset]
                })()
                break
            case '#dag':
            case '#avond':
            case '#nacht':
            case '#24uur':
                update.tijd = [...shortcutPresets[actionName]]
                break
            case '#werkweek':
            case '#weekend':
                update.weekdag = new Set(shortcutPresets[actionName])
                break
            case '#deze-dag':
                update.weekdag = new Set([String(new Date().getDay())])
                break
            default:
                return
        }
        this.render(update)
    }
    
    removeLabel(element) {
        this.filterLabels.remove(element)
        this.render({extrafilters: this.filterLabels.labels})
    }

    filterCluster({adres}, ctrlKey) {
        const state = this.#state
        const extrafilters = state.extrafilters
        const adresFilter = extrafilters.find(([key]) => key === 'adres')

        if (adresFilter && ctrlKey) {
            // find the entry in extrafilters.
            const [_, set] = adresFilter

            if (set.has(adres)) {
                set.delete(adres)

                if (!set.size) {
                    extrafilters.splice(extrafilters.indexOf(adresFilter), 1)
                }
            }
            else {
                set.add(adres)
            }
        }
        else {
            extrafilters.push(['adres', new Set([adres])])
        }
        this.render({extrafilters})
        return filterFunction(state)
    }

    filterRoute({datum_str, kenteken}) {
        this.render({
            extrafilters: [
                ['datum_str', new Set([datum_str])],
                ['kenteken', new Set([kenteken])],
            ],
        })
        return filterFunction(this.#state)
    }

    filterWijk({naam, ligt_in: stadsdeel}, ctrlKey) {
        const state = this.#state

        if (ctrlKey) {
            if (state.wijk.has(naam)) {
                state.wijk.delete(naam)

                if (state.wijk.size === 0) {
                    state.stadsdeel.clear()
                }
            }
            else {
                state.wijk.add(naam)
                state.stadsdeel.add(stadsdeel)
            }
            
            this.render({
                wijk: state.wijk,
                stadsdeel: state.stadsdeel,
            })
        }
        else {
            this.render({
                wijk: new Set([naam]),
                stadsdeel: new Set([stadsdeel]),
            })
        }
        return filterFunction(state)
    }

    setText(text) {
        this.aantalElement.textContent = text
        // return this.#state
    }
}


/**
 * Geeft een functie die rijen filtert, of null (= geen filter).
 */
export function filterFunction(controlsState) {
    const {
        fractie,
        week,
        tijd,
        weekdag,
        stadsdeel,
        wijk,
        extrafilters
    } = controlsState

    const partials = [
        member('fractie', fractie),
        interval('datum_ms', ...week),
        interval('tijd_ms', ...tijd),
        member('weekdag_ma1', weekdag),
        member('stadsdeel', stadsdeel),
        member('wijk', wijk),
        ...extrafilters
            .map(([key, values]) => member(key, values))
    ]
    .filter(Boolean)

    if (!partials.length) {
        return null
    }
    return (row) => partials.every(fn => fn(row))
}
