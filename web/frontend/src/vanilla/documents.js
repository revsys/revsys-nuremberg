import Image from './images'
import DownloadQueue from './download-queue'

// Globals
let currentPage = 1
let currentOrigin = null
let currentTool = 'scoll'
let firstPage = null
let lastPage = null
let scale = 1
let viewScale = 1
let prevViewScale = null
let expanded = false
let firstVisible = null
let currentImage = null
let images = []
let documentID = null
let totalPages = null
let pagePlaceholder = null
let imageCSSRule = null
let dragPosition = null


const goToPage = (page) => {
  images[currentPage - 1].$el.removeClass('current')
  currentPage = Math.min(Math.max(page, firstPage), lastPage)
  let pageSelector = document.getElementById("page-selector")
  pageSelector.value = currentPage

  // Toggle the current class
  let image = images[currentPage - 1]
  image.$el.addClass('current')

  firstVisible = null
  setCurrentImage(image)

}

const setPage = (page) => {
  currentPage = page;
  let pageSelector = document.getElementById("page-selector")
  pageSelector.value = page
}

const setPageDownload = (url, filename) => {
  let downloadLink = document.querySelector("a.download-page")
  downloadLink.setAttribute("href", url)
  downloadLink.setAttribute("download", filename)
}

const setFirstVisible = (newFirst) => {
  firstVisible = newFirst
  let viewport = $('.viewport-content')

  if (!currentImage || currentImage.$el[0].offsetTop + currentImage.$el[0].offsetHeight > viewport.scrollTop() + viewport.height() ||
    currentImage.$el[0].offsetTop < viewport.scrollTop()) {
    setCurrentImage(firstVisible)
  }
}

const setCurrentImage = (newImage) => {
  let viewport = $('.viewport-content')
  let previous = currentImage
  if (!newImage) {
    currentImage = previous
  }
  currentImage = newImage
  currentImage.current = true
  if (previous) {
    previous.current = false
  }

  if (currentImage !== firstVisible) {
    if (viewport.scrollTop() > currentImage.el.offsetTop || viewport.scrollTop() + viewport.height() < currentImage.el.offsetTop + currentImage.el.offsetHeight) {
      viewport.scrollTop(currentImage.el.offsetTop)
    }
    if (viewport.scrollLeft() > currentImage.el.offsetLeft || viewport.scrollLeft() + viewport.width() < currentImage.el.offsetLeft + currentImage.el.offsetWidth) {
      viewport.scrollLeft(currentImage.el.offsetLeft)
    }
  }
}

// Set which tool is in use in the overlay
const setTool = (viewport, tool) => {
  currentTool = tool
  viewport.removeClass('tool-magnify tool-scroll')
  viewport.off('mousewheel', wheelZoom)
  viewport.off('click', magnifyTool)
  viewport.off('contextmenu', magnifyTool)
  viewport.off('dblclick', magnifyTool)

  if (tool === 'magnify') {
    viewport.addClass('tool-magnify')
    viewport.on('mousewheel', wheelZoom)
    viewport.on('dblclick', magnifyTool)
  } else {
    viewport.addClass('tool-scroll')
    viewport.on('click', magnifyTool)
    viewport.on('contextmenu', magnifyTool)
  }
}

// animate switching to and from the fixed full-screen viewport
let expandingCSS

const toggleExpand = (viewport) => {
  // Handle value setting
  let old_expanded = expanded
  expanded = !expanded

  if (expanded) {
    let rect = viewport[0].getBoundingClientRect()
    expandingCSS = {
      position: 'fixed',
      left: Math.max(0, rect.left),
      top: Math.max(0, rect.top),
      right: $(window).width() - Math.max(0, rect.right),
      bottom: $(window).height() - Math.max(0, rect.bottom),
      'border-width': 0,
      'border-top-width': 0,
      'background-color': 'transparent',
    }
    viewport.css(expandingCSS)
    viewport.addClass('expanded')
    viewport.removeAttr('style')
    recalculateVisible()
  } else {
    viewport.css(expandingCSS)
    setTimeout(() => {
      viewport.removeClass('expanded', expanded)
      viewport.removeAttr('style')
      _.defer(recalculateVisible)
    }, 300)
  }
}

const scaleRatio = (thisScale) => {
  let s = thisScale || scale;
  return Math.min(10, Math.max(1, Math.floor(1 / s)));
}

