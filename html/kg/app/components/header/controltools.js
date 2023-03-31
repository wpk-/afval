'use strict'

export const parseChecks = (boxes) =>
    new Set(
        [...boxes]
        .filter(input => input.checked)
        .map(input => input.value)
    )

export const renderChecks = (boxes, selected) =>
    [...boxes].forEach(input => input.checked = selected.has(input.value))

export const parseRadios = (boxes) =>
    [...boxes].find(input => input.checked)?.value

export const renderRadios = (boxes, value) =>
    [...boxes].find(input => input.value === value).checked = true

export const parseRange = (start, end) =>
    [start.valueAsNumber, end.valueAsNumber + parseInt(end.dataset.offset || 0)]

export const renderRange = (start, end, [rangeStart, rangeEnd]) => {
    start.valueAsNumber = rangeStart
    end.valueAsNumber = rangeEnd - parseInt(end.dataset.offset || 0)
}

export const parseSelect = (select) =>
    select.multiple
    ? new Set(
            [...select.selectedOptions]
            .map(option => option.value)
            .filter(Boolean)
        )
    : select.value

export const renderSelect = (select, selected) =>
    select.multiple
    ? selected.size
        ? [...select.options].forEach(
            option => option.selected = selected.has(option.value))
        : (select.selectedIndex = 0)
    : (select.value = selected)

export const renderSelectDisabled = (select, key, accepted) =>
    [...select.options]
    .slice(1)
    .forEach(accepted.size
        ? option => option.disabled = !accepted.has(option.dataset[key])
        : option => option.disabled = false
    )
