import { useState } from 'react'

const SearchBar = (props) => {
  const { query, url } = props

  return (
    <form className="results-search" role="search" aria-label="full-text search" action={url} method='GET'>
      <div className="search-bar-wrapper">
        <input type="search" name="q" title="Search query" value={query} required />
        <div className="button-wrapper">
          <button className="clear-search" type="reset">Clear</button>
          <button className="button search-button" type="submit">Search</button>
        </div>
      </div>
    </form>
  )
}

export default SearchBar
