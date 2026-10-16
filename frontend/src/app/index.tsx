import { RouterProvider } from 'react-router'

import { Providers } from './providers'
import { router } from './router'
import './styles/index.css'

export function App() {
  return (
    <Providers>
      <RouterProvider router={router} />
    </Providers>
  )
}
