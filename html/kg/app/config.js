'use strict'

/**
 * Data URL's
 */
export const bronnen = {
    containers: {
        url: './data/containers.min.json',
        compressed: true,
    },
    gebieden: {
        url: './data/gebieden.min.json',
        compressed: true,
    },
    wegingen: {
        url: './data/wegingen.min.json',
        compressed: true,
    },
    wegingenDelta: {
        url: './data/wegingen.3min.json',
        interval: 2 * 60 * 1000,
        compressed: true,
    }
}

/**
 * Kleurstandaard van Afval Circulair.
 */
export const fractieKleur = {
    'GFT': [65, 150, 72],
    'Glas': [255, 194, 10],
    'Papier': [0, 128, 198],
    'Plastic': [241, 101, 35],
    'Rest': [74, 89, 97],
    'Textiel': [158, 31, 98],
}

/**
 * Based on
 * https://coolors.co/palette/001219-005f73-0a9396-94d2bd-e9d8a6-ee9b00-ca6702-bb3e03-ae2012-9b2226
 * interpolated to create 24 colours.
 */
export const uurKleur = {
    0: [52, 23, 29],        // 34171D
    1: [26, 21, 27],        // 1A151B
    2: [0, 18, 25],
    3: [0, 57, 70],         // 003946
    4: [0, 95, 115],
    5: [5, 121, 133],       // 057985
    6: [10, 147, 150],
    7: [79, 179, 170],      // 4FB3AA
    8: [148, 210, 189],
    9: [191, 213, 178],     // BFD5B2
    10: [233, 216, 166],
    11: [236, 186, 83],     // ECBA53
    12: [238, 155, 9],
    13: [220, 129, 1],      // DC8101
    14: [202, 103, 2],
    15: [195, 83, 3],       // C35303
    16: [187, 62, 3],
    17: [181, 47, 11],      // B52F0B
    18: [174, 32, 18],
    19: [165, 33, 28],      // A5211C
    20: [155, 34, 38],
    21: [129, 31, 36],      // 811F24
    22: [103, 29, 34],      // 671D22
    23: [78, 26, 32],       // 4E1A20
}

/**
 * Een eigen kleur voor elke week van het jaar.
 * Modulo vijf omdat we maximaal vijf weken data tonen.
 * https://coolors.co/390099-9e0059-ff0054-ff5400-ffbd00
 */
export const week5Kleur = {
    0: [57, 0, 153],
    1: [158, 0, 89],
    2: [255, 0, 84],
    3: [255, 84, 0],
    4: [255, 189, 0],
}

/**
 * Een kleurschema van 7 kleuren.
 * https://colorswall.com/palette/171311
 * Let op, maandag = '1'.
 */
export const weekdagKleur = {
    '1': [255, 255, 0],     // Yellow
    '2': [0, 255, 0],       // Green
    '3': [0, 255, 255],     // Cyan
    '4': [0, 0, 255],       // Blue
    '5': [255, 0, 255],     // Magenta
    '6': [255, 0, 0],       // Red
    '0': [0, 0, 0],         // Black
}

/**
 * The map location and zoom when state doesn't define this (yet).
 */
export const initialViewState = {
    longitude: 4.8978,
    latitude: 52.35,
    zoom: 17,
    // minZoom: 9.5,
    maxZoom: 21.5,
}

/**
 * GPS/WebMercator map tiles van Gemeente Amsterdam.
 */
export const kaartLayerProps = {
    data: 'https://t1.data.amsterdam.nl/topo_wm/{z}/{x}/{y}.png',
    // data: [
    //     'https://t1.data.amsterdam.nl/topo_wm/{z}/{x}/{y}.png',
    //     'https://t2.data.amsterdam.nl/topo_wm/{z}/{x}/{y}.png',
    //     'https://t3.data.amsterdam.nl/topo_wm/{z}/{x}/{y}.png',
    //     'https://t4.data.amsterdam.nl/topo_wm/{z}/{x}/{y}.png',
    // ],
    tileSize: 256,
    minZoom: 10.5,
    maxZoom: 21.5,
    extent: [4.5, 52.16, 5.5, 52.69],   // minX, minY, maxX, maxY
}

/**
 * De stadsdelen van Amsterdam.
 */
export const stadsdelenLayerProps = {
    getWidth: 5,
    widthScale: 1,
    widthMinPixels: 2,
    getColor: [0, 0, 0],
    getPath: d => d.geometrie,
}

