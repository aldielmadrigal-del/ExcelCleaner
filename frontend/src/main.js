import { UniverSheetsCorePreset } from '@univerjs/preset-sheets-core'
import sheetsCoreEnUS from '@univerjs/preset-sheets-core/locales/en-US'
import {
    createUniver,
    LocaleType,
    mergeLocales
} from '@univerjs/presets'

import '@univerjs/preset-sheets-core/lib/index.css'
import './style.css'


const app = document.querySelector('#app')

app.innerHTML = `
    <div id="upload-screen">

        <h1>Excel Cleaner</h1>

        <p>
            Analiza tu archivo y visualiza el resultado completo.
        </p>

        <input
            id="file-input"
            type="file"
            accept=".xlsx,.xls,.csv"
        >

        <button id="analyze-button">
            Analizar archivo
        </button>

        <div id="status"></div>

    </div>


    <div id="viewer-screen">

        <div id="viewer-header">

            <button id="back-button">
                ← Volver
            </button>

            <span id="viewer-title">
                Vista previa
            </span>

        </div>


        <div id="changes-panel">

            <div class="changes-header">

                <div>

                    <h2>
                        Cambios detectados
                    </h2>

                    <p>
                        Revisa el archivo original y el resultado
                        corregido antes de descargarlo.
                    </p>

                </div>


                <div id="total-changes-badge">
                    0 cambios
                </div>

            </div>


            <div id="change-cards"></div>

            <div id="price-section"></div>

        </div>


        <div id="comparison-area">

            <div class="spreadsheet-panel">

                <div class="spreadsheet-title">

                    <strong>
                        Original
                    </strong>

                    <span>
                        Archivo recibido
                    </span>

                </div>

                <div
                    id="univer-before"
                    class="univer-container"
                ></div>

            </div>


            <div class="spreadsheet-panel">

                <div class="spreadsheet-title">

                    <strong>
                        Corregido
                    </strong>

                    <span>
                        Resultado de la limpieza
                    </span>

                </div>

                <div
                    id="univer-after"
                    class="univer-container"
                ></div>

            </div>

        </div>

    </div>
`


const uploadScreen =
    document.querySelector('#upload-screen')

const viewerScreen =
    document.querySelector('#viewer-screen')

const fileInput =
    document.querySelector('#file-input')

const analyzeButton =
    document.querySelector('#analyze-button')

const status =
    document.querySelector('#status')

const backButton =
    document.querySelector('#back-button')

const viewerTitle =
    document.querySelector('#viewer-title')

const totalChangesBadge =
    document.querySelector('#total-changes-badge')

const changeCards =
    document.querySelector('#change-cards')


function columnLetter(number) {

    let result = ''

    while (number > 0) {

        number--
        result =
            String.fromCharCode(
                65 + (number % 26)
            ) + result

        number =
            Math.floor(number / 26)
    }

    return result
}


function buildSheetData(sheet, mode) {

    const rows =
        mode === 'before'
            ? sheet.original_preview
            : sheet.cleaned_preview

    const cellData = {}

    rows.forEach((row, rowIndex) => {

        cellData[rowIndex] = {}

        row.cells.forEach(
            (cell, columnIndex) => {

                cellData[rowIndex][columnIndex] = {
                    v: cell.value
                }

            }
        )

    })

    return cellData
}


function buildWorkbook(result, mode) {

    const sheets = {}
    const sheetOrder = []

    result.sheets.forEach(
        (sheet, sheetIndex) => {

            const sheetId =
                `sheet-${mode}-${sheetIndex}`

            sheetOrder.push(sheetId)

            const rows =
                mode === 'before'
                    ? sheet.original_preview
                    : sheet.cleaned_preview

            const rowCount =
                rows.length

            const columnCount =
                sheet.columns

            const cellData =
                buildSheetData(
                    sheet,
                    mode
                )

            sheets[sheetId] = {

                id: sheetId,

                name: sheet.name,

                rowCount:
                    Math.max(
                        rowCount,
                        50
                    ),

                columnCount:
                    Math.max(
                        columnCount + 5,
                        20
                    ),

                cellData

            }

        }
    )

    return {

        id:
            `excel-cleaner-${mode}-${Date.now()}`,

        name:
            `Excel Cleaner ${mode}`,

        sheetOrder,

        sheets

    }
}


function createViewer(
    containerId,
    result,
    mode
) {

    const {
        univerAPI
    } = createUniver({

        locale:
            LocaleType.EN_US,

        locales: {

            [LocaleType.EN_US]:
                mergeLocales(
                    sheetsCoreEnUS
                )

        },

        presets: [

            UniverSheetsCorePreset({

                container:
                    containerId,

                toolbar:
                    false,

                contextMenu:
                    false,

                formulaBar:
                    false,

                footer: {

                    sheetBar:
                        true,

                    statisticBar:
                        false,

                    menus:
                        false,

                    zoomSlider:
                        false,

                    addSheetButtonConfig: {

                        show:
                            false

                    }

                }

            })

        ]

    })


    univerAPI.createWorkbook(
        buildWorkbook(
            result,
            mode
        )
    )


    univerAPI.addEvent(

        univerAPI.Event.LifeCycleChanged,

        ({ stage }) => {

            if (
                stage ===
                univerAPI.Enum
                    .LifecycleStages
                    .Rendered
            ) {

                const workbook =
                    univerAPI.getActiveWorkbook()


                workbook.disableSelection()


                const permission =
                    workbook.getWorkbookPermission()


                permission.setReadOnly()


                univerAPI.setPermissionDialogVisible(
                    false
                )

            }

        }

    )


    return univerAPI
}


