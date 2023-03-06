
let controller;
let loadingTimeout = null;

export const min = (nums) => {
  if (nums.length) return Math.min(...nums)
}

export const max = (nums) => {
  if (nums.length) return Math.max(...nums)
}

export const loadResults = (href) => {
  // Abort any already running requests
  if (controller) {
    controller.abort();
    // FIXME clear timeout here
  }

  // Load the actual results using fetch()
  controller = new AbortController();

  fetch({
    resource: href,
    data: {
      'partial': true
    },
    signal: controller.signal
  }).then((response) => {
    return response.text()
  }).then((response) => {
    controller = null
    loadingTimeout = null
    let main = document.getElementsByTagName('main')[0]
    main.innerHTML = response
  }).catch((error) => {
    console.error(`Retrieve failed: ${error.message}`)
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