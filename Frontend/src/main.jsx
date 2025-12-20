import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

import React from "react";
import ReactDOM from "react-dom/client";
import AppWithBackground from "./App";
import "./index.css"; // ← make sure this is imported


createRoot(document.getElementById('root')).render(
  <StrictMode>
    <AppWithBackground />
  </StrictMode>,
)
