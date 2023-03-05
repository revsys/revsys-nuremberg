/*
 * This is the entry point for the non-ReactJS bits of the search page
 */

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

const main = () => {

  // Handle sort by select box
  let resultSort = document.getElementById('results-sort');
  resultSort.addEventListener('change', (e) => {
    let sort = e.target.value;
    window.location.href = sort;
  });

  // Setup facet toggles
  toggleFacetCollapse()
}

document.addEventListener('DOMContentLoaded', main)