import * as $ from 'manhattan-essentials'
import * as manage from 'manhattan-manage'

import * as charts from './helpers/charts.js'


function onContentLoaded() {

    // Initialise manhattan manage
    manage.init(window.MANHATTAN_CONTENT_UPDATES_SIGNAL)

    // Initialize charts
    charts.init()
}

$.listen(window, {'DOMContentLoaded': onContentLoaded})
