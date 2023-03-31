'use strict'

const debounce = (fn, ms) => {
    let fnArgs = []
    let tid = null

    return (...args) => {
        fnArgs = args
        clearTimeout(tid)
        tid = setTimeout(() => fn(...fnArgs), ms)
    }
}

export class StoredState {
    constructor(name) {
        
        const storeThis = debounce(() => {
            const obj = this.toJSON()
            const str = JSON.stringify(obj)
            localStorage.setItem(name, str)
        }, 2000)

        return new Proxy(this, {
            set(target, name, value, receiver) {
                storeThis()
                return Reflect.set(...arguments)
            },
            deleteProperty(target, name) {
                storeThis()
                return Reflect.deleteProperty(...arguments)
            },
        })
    }

    static restore(name, defaultState) {
        const str = localStorage.getItem(name)
        const obj = JSON.parse(str)
        return new this(name, {...defaultState, ...obj})
    }

    // Abstract method.
    // Implement this in all subclasses.
    toJSON() {return {}}
}
