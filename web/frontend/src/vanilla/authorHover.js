import 'vite/modulepreload-polyfill'
import { createPopper } from '@popperjs/core'

const showEvents = ['mouseenter', 'focus']
const hideEvents = ['mouseleave', 'blur']

const handleHover = (authorLinks) => {
    Array.from(authorLinks).forEach(link => {
        const content = link.getElementsByClassName("author-hover-content")[0]
        const instance = createPopper(link, content, {
            placement: 'left',
            modifiers: [
                {
                    name: 'offset',
                    options: {
                        offset: [0, 0],
                    }
                }
            ]
        })

        showEvents.forEach(event => {
            link.addEventListener(event, () => {
                content.setAttribute('data-show', '')
                instance.update()
            })
        })

        hideEvents.forEach(event => {
            link.addEventListener(event, () => {
                content.removeAttribute('data-show')
            })
        })
    })

}

const main = () => {
    const authorLinks = document.getElementsByClassName("author-hover-link")

    // Handle initial hover on page load
    handleHover(authorLinks)

    // Setup subsequent hover handling on form updates
    const form = document.getElementById("main-search-form")
    if (form) {
        form.addEventListener("submit", () => {
            handleHover(authorLinks)
        })
    }
}


document.addEventListener('DOMContentLoaded', main)