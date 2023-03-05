import { useState } from 'react'

const resetForms = (setParams) => {
  console.log("Resetting...")
  document.getElementById("main-search-form").reset()
  document.getElementById("date-filter-form").reset()
  setParams({ 'q': '' })
  window.location.reload(false)
}

const SearchBar = (props) => {
  const { query, url, setParams } = props

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
        <input type="search" name="q" title="Search query" defaultValue={query} />
        <div className="button-wrapper">
          <button className="clear-search" type="reset" onClick={() => resetForms(setParams)}>Clear</button>
          <button className="button search-button" type="submit">Search</button>
        </div>
      </div>
    </form>
  )
}

export default SearchBar
