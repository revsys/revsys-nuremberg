import React from 'react'
import ReactDOM from 'react-dom/client'
import Search from './views/Search'
import './index.css'
import { BrowserRouter } from "react-router-dom"

ReactDOM.createRoot(document.getElementById('search')).render(
  <React.StrictMode>
    <BrowserRouter>
      <Search />
    </BrowserRouter>
  </React.StrictMode>,
)
