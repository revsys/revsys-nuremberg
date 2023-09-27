import 'vite/modulepreload-polyfill'
import { createPopper } from '@popperjs/core'

const showEvents = ['mouseenter', 'focus']
const hideEvents = ['mouseleave', 'blur']

const handleToolHover = (buttons) => {
    Array.from(buttons).forEach(button => {
        const queryString = `div.${button.dataset.name}-tooltip`
        const content = document.querySelector(queryString);
        const instance = createPopper(button, content, {
            placement: 'bottom',
            modifiers: [
                {
                    name: 'offset',
                    options: {
                        offset: [10, 10],
                    }
                }
            ]
        })

        showEvents.forEach(event => {
            button.addEventListener(event, () => {
                content.style.display = 'block'
                instance.update()
            })
        })

        hideEvents.forEach(event => {
            button.addEventListener(event, () => {
                content.style.display = 'none'
            })
        })
    })

}

const toolMain = () => {
    const buttons = document.getElementsByClassName("tool-button")
    console.log("Loading!")
    // Handle initial hover on page load
    handleToolHover(buttons)

}


document.addEventListener('DOMContentLoaded', toolMain)