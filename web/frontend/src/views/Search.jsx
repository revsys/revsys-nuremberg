import { useState } from 'react'
import { useSearchParams } from "react-router-dom"

import SearchBar from './SearchBar'

const Search = (props) => {
  // const params = new URLSearchParams(window.location.search)
  const [params, setParams] = useSearchParams()

  return (
    <section role="search" aria-label="Search the archive" className="theme-beige thin">
      <h1 className="h4">Search the archive</h1>
      <div className="full-width">
        <SearchBar query={params.get('q')} />
        <div className="show-advanced-search"><a>Advanced Search</a></div>
        {/* <p>{% include 'search/advanced-search-form.html' with form=advanced_search_form %}</p> */}
      </div>
    </section >
  )
}

export default Search
