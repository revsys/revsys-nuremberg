import { useState } from 'react'

const resetForms = () => {
  console.log("Resetting...")
  document.getElementById("main-search-form").reset()
  document.getElementById("date-filter-form").reset()
}

const SearchBar = (props) => {
  const { query, url } = props

  return (
    <form
      className="results-search"
      id="main-search-form"
      role="search"
      aria-label="full-text search"
      action={url}
      method="GET"
    >
      <div className="search-bar-wrapper">
        <input type="search" name="q" title="Search query" defaultValue={query} required />
        <div className="button-wrapper">
          <button className="clear-search" type="reset" onClick={() => resetForms()}>Clear</button>
          <button className="button search-button" type="submit">Search</button>
        </div>
      </div>
    </form>
  )
}

export default SearchBar