const pageScale = (scale) => {
  // Page scale controls the number of visible page columns
  let viewport = $('.viewport-content')

  if (imageCSSRule) {
    let fn = ('setProperty' in imageCSSRule.style) ? 'setProperty' : 'setAttribute'
    imageCSSRule.style[fn]('font-size', 48 * scale + 'px', 'important')
    imageCSSRule.style[fn]('line-height', 64 * scale + 'px', 'important')
    imageCSSRule.style[fn]('height', 'auto', 'important')
    imageCSSRule.style[fn]('width', 100 * scale + '%', 'important')
  }

}
// Find a visible document page
const findVisible = (first, last, bounds) => {
  if (first > last) {
    return null;
  }

  let midpoint = Math.floor((first + last) / 2)
  let testPage = images[midpoint]

  let testBounds = {
    left: testPage.el.offsetLeft,
    top: testPage.el.offsetTop,
  }

  testBounds.bottom = testBounds.top + testPage.el.offsetHeight
  testBounds.right = testBounds.left + testPage.el.offsetWidth

  if (bounds.top > testBounds.bottom) {
    return findVisible(midpoint + 1, last, bounds)
  } else if (bounds.bottom < testBounds.top) {
    return findVisible(first, midpoint - 1, bounds)
  } else {
    return midpoint
  }
}

const smoothZoom = (thisViewScale, scaleOrigin) => {
  let newViewScale = Math.min(10, Math.max(1, thisViewScale))
  let viewport = $("div.viewport-content")

  if (viewScale != newViewScale) {
    let scaleDelta = newViewScale / viewScale

    if (currentOrigin === null) {
      currentOrigin = {
        x: viewport.scrollLeft(),
        y: viewport.scrollTop(),
      }
    }

    let targetOrigin = {
      x: Math.max(0, currentOrigin.x + scaleOrigin.x - scaleOrigin.x / scaleDelta),
      y: Math.max(0, currentOrigin.y + scaleOrigin.y - scaleOrigin.y / scaleDelta)
    }

    viewScale = newViewScale
    scaleView(viewScale, true, targetOrigin)
  }

  viewScale = newViewScale
}

let zoomTimeout = null

const scaleView = (scale, animate, scaleOrigin) => {
  console.log(`scaleView: ${scale} ${animate} ${scaleOrigin}`)
  let viewport = $("div.viewport-content")
  let scaleDelta = scale / (prevViewScale || 1)
  prevViewScale = scale
  let duration = 300

  let transformedOrigin = {
    x: scaleOrigin.x * scaleDelta,
    y: scaleOrigin.y * scaleDelta,
  }

  if (animate) {
    currentOrigin = transformedOrigin

    $('.document-image-layout').css({
      width: 100 * scale + '%',
      left: (- transformedOrigin.x + viewport.scrollLeft()) + 'px',
      top: (- transformedOrigin.y + viewport.scrollTop()) + 'px',
      // add extra margin to avoid forced movement at the layout boundaries before scaling completes
      margin: '0 100% 100% 0',
      transition: animate ? 'width ' + duration + 'ms, height ' + duration + 'ms, left ' + duration + 'ms, top ' + duration + 'ms' : 'none',
    })

    if (zoomTimeout) {
      clearTimeout(zoomTimeout)
    }

    zoomTimeout = setTimeout(function () {
      // clear the current animation
      zoomTimeout = null;
      currentOrigin = null;

      // reset the origin offset, and apply it as a scroll offset instead
      $('.document-image-layout').css({
        left: 0,
        top: 0,
        margin: 0,
        // add extra margin needed to avoid a jump when switching to scroll offset
        'margin-bottom': Math.max(0, (transformedOrigin.y + viewport[0].clientHeight) - $('.document-image-layout').height()) + 'px',
        transition: 'none',
      });
      viewport.scrollLeft(transformedOrigin.x);
      viewport.scrollTop(transformedOrigin.y);

      // recalculate visible pages with the new scroll coordinates
      recalculateVisible();
    }, duration);
  } else {
    $('.document-image-layout').css({
      width: 100 * scale + '%',
      left: (- transformedOrigin.x + viewport.scrollLeft()) + 'px',
      top: (- transformedOrigin.y + viewport.scrollTop()) + 'px',
      transition: 'none',
    });
  }

}

const isVisible = (n, bounds) => {
  return findVisible(n, n, bounds) !== null;
}

// Scan all images, marking which are currently visible in the viewport

