
let currentLoad = null;
let loadingTimeout = null;

const spinnerOptions = {
  lines: 17 // The number of lines to draw
  , length: 3 // The length of each line
  , width: 3 // The line thickness
  , radius: 10 // The radius of the inner circle
  , scale: 1 // Scales overall size of the spinner
  , corners: 1 // Corner roundness (0..1)
  , color: '#9ec0c1' // #rgb or #rrggbb or array of colors
  , opacity: 0.25 // Opacity of the lines
  , rotate: 0 // The rotation offset
  , direction: 1 // 1: clockwise, -1: counterclockwise
  , speed: 1 // Rounds per second
  , trail: 60 // Afterglow percentage
  , fps: 15 // Frames per second when using setTimeout() as a fallback for CSS
  , zIndex: 2e9 // The z-index (defaults to 2000000000)
  , className: 'spinner' // The CSS class to assign to the spinner
  , top: '50%' // Top position relative to parent
  , left: '40px' // Left position relative to parent
  , shadow: false // Whether to render a shadow
  , hwaccel: false // Whether to use hardware acceleration
  , position: 'absolute' // Element positioning
}

export const min = (nums) => {
  if (nums.length) return Math.min(...nums)
}

export const max = (nums) => {
  if (nums.length) return Math.max(...nums)
}

// equivalent to lodash.debounce
export function debounce(func, timeout = 300) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => { func.apply(this, args); }, timeout);
  };
}

export const loadResults = (href) => {
  // Abort any already running requests
  if (currentLoad) {
    currentLoad.abort()
    clearTimeout(loadingTimeout)
  }

  loadingTimeout = setTimeout(() => {
    let $indicator = $('.loading-indicator').removeClass('hide');
    $indicator.find('.spinner').remove();

    // Create new spinner
    console.log("Setting spinner....")
    new Spinner(spinnerOptions).spin($indicator[0]);

    // Hide results
    $('.results-count').addClass('hide')

    loadingTimeout = setTimeout(() => {
      $('<a>')
        .addClass('force-load')
        .attr('href', href)
        .text('This is taking unusually long. Click here to load results manually.')
        .appendTo($indicator)
    }, 7000)

  }, 100);

  currentLoad = $.ajax({
    url: href,
    data: { 'partial': true }
  })

  currentLoad.then(function (html) {
    clearTimeout(loadingTimeout);
    currentLoad = null;
    loadingTimeout = null;
    $('main').html(html);
  })
    .fail(function (xhr, status) {
      if (status !== 'abort') {
        // fallback to normal page load
        location.href = href;
      }
    })
}

export const gotoResults = (href) => {
  if (location.search === href) {
    return;
  }
  if (history && history.pushState) {
    history.pushState(undefined, undefined, href);
  }
  loadResults(href);
}