/**
 * De wijken van Amsterdam.
 */
export const wijkenLayerProps = {
    filled: true,
    getFillColor: [0, 0, 0, 0],     // transparent.
    stroked: true,
    lineWidthMinPixels: 1,
    getLineColor: [80, 80, 80],
    getPolygon: d => d.geometrie,
}

/**
 * Containerlocaties met afvalfractie.
 */
export const containersLayerProps = {
    filled: true,
    getFillColor: ({fractie}) => fractieKleur[fractie] ?? [80, 80, 80],
    stroked: false,
    getLineColor: ({fractie}) => fractieKleur[fractie] ?? [80, 80, 80],
    getRadius: 1,
    radiusScale: 1,
    radiusMinPixels: 0,
    radiusMaxPixels: 100,
    getPosition: d => [d.lon, d.lat],
}

/**
 * Wegingen van geledigde afvalcontainers.
 */
export const wegingenLayerProps = {
    filled: true,
    getFillColor: [80, 80, 80],
    stroked: true,
    lineWidthMinPixels: 1,
    lineWidthMaxPixels: 5,
    getLineColor: [80, 80, 80],
    getRadius: 10,
    radiusScale: 1,
    radiusMinPixels: 2,
    radiusMaxPixels: 30,
    //getPosition: d => [d.lon, d.lat],
    // getPosition wordt geregeld in Kaart.renderState().
}

/**
 * Marker geeft aan welke rij in de tabel te muis aanwijst.
 */
export const highlightLayerProps = {
    filled: true,
    getFillColor: [255, 0, 255],
    stroked: true,
    getLineColor: [255, 0, 255],
    getRadius: 10,
    radiusScale: 1,
    radiusMinPixels: 5,
    radiusMaxPixels: 30,
    getPosition: d => [d.lon, d.lat],
}

/**
 * Kolommen voor ag-grid rendering van wegingen.
 */
export const columnDefs = [
    {
        field: 'kenteken',
        title: 'Kenteken',
        width: 100,
    },
    {
        field: 'volgnummer',
        title: 'Volgnr',
        width: 80,
        hozAlign: 'right',
    },
    {
        field: 'datum_ms',
        title: 'Datum',
        width: 100,
        formatter: (cell) => cell.getData().datum_str,
    },
    {
        field: 'tijd_ms',
        title: 'Tijd',
        width: 60,
        formatter: (cell) => cell.getData().tijd_str,
    },
    {
        field: 'fractie',
        title: 'Fractie',
        width: 80,
    },
    {
        field: 'eerste_weging',
        title: 'Eerste weging',
        width: 80,
        formatter: (cell) => cell.getData().eerste_weging?.toLocaleString(),
        hozAlign: 'right',
    },
    {
        field: 'tweede_weging',
        title: 'Tweede weging',
        width: 80,
        formatter: (cell) => cell.getData().tweede_weging?.toLocaleString(),
        hozAlign: 'right',
    },
    {
        field: 'netto_gewicht',
        title: 'Netto gewicht',
        width: 80,
        formatter: (cell) => cell.getData().netto_gewicht?.toLocaleString(),
        hozAlign: 'right',
    },
    {
        field: 'afstand',
        title: 'Afstand',
        width: 80,
        formatter: (cell) => cell.getData().afstand?.toLocaleString(),
        hozAlign: 'right',
    },
    {
        field: 'containers',
        title: 'Containers',
        width: 200,
        formatter: (cell) => cell.getData().containers?.join(', '),
    },
    {
        field: 'adres',
        title: 'Adres',
        width: 300,
    },
    {
        field: 'buurt',
        title: 'Buurt',
        width: 250,
    },
    {
        field: 'stadsdeel',
        title: 'Stadsdeel',
        width: 100,
    },
]


/**
 * Exporteer gestructureerd voor App.
 */
export default {
    data: {
        bronnen,
    },
    kaart: {
        kleurschemas: {
            fractie: fractieKleur,
            weekdag_ma1: weekdagKleur,
            week_mod5: week5Kleur,
            uur: uurKleur,
        },
        layerProps: {
            kaart: kaartLayerProps,
            stadsdelen: stadsdelenLayerProps,
            wijken: wijkenLayerProps,
            containers: containersLayerProps,
            wegingen: wegingenLayerProps,
            highlight: highlightLayerProps,
        },
        initialViewState,
    },
    tabel: {
        columns: columnDefs,
        rowHeight: 24,
    },
}