const baseRecalculateVisible = () => {
  const preloadRange = 200
  let viewport = $("div.viewport-content")
  DownloadQueue.resetPriority()

  let bounds = {
    top: viewport.scrollTop(),
    left: viewport.scrollLeft(),
  }
  bounds.right = bounds.left + viewport.width()
  bounds.bottom = bounds.top + viewport.height()

  bounds.top -= preloadRange
  bounds.bottom += preloadRange

  let visibleIndex = findVisible(0, images.length - 1, bounds)
  let firstVisible = visibleIndex
  let lastVisible = visibleIndex

  // Look back for the first visible page
  for (let i = visibleIndex - 1; i >= 0; i--) {
    if (!isVisible(i, bounds)) {
      break
    }
    firstVisible = i
  }

  // Look forward for the last visible page
  for (let i = visibleIndex + 1; i < totalPages; i++) {
    if (!isVisible(i, bounds)) {
      break
    }
    lastVisible = i
  }


  // Calculate total scale for image loading
  let totalScale
  if (Modernizr.touchevents) {
    totalScale = document.body.clientWidth / window.innerWidth;
  } else {
    totalScale = scale * viewScale
  }

  // Loop over all images setting visibility
  images.forEach((image, index) => {
    if (index >= firstVisible && index <= lastVisible) {
      image.scale = totalScale
      image.visible = true
    } else {
      image.visible = false
    }
  })

  if (firstVisible !== null) {
    let testPage = images[firstVisible]
    bounds.top += preloadRange
    bounds.bottom -= preloadRange
    let testBounds = {
      top: testPage.el.offsetTop
    }
    testBounds.bottom = testBounds.top = testBounds.top + testPage.el.offsetHeight / 2
    if (testBounds.top > bounds.bottom) {
      firstVisible = Math.max(0, firstVisible - scaleRatio())
    } else if (testBounds.bottom < bounds.top) {
      firstVisible = Math.min(totalPages - 1, firstVisible + scaleRatio())
    }

    setFirstVisible(images[firstVisible])
  }
}

const recalculateVisible = _.debounce(baseRecalculateVisible, 50)

const magnifyTool = (e) => {
  let viewport = $("div.viewport-content")
  e.preventDefault()

  let scaleOrigin = {
    x: e.pageX - viewport.offset().left,
    y: e.pageY - viewport.offset().top
  }

  let newScale;

  let $page = $(e.target).closest('.document-image')
  let page

  images.forEach((image, i) => {
    if (image.el === $page[0]) {
      page = image
    }
  })

  if (page) {
    setFirstVisible(page)
    setCurrentImage(page)
  }

  // this mode is used in smooth zoom mode to focus on a page. never zooms to page
  if (e.type == 'dblclick') {
    if (viewScale >= 1 / scale) {
      newScale = 1;
      smoothZoom(newScale, scaleOrigin);
    } else {
      viewScale = 1 / scale;
      scaleView(1 / scale, true, { x: page.$el.position().left, y: page.$el.position().top });
    }
  } else {
    if (!e.which) e.which = e.keyCode;
    if (e.type === 'click' && !e.ctrlKey && !e.metaKey && !e.shiftKey) {
      // on left-click, view scale for 100% and page zoom under 100%
      if (scale == 1) {
        newScale = 1.5 * viewScale;
        console.log("Click here1")
        smoothZoom(newScale, scaleOrigin);
      } else {
        newScale = 1;
        console.log("Click here2")
        zoomToPage(page, newScale);
      }
    } else if (e.type === 'contextmenu' || e.ctrlKey || e.metaKey || e.shiftKey) {
      // on right-click, reset zoom if zoomed in on multiple columns,
      // zoom out if zoomed in on one column, add more columns otherwise
      if (viewScale > 1) {
        if (scale < 1) {
          newScale = 1;
          smoothZoom(newScale, scaleOrigin);
        } else {
          newScale = 1 / 1.5 * viewScale;
          smoothZoom(newScale, scaleOrigin);
        }
      } else {
        newScale = 1 / (scaleRatio() + 1);
        zoomToPage(page, newScale);
      }
    }
  }
}

const zoomIn = () => {
  // behavior of the "zoom in" button
  // Page zoom over 100%, smooth zoom under 100%
  let viewport = $("div.viewport-content")
  let newScale = scale * viewScale
  if (newScale < 1) {
    newScale = 1 / (scaleRatio(newScale) - 1)
    zoomToPage(_.find(images, function (img) { return img === firstVisible }), newScale)
  } else {
    newScale = 1.5 * viewScale;
    smoothZoom(newScale, { x: viewport.width() / 2, y: viewport.height() / 2 });
  }
}

