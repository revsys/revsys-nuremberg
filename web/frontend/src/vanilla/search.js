/*
 * This is the entry point for the non-ReactJS bits of the search page
 */
import { min, max, gotoResults, debounce } from '@/vanilla/common'

// Handle toggling the 'collapsed' class on facet nav elements
const toggleFacetCollapse = () => {
  let facets = document.getElementsByClassName("facet")
  Array.from(facets).forEach((facet) => {
    let toggle = facet.getElementsByClassName("collapse")[0]
    toggle.addEventListener("click", (e) => {
      facet.classList.toggle("collapsed")
    })
  })
}

// Handle toggling show all facets
const toggleShowAllFacets = () => {
  let facets = document.getElementsByClassName("facet")
  Array.from(facets).forEach((facet) => {
    let toggle = facet.getElementsByClassName("show-all")[0]
    if (toggle) {
      toggle.addEventListener("click", (e) => {
        console.log("Checked show all")
        e.preventDefault()
        facet.classList.toggle("show-all")
        let innerFacets = facet.getElementsByTagName("p")
        Array.from(innerFacets).forEach((innerFacet) => {
          innerFacet.classList.remove("hide")
        })
        toggle.classList.add('hide')
      })

    }
  })
}

// Handle year range inputs
const yearRangeControls = () => {
  // Get the inputs
  let dateForm = document.querySelector(".date-filter-form")
  let fromYear = document.querySelector("input[name='year_min']")
  let toYear = document.querySelector("input[name='year_max']")

  // We aren't on a search page
  if (!fromYear || !toYear) {
    return;
  }

  // Handle restricting to the values in the facets
  if (!fromYear.value || !toYear.value) {
    // Handle finding the facet years
    let facetYears = document.querySelectorAll(".facet p[data-year]")
    let years = []
    Array.from(facetYears).forEach((facetYear) => {
      if (facetYear.dataset.year) {
        if (facetYear.dataset.year == 0) {
          console.log("Skipping 0 year")
          return
        }
        years.push(facetYear.dataset.year)
      }
    })
    let minYear = min(years)
    let maxYear = max(years)
    fromYear.value = minYear
    toYear.value = maxYear
  }

  // Date Range Slider
  const setRange = debounce(() => {
    dateForm.submit()
  }, 700)

  $('.date-slider').slider({
    range: true,
    min: 1793,
    max: 1948,
    values: [$('input[name="year_min"]').val(), $('input[name="year_max"]').val()],
    slide: function (e, ui) {
      $('input[name="year_min"]').val(ui.values[0]);
      $('input[name="year_max"]').val(ui.values[1]);
      setRange();
    },
  })
  // Handle submit of the form.  The sidebar green arrow button isn't a submit
  // button type for some reason.  Assuming it was intentional and keeping it.
  let goButton = document.getElementById("date-submit-button")

  goButton.addEventListener("click", (e) => {
    e.preventDefault()
    e.stopPropagation()

    // Handle out of bounds years
    if (fromYear.value < 1895 || fromYear.value > 1950 || toYear.value < 1895 || toYear.value > 1950) {
      let currentFrom = fromYear.value
      let currentTo = toYear.value
      fromYear.value = min([max([currentFrom, 1895]), 1950])
      toYear.value = min([max([currentTo, 1895]), 1950])
    }

    if (fromYear.value > toYear.value) {
      let oldFromYear = fromYear.value
      let oldToYear = toYear.value
      fromYear.value = oldToYear
      toYear.value = oldFromYear
      console.log(`Flipping years`)
    }

    let href = window.location.href
    let range = 'f=date_year:' + fromYear.value + '-' + toYear.value;
    if (location.search && location.search.indexOf('date_year') > -1) {
      href = location.search.replace(/f=date_year:\d+-?\d+/, range)
    }
    else if (location.search.indexOf('?') > -1) {
      href = location.search + '&' + range;
    }
    else {
      href = '?' + range;
    }
    href = href.replace(/([\?&])page=\d+&?/, function (m, c) { return c });
    href = "/search/new-search" + href
    gotoResults(href);
  })
}

const scrollToTop = () => {
  const results = document.querySelector(".results-count")
  results.scrollIntoView();
}

const submitForm = (form) => {
  console.log("in submitForm JS")
  let action = form.attr('action')
  console.log(action)
  if (!action || action == location.pathname) {
    gotoResults('?' + form.serialize())
    return false
  }
  return true
}

const tabClicking = (e) => {
  return (e.ctrlKey || e.metaKey || (e.button && e.button == 1));
}

const handleSearchClear = () => {
  let clearButton = document.getElementById("search-bar-clear")
  let searchInput = document.getElementById("search-query")
  if (clearButton) {
    clearButton.addEventListener("click", (e) => {
      e.preventDefault()
      searchInput.value = ""
    })
  }
}

/* **********************************************************************
   Main Entry Point
   ********************************************************************* */
const main = () => {

  // Handle sort by select box
  let resultSort = document.getElementById('results-sort');

  if (resultSort) {
    resultSort.addEventListener('change', (e) => {
      let sort = e.target.value;
      window.location.href = sort;
    });
  }

  // Setup facet toggles
  toggleFacetCollapse()

  // Handle year range inputs
  yearRangeControls()

  // Handle show all facets
  toggleShowAllFacets()

  // Handle scrolling to top
  let scrollToTopButton = document.querySelector("a.page-number")

  if (scrollToTopButton) {
    scrollToTopButton.addEventListener("click", scrollToTop)
  }

  // Clear search form
  handleSearchClear()

  // Handle form submission
  /*
  $(document).on('submit', 'form', function (e) {
    if (tabClicking(e)) return;
    var $form = $(this);
    return submitForm($form);
  });*/
}

document.addEventListener('DOMContentLoaded', main)