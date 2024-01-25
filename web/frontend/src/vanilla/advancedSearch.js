import 'vite/modulepreload-polyfill'
import { createPopper } from '@popperjs/core'

const showEvents = ['mouseenter', 'focus']
const hideEvents = ['mouseleave', 'blur']

const handleHover = (helpLabels) => {
    Array.from(helpLabels).forEach(item => {
        const content_id = item.dataset.content_id
        const content = document.getElementById(content_id)
        const instance = createPopper(item, content, {
            placement: 'left',
            modifiers: [
                {
                    name: 'offset',
                    options: {
                        offset: [0, -100],
                    }
                }
            ]
        })

        showEvents.forEach(event => {
            item.addEventListener(event, () => {
                content.setAttribute('data-show', '')
                instance.update()
            })
        })

        hideEvents.forEach(event => {
            item.addEventListener(event, () => {
                content.removeAttribute('data-show')
            })
        })
    })

}

const main = () => {
    const helpLabels = document.getElementsByClassName("help-label")
    console.dir(helpLabels)
    // Handle initial hover on page load
    handleHover(helpLabels)

    console.log("advancedSearch.js")
}


document.addEventListener('DOMContentLoaded', main)