const zoomOut = () => {
  // behavior of the "zoom out" button
  // Page zoom over 100%, smooth zoom under 100%
  let viewport = $("div.viewport-content")
  let newScale = scale * viewScale;
  if (newScale <= 1) {
    newScale = 1 / Math.min(10, scaleRatio(newScale) + 1);
    zoomToPage(_.find(images, function (img) { return img === firstVisible }), newScale);
  } else {
    newScale = 1 / 1.5 * viewScale;
    smoothZoom(newScale, { x: viewport.width() / 2, y: viewport.height() / 2 });
  }
}

const wheelZoom = (e) => {
  // Event handler for the scroll-to-zoom tool.
  e.preventDefault();
  let scaleOrigin = { x: e.offsetX, y: e.offsetY };
  let scaleDelta = (1 + Math.min(1, Math.max(-1, e.deltaY)) * 0.1);
  smoothZoom(viewScale * scaleDelta, scaleOrigin);
}

const zoomToPage = (page, thisScale) => {
  // This is the behavior of the scroll-mode zoom, which keeps pages fit to the viewport width
  // by adding columns. It works with or without a "target" page to center the zooming on.

  // All animation happens in "view scale", which is complicated, but it stops pages from visibly
  // bouncing around when the number of columns changes.
  console.log("Page!")
  console.dir(page)
  let viewport = $("div.viewport-content")
  let scaleDelta = thisScale / scale
  let previousScale = scale
  let laneOffset
  scale = thisScale

  console.log(`scaleDelta: ${scaleDelta}`)
  const pinnedPageOrigin = (page) => {
    if (!page) {
      return {
        x: viewport.scrollLeft(),
        y: viewport.scrollTop()
      };
    }

    return {
      x: page.$el[0].offsetLeft,
      y: page.$el[0].offsetTop
    };
  }

  if (scaleDelta < 1) {
    // zoom out

    // Don't let pages become smaller than necessary to fit all in the viewport
    if (scale < 1 / totalPages || $('.document-image-layout').height() <= viewport[0].clientHeight) {
      scale = previousScale
      return
    }

    let topOffset
    let oldLanes
    let oldLane
    let newLanes
    let newLane

    if (page) {
      // Calculate the offset needed to keep the target page in the same perceived column,
      // and apply that width to the placeholder element.
      topOffset = Math.max(0, page.$el.position().top - viewport.scrollTop());
      oldLanes = scaleRatio(previousScale)
      newLanes = scaleRatio();
      let pageIndex = parseInt(page.$el.data('page')) - 1;
      oldLane = (pageIndex + (laneOffset || 0)) % oldLanes;
      newLane = pageIndex % newLanes;

      // The column is automatically justified to whichever column is closest, minimizing perceived movement.
      if (oldLane >= (newLanes - 1) / 2) {
        oldLane = newLanes - (newLanes - 1 - oldLane);
      }
      // Only make the offset when necessary to avoid perceived movement.
      if (newLanes > 2 && totalPages > 3) {
        laneOffset = (oldLane - newLane + newLanes) % newLanes;
        pagePlaceholder.css({ width: 100 * scale * laneOffset + '%' });
      }
    } else {
      pagePlaceholder.css({ width: 0 });
    }

    // To zoom out, adjust page scale to new number of lanes
    pageScale(scale)

    let pageOrigin
    if (page) {
      // If we have a page, attempt to keep its zoom consistent to the side of the viewport it is on
      pageOrigin = pinnedPageOrigin(page)
      if (oldLane >= (newLanes - 1) / 2 || newLanes == 2 && newLane == 1) {
        pageOrigin.x = viewport.width() - viewport.width() * scaleDelta
      } else if (page) {
        pageOrigin.x = 0
      }
      pageOrigin.y -= topOffset * scaleDelta
    } else {
      pageOrigin = { x: 0, y: 0 }
    }

    // Instantly anti-scale to remove perceived page scale
    scaleView(1 / scaleDelta, false, pageOrigin)
    _.defer(function () {
      // animate the view scale to visibly zoom out (next tick, to animate)
      scaleView(1, true, { x: 0, y: pageOrigin.y / scaleDelta });
    });

  } else if (scaleDelta > 1) {
    // Zooming in is simpler since we always zoom straight to 100%:
    // 1. animate the view scale in to 100%
    let pageOrigin = pinnedPageOrigin(page);
    scaleView(scaleDelta, true, pageOrigin);
    setTimeout(() => {
      // reset other values for 1 column
      pagePlaceholder.css({ width: '0%' });
      laneOffset = 0;
      viewport.scrollTop(0);
      viewport.scrollLeft(0);
      // 2. instantly remove the view scale
      scaleView(1, false, { x: 0, y: 0 });
      // 3. replace it with page scale of a single column
      pageScale(scale);
      if (page) {
        // 4. re-adjust scroll position to keep the zoomed page in view
        viewport.scrollTop(page.$el.position().top);
        viewport.scrollLeft(page.$el.position().left);
      }
    }, 300);
  }

  setTimeout(() => {
    // At the end of a page zoom, we always have no view scaling.
    // Recalculate visible pages after a delay.
    viewScale = 1;
    recalculateVisible();
  }, 300);

}

