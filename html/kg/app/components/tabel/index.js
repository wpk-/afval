'use strict'
import 'tabulator-tables/dist/css/tabulator.min.css'
import 'tabulator-tables/dist/css/tabulator_simple.min.css'

import Tabulator from 'tabulator-tables/src/js/core/Tabulator.js'
import LayoutModule from 'tabulator-tables/src/js/modules/Layout/Layout.js'
import LocalizeModule from 'tabulator-tables/src/js/modules/Localize/Localize.js'
import CommsModule from 'tabulator-tables/src/js/modules/Comms/Comms.js'
import FilterModule from 'tabulator-tables/src/js/modules/Filter/Filter.js'
import FormatModule from 'tabulator-tables/src/js/modules/Format/Format.js'
import InteractionModule from 'tabulator-tables/src/js/modules/Interaction/Interaction.js'
import SortModule from 'tabulator-tables/src/js/modules/Sort/Sort.js'

Tabulator.registerModule([
    LayoutModule,
    LocalizeModule,
    CommsModule,
    FilterModule,
    FormatModule,
    InteractionModule,
    SortModule,
])

import {TabelState} from './state.js'


/**
 * Events:
 *  - change (event.detail = state)
 *  - scroll (event.detail = state)
 *  - rowover (event.detail = row item)
 *  - rowout (event.detail = row item)
 * 
 * Methods:
 *  - render(stateUpdates)
 *  - setFilter(function)
 *  - setData(wegingen)
 */
export class Tabel {
    #state

    constructor(rootNode, config, data) {
        // state
        this.#state = TabelState.restore(rootNode.id)

        this.tabular = new Tabulator(rootNode, {
            initialSort: this.#state.sort,
            ...config
        })

        // Filter changed. Automatically triggered on programmatic changes, too.
        this.tabular.on('dataFiltered', this._onChange)

        // User changed sort order.
        this.tabular.on('dataSorting', this._onSort)

        // Data sorted, window resized, filter changed, etc.
        this.tabular.on('renderComplete', this._onScroll)

        // Table scrolled. Different rows visible.
        this.tabular.on('scrollVertical', this._onScroll)

        // Mouse hovers a row.
        this.tabular.on('rowMouseEnter', this._onMouseEnter)

        // Mouse leaves the row.
        this.tabular.on('rowMouseLeave', this._onMouseLeave)

        // patches
        this.setData = this.#waitForTableBuilt(this.setData)
        this.setFilter = this.#waitForTableBuilt(this.setFilter)

        // data
        if (data) {
            Promise.resolve(data).then(x => this.setData(x))
        }
    }

    get rootElement() {return this.tabular.element}

    _onChange = (_, rows) => {
        // .on('dataFiltered', _onFilter)
        // filters - array of filters currently applied
        // rows - array of row components that pass the filters
        const state = this.#state
        state.active = new Set(rows.map(row => row.getIndex()))
        this.rootElement
        .dispatchEvent(new CustomEvent('change', {detail: state}))
    }

    _onScroll = () => {
        const state = this.#state
        const rows = this.tabular.getRows('visible')
        state.scroll = new Set(rows.map(row => row.getIndex()))
        this.rootElement
        .dispatchEvent(new CustomEvent('scroll', {detail: state}))
    }

    _onSort = (sorters) => {
        const state = this.#state
        state.sort = sorters?.length
            ? sorters.map(({field, dir}) => ({column: field, dir}))
            : []
    }

    _onMouseEnter = (_, row) => {
        const item = row.getData()
        this.rootElement
        .dispatchEvent(new CustomEvent('rowover', {detail: item}))
    }

    _onMouseLeave = (_, row) => {
        const item = row.getData()
        this.rootElement
        .dispatchEvent(new CustomEvent('rowout', {detail: item}))
    }

    // Required for state restore but not used.
    // Restored state is always empty.
    render() {}

    setFilter(func) {
        const tabular = this.tabular

        if (func) {
            tabular.setFilter(func)
        }
        else {
            tabular.clearFilter()
        }
    }

    getData(selection) {
        return this.tabular.getData(selection)
    }

    setData = async (data) => {
        await this.tabular.getDataCount()
            ? this.tabular.replaceData(data)
            : this.tabular.setData(data)
    }

    // Tabulator vindt het niet fijn als we dingen doen als t.setFilter(...)
    // voordat de tabel geinitialiseerd is. Met #waitFor patchen we onze eigen
    // setFilter methode zodat deze de aanroep vertraagt totdat Tabulator wel
    // geinitialiseerd is. Hetzelfde geldt voor setData.
    #waitForTableBuilt(method) {
        const methodName = method.name
        let methodArgs = undefined
        let called = false

        this.tabular.on('tableBuilt', () => {
            this[methodName] = method
            if (called) {
                this[methodName](...methodArgs)
            }
        })

        return (...args) => {
            called = true
            methodArgs = args
        }
    }
}
