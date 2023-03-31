'use strict'
import './main.css'

import config from './config.js'
import {App} from './components/app/index.js'

const root = document.querySelector('#app')
const app = new App(root, config)
