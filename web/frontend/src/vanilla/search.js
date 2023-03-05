/*
 * This is the entry point for the non-ReactJS bits of the search page
 */

const main = () => {
  let resultSort = document.getElementById('results-sort');
  resultSort.addEventListener('change', (e) => {
    let sort = e.target.value;
    window.location.href = sort;
  });
}

document.addEventListener('DOMContentLoaded', main)