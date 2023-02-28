import { useState } from 'react'

import SearchBar from './SearchBar'

const Search = (props) => {
  const [count, setCount] = useState(0)

  return (
    <section role="search" aria-label="Search the archive" className="theme-beige thin">
      <h1 className="h4">Search the archive</h1>
      <div className="full-width">
        <SearchBar />
        <div className="show-advanced-search"><a>Advanced Search</a></div>
        {/* <p>{% include 'search/advanced-search-form.html' with form=advanced_search_form %}</p> */}
      </div>
    </section >
  )
}

export default Search
