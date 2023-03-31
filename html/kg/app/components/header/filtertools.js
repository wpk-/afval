'use strict'

// true iff both values are equal.
export const eqTest = (key, value) =>
    ({[key]: rowValue}) => rowValue === value

// true iff rowValue >= value.
export const gteTest = (key, value) =>
    ({[key]: rowValue}) => value <= rowValue

// true iff start <= rowValue < end. (if start > end, wrap around.)
export const intervalTest = (key, start, end) =>
    (start < end)
    ? ({[key]: rowValue}) => start <= rowValue && rowValue < end
    : ({[key]: rowValue}) => start <= rowValue || rowValue < end

// true iff rowValue < value.
export const ltTest = (key, value) =>
    ({[key]: rowValue}) => rowValue < value

// true iff rowValue in set.
export const membershipTest = (key, set) =>
    ({[key]: rowValue}) => set.has(rowValue)

// true iff rowValue is a substring of str.
export const substringTest = (key, str) =>
    ({[key]: rowValue=''}) => ~String(rowValue).toLowerCase().indexOf(str)

// Equality test only if value is not null or undefined.
export const equal = (key, value) =>
    (value === null || typeof value === 'undefined')
    ? null
    : eqTest(key, value)

// Membership test only if set is not empty.
export const member = (key, set) =>
    set.size ? membershipTest(key, set)
    : null

// Interval test if start and end are set.
// Single sided test if either start or end is set.
export const interval = (key, start, end) =>
    isNaN(start) ? (!isNaN(end) ? ltTest(key, end) : null)
    : isNaN(end) ? gteTest(key, start)
    : start !== end ? intervalTest(key, start, end)
    : null

// Substring test if the search value is not empty.
export const substring = (key, token) =>
    token
    ? substringTest(key, String(token).toLowerCase())
    : null
