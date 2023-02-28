import 'vite/modulepreload-polyfill'
import { createPopper } from '@popperjs/core'

const showEvents = ['mouseenter', 'focus']
const hideEvents = ['mouseleave', 'blur']


const main = () => {
    const authorLinks = document.getElementsByClassName("author-hover-link")

    Array.from(authorLinks).forEach(link => {
        const content = link.getElementsByClassName("author-hover-content")[0]
        const instance = createPopper(link, content, {
            placement: 'left',
            modifiers: [
                {
                    name: 'offset',
                    options: {
                        offset: [0, 4],
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


document.addEventListener('DOMContentLoaded', main)