import 'vite/modulepreload-polyfill'
import { createPopper } from '@popperjs/core'

const showEvents = ['mouseenter', 'focus']
const hideEvents = ['mouseleave', 'blur']

const handleHover = (buttons) => {
    Array.from(buttons).forEach(button => {
        console.log(`Name: ${button.dataset.name}`)
        const queryString = `div.${button.dataset.name}-tooltip`
        console.log(queryString)
        const content = document.querySelector(queryString);
        console.log(button, content)
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

const main = () => {
    const buttons = document.getElementsByClassName("tool-button")
    console.log("Loading!")
    // Handle initial hover on page load
    handleHover(buttons)

}


document.addEventListener('DOMContentLoaded', main)