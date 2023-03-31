'use strict'

const labelTemplate = document.createElement('template')

labelTemplate.innerHTML = `
<li class="label">
    <span class="text"></span>
    <a href="#remove" class="action">×</a>
</li>`

const makeLabel = (text) => {
    const label = labelTemplate.content.cloneNode(true).querySelector('li')
    label.querySelector('.text').textContent = text
    return label
}


export class LabelsList {
    #values = new WeakMap()

    constructor(rootNode, textFunction) {
        this.rootNodeRef = new WeakRef(rootNode)
        this.textFunction = textFunction
    }

    get rootElement() {return this.rootNodeRef.deref()}

    get labelElements() {
        return this.rootElement.querySelectorAll('.label')
    }

    get labels() {
        return [...this.labelElements].map(elm => this.#values.get(elm))
    }

    set labels(list) {
        // list = [object1, object2, ...]
        const labelText = this.textFunction

        this.#values = new WeakMap()
        
        this.rootElement
        .replaceChildren(...
            list.map(obj => {
                const text = labelText(obj)
                const label = makeLabel(text)
                this.#values.set(label, obj)
                return label
            })
        )
    }

    remove(labelElement) {
        labelElement.closest('.label').remove()
    }
}
