import { useState } from 'react'
import { useSearchParams } from "react-router-dom"
import SearchBar from './SearchBar'

const Search = (props) => {
  const [params, setParams] = useSearchParams()

  return (
    <section role="search" aria-label="Search the archive" className="theme-beige thin">
      <h1 className="h4">Search the archive</h1>
      <div className="full-width">
        <SearchBar
          query={params.get('q')}
          setParams={setParams}
        />
        <div className="show-advanced-search"><a>Advanced Search</a></div>
        <p></p>
      </div>
    </section >
  )
}

export default Search