function buildChangeSummary(result) {

    let whitespace = 0
    let duplicates = 0
    let emptyRows = 0


    result.sheets.forEach(
        (sheet) => {

            whitespace +=
                sheet.whitespace_cells

            duplicates +=
                sheet.duplicate_rows

            emptyRows +=
                sheet.empty_rows

        }
    )


    totalChangesBadge.textContent =
        `${result.total_changes} ${
            result.total_changes === 1
                ? 'cambio'
                : 'cambios'
        }`


    const cards = []


    if (whitespace > 0) {

        cards.push(`

            <div class="change-card">

                <strong>
                    ${whitespace}
                </strong>

                <span>
                    ${
                        whitespace === 1
                            ? 'celda corregida'
                            : 'celdas corregidas'
                    }
                </span>

                <small>
                    Espacios innecesarios
                </small>

            </div>

        `)

    }


    if (duplicates > 0) {

        cards.push(`

            <div class="change-card">

                <strong>
                    ${duplicates}
                </strong>

                <span>
                    ${
                        duplicates === 1
                            ? 'fila eliminada'
                            : 'filas eliminadas'
                    }
                </span>

                <small>
                    Filas duplicadas
                </small>

            </div>

        `)

    }


    if (emptyRows > 0) {

        cards.push(`

            <div class="change-card">

                <strong>
                    ${emptyRows}
                </strong>

                <span>
                    ${
                        emptyRows === 1
                            ? 'fila eliminada'
                            : 'filas eliminadas'
                    }
                </span>

                <small>
                    Filas completamente vacías
                </small>

            </div>

        `)

    }


    if (cards.length === 0) {

        changeCards.innerHTML = `

            <div class="no-changes">

                No se detectaron cambios.

            </div>

        `

    } else {

        changeCards.innerHTML =
            cards.join('')

    }


    const priceSection =
        document.querySelector(
            '#price-section'
        )


    if (priceSection) {

        priceSection.innerHTML = `

            <div class="price-box">

                <div>

                    <span class="price-label">
                        Precio de limpieza
                    </span>

                    <strong class="price-value">
                        $${result.price}
                    </strong>

                </div>


                <button
                    id="continue-payment-button"
                    type="button"
                >

                    ${
                        result.price === 0
                            ? 'Descargar archivo limpio'
                            : 'Continuar al pago'
                    }

                </button>

            </div>

        `


        const downloadButton =
            document.querySelector(
                '#continue-payment-button'
            )


        if (
            downloadButton &&
            result.price === 0 &&
            result.download_id
        ) {

            downloadButton.addEventListener(
                'click',
                () => {

                    window.location.href =
                        `/api/download/${encodeURIComponent(
                            result.download_id
                        )}`

                }
            )

        }

    }

}


function showViewer(
    result,
    filename
) {

    uploadScreen.style.display =
        'none'

    viewerScreen.style.display =
        'flex'


    viewerTitle.textContent =
        `${filename} — ${
            result.sheet_count
        } hoja(s) — ${
            result.total_changes
        } cambio(s)`


    buildChangeSummary(result)


    const beforeAPI =
        createViewer(
            'univer-before',
            result,
            'before'
        )


    const afterAPI =
        createViewer(
            'univer-after',
            result,
            'after'
        )


    let changingSheet =
        false


    beforeAPI.addEvent(

        beforeAPI.Event.BeforeSheetActivate,

        (event) => {

            if (changingSheet) {
                return
            }

            const sheetId =
                event.sheetId

            changingSheet = true

            try {

                afterAPI
                    .getActiveWorkbook()
                    .getActiveSheet()
                    .activate()

                const workbook =
                    afterAPI
                        .getActiveWorkbook()

                const sheet =
                    workbook
                        .getSheetBySheetId(
                            sheetId.replace(
                                'sheet-before-',
                                'sheet-after-'
                            )
                        )

                if (sheet) {
                    sheet.activate()
                }

            } finally {

                changingSheet =
                    false

            }

        }

    )


    afterAPI.addEvent(

        afterAPI.Event.BeforeSheetActivate,

        (event) => {

            if (changingSheet) {
                return
            }

            const sheetId =
                event.sheetId

            changingSheet = true

            try {

                const workbook =
                    beforeAPI
                        .getActiveWorkbook()

                const sheet =
                    workbook
                        .getSheetBySheetId(
                            sheetId.replace(
                                'sheet-after-',
                                'sheet-before-'
                            )
                        )

                if (sheet) {
                    sheet.activate()
                }

            } finally {

                changingSheet =
                    false

            }

        }

    )

}


analyzeButton.addEventListener(
    'click',
    async () => {

        const file =
            fileInput.files[0]


        if (!file) {

            status.textContent =
                'Selecciona primero un archivo.'

            return

        }


        analyzeButton.disabled =
            true


        status.textContent =
            'Analizando archivo...'


        try {

            const formData =
                new FormData()


            formData.append(
                'file',
                file
            )


            const response =
                await fetch(
                    '/api/analyze',
                    {
                        method:
                            'POST',

                        body:
                            formData
                    }
                )


            const result =
                await response.json()


            if (!response.ok) {

                throw new Error(
                    result.error ||
                    'Error al analizar el archivo.'
                )

            }


            showViewer(
                result,
                file.name
            )


        } catch (error) {

            console.error(error)


            status.textContent =
                `Error: ${error.message}`


            analyzeButton.disabled =
                false

        }

    }
)


backButton.addEventListener(
    'click',
    () => {

        window.location.reload()

    }
)
