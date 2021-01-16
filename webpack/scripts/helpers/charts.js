import Chart from 'chart.js'
import * as $ from 'manhattan-essentials'


// -- Utils --

/**
 * Return the given integer value as a
 */
function thousands(value) {
    if (isNaN(value)) {
        return value
    }

    const parts = value.toString().split('.')
    parts[0]
        .toString()
        .replace(/\B(?=(\d{3})+(?!\d))/g, ',')

    if (parts.length === 1) {
        return parts[0]
    }
    return `${parts[0]}.${parts[1]}`
}


// -- Chart types --

function createLineChart(elm) {

    const chartData = JSON.parse(elm.getAttribute('data-chart--data'))
    const labels = JSON.parse(elm.getAttribute('data-chart--labels') || '[""]')

    let chart = new Chart(
        $.one('canvas', elm).getContext('2d'),
        {
            'type': 'line',
            'data': chartData,
            'options': {
                'scales': {
                    'yAxes': [{
                        'ticks': {
                            'callback': (value, index, values) => {
                                return thousands(value)
                            }
                        }
                    }]
                },
                'tooltips': {
                    'backgroundColor': 'rgba(0, 0, 0, 0.8)',
                    'callbacks': {
                        'label': (item, data) => {
                            const value = data
                                .datasets[item.datasetIndex]
                                .data[item.index]

                            const label = labels[item.datasetIndex]
                                .toLowerCase()

                            return `${thousands(value)} ${label}`
                        }
                    }
                }
            }
        }
    )
}


// -- Init --

export function init() {

    // Configure chart defaults
    Chart.defaults.global.layout = {
        'padding': {
            'left': 40,
            'right': 65,
            'top': 65,
            'bottom': 25
        }
    }
    Chart.defaults.global.responsive = true
    Chart.defaults.global.maintainAspectRatio = false
    Chart.defaults.global.legend.display = false
    Chart.defaults.global.tooltips.bodyFontSize = 14
    Chart.defaults.global.tooltips.bodyFontStyle = 'bold'
    Chart.defaults.global.tooltips.cornerRadius = 0
    Chart.defaults.global.tooltips.displayColors = false
    Chart.defaults.global.tooltips.xPadding = 10
    Chart.defaults.global.tooltips.xAlign = 'center'
    Chart.defaults.global.tooltips.yAlign = 'bottom'
    Chart.defaults.global.tooltips.yPadding = 15
    Chart.defaults.global.tooltips.callbacks.labelColor = () => {
        return '#fff'
    }
    Chart.scaleService.updateScaleDefaults(
        'linear',
        {
            'ticks': {
                'beginAtZero': true,
                'fontColor': '#999',
                'fontFamily': 'Ubuntu, Helvetica, sans-serif',
                'fontSize': 14,
                'maxTicksLimit': 4
            }
        }
    )
    Chart.scaleService.updateScaleDefaults(
        'category',
        {
            'gridLines': {'display': false},
            'ticks': {
                'autoSkip': true,
                'fontColor': '#999',
                'fontFamily': 'Ubuntu, Helvetica, sans-serif',
                'fontSize': 14,
                'maxRotation': 0,
                'maxTicksLimit': 4
            }
        }
    )

    // Find and create charts within the page
    for (let chartElm of $.many('[data-chart]')) {

        const chartType = chartElm.getAttribute('data-chart--type')

        switch (chartType) {

        case 'line':
            createLineChart(chartElm)
            break

        // no default

        }
    }

}