// Mouse drag when magnified
const startDrag = (e) => {
  if (e.which !== 1 || (e.which !== 3 && currentTool !== 'magnify'))
    return;
  dragPosition = { x: e.clientX, y: e.clientY }
  $(document).on('mousemove', doDrag)
  $(document).one('mouseup', endDrag)
  e.preventDefault();
}

const endDrag = (e) => {
  dragPosition = null
  $(document).off('mousemove', doDrag)
}

const doDrag = (e) => {
  let oldPosition = dragPosition
  let newPosition = { x: e.clientX, y: e.clientY }
  let viewport = $("div.viewport-content")
  viewport.scrollLeft(viewport.scrollLeft() + oldPosition.x - newPosition.x)
  viewport.scrollTop(viewport.scrollTop() + oldPosition.y - newPosition.y)
  dragPosition = newPosition
}

// Main entry point
const main = () => {

  // Set page min/max
  let pageSelector = document.getElementById("page-selector")
  let fpage = pageSelector.firstElementChild
  let lpage = pageSelector.lastElementChild
  firstPage = parseInt(fpage.value)
  lastPage = parseInt(lpage.value)

  // Handle page changes
  $('.first-page').on('click', () => { goToPage(firstPage) })
  $('.last-page').on('click', () => { goToPage(lastPage) })
  $('.next-page').on('click', () => { goToPage(currentPage + 1) })
  $('.prev-page').on('click', () => { goToPage(currentPage - 1) })

  pageSelector.addEventListener('change', () => {
    goToPage(parseInt(pageSelector.value))
  })

  // Handle tool changes
  let magToolButton = document.querySelector("div.tool-buttons button.magnify")
  let scrollToolButton = document.querySelector("div.tool-buttons button.scroll")
  let expandToolButton = document.querySelector("div.tool-buttons button.expand")
  let zoomInButton = document.querySelector("div.zoom-buttons button.zoom-in")
  let zoomOutButton = document.querySelector("div.zoom-buttons button.zoom-out")

  let viewport = $("div.viewport-content")

  magToolButton.addEventListener('click', () => { setTool(viewport, 'magnify') })
  scrollToolButton.addEventListener('click', () => { setTool(viewport, 'scroll') })
  expandToolButton.addEventListener('click', () => { toggleExpand(viewport) })
  zoomInButton.addEventListener('click', () => { zoomIn() })
  zoomOutButton.addEventListener('click', () => { zoomOut() })

  // Handle images
  let page_images = viewport.find('.document-image')
  page_images.each((i, image) => {
    let container = $(image)
    images.push(new Image({
      el: image,
      $el: container,
      page: container.data('page'),
      alt: container.data('alt'),
      urls: {
        full: container.data('full-url'),
        screen: container.data('screen-url'),
        thumb: container.data('thumb-url')
      },
      size: {
        width: parseInt(container.data('width')),
        height: parseInt(container.data('height'))
      }
    }))
  })

  // Debugging
  console.log("Page Images:")
  console.dir(page_images)

  // Initialize images
  images.forEach((i) => { i.init() })

  // Stash document data
  documentID = viewport.data('document-id')
  totalPages = page_images.length

  let layout = viewport.find('.document-image-layout')

  if (!Modernizr.touchevents) {
    setTool(viewport, 'scroll')
  }

  let stylesheet = document.styleSheets[0]
  let rules = ('cssRules' in stylesheet) ? stylesheet.cssRules : stylesheet.rules

  stylesheet.insertRule("body.document-viewer #document-viewport .document-image { width: 100% !important; height: auto !important; }", 0)

  imageCSSRule = rules[0]
  if (imageCSSRule && imageCSSRule.cssRules) {
    imageCSSRule = imageCSSRule.cssRules[0]
  }

  pagePlaceholder = $('<div></div>').css({
    display: 'inline-block',
    width: 0,
    height: '1px',
  }).prependTo(layout);

  viewport.on('scroll', () => { console.log("scroll!"); recalculateVisible() })
  viewport.on('resize', () => { recalculateVisible() })
  viewport.on('mousedown', startDrag)

  recalculateVisible()
  setFirstVisible(images[0])
}

document.addEventListener('DOMContentLoaded', main)