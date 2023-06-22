// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import { UserContextProvider } from './components/context'
import './index.css'

ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
    <UserContextProvider>
        <App/>
    </UserContextProvider>)
