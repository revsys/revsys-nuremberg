/*
 * This is the entry point for the non-ReactJS bits of the search page
 */
import { min, max, gotoResults } from '@/vanilla/common';

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

  // Handle restricting to the values in the facets
  if (!fromYear.value || !toYear.value) {
    // Handle finding the facet years
    let facetYears = document.querySelectorAll(".facet p[data-year]")
    let years = []
    Array.from(facetYears).forEach((facetYear) => {
      years.push(facetYear.dataset.year)
    })
    let minYear = min(years)
    let maxYear = max(years)
    fromYear.value = minYear
    toYear.value = maxYear
  }

  // Handle out of bounds years
  if (fromYear.value < 1895 || fromYear.value > 1950 || toYear.value < 1895 || toYear.value > 1950) {
    let currentFrom = fromYear.value
    let currentTo = toYear.value
    fromYear.value = min([max([currentFrom, 1895]), 1950])
    toYear.value = min([max([currentTo, 1895]), 1950])
  }

  // FIXME handle updating query params when date range changes
  // FIXME handle slider

  // Handle submit of the form.  The sidebar green arrow button isn't a submit
  // button type for some reason.  Assuming it was intentional and keeping it.
  let goButton = document.getElementById("date-submit-button")

  goButton.addEventListener("click", (e) => {
    console.log(`Clicking! ${fromYear.value}  ${toYear.value}`)
    e.preventDefault()
    e.stopPropagation()
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
    console.log(href)
    //gotoResults(href);
    window.location.href = href
  })
}
/* **********************************************************************
   Main Entry Point
   ********************************************************************* */
const main = () => {

  // Handle sort by select box
  let resultSort = document.getElementById('results-sort');
  resultSort.addEventListener('change', (e) => {
    let sort = e.target.value;
    window.location.href = sort;
  });

  // Setup facet toggles
  toggleFacetCollapse()

  // Handle year range inputs
  yearRangeControls()

  // Handle show all facets
  toggleShowAllFacets()
}

document.addEventListener('DOMContentLoaded', main)