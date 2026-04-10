import { useState } from 'react'
import { MainWorkspace } from './components/MainWorkspace'
import { SplashScreen } from './components/SplashScreen'

export default function App() {
  const [entered, setEntered] = useState(false)

  if (!entered) {
    return <SplashScreen onEnter={() => setEntered(true)} />
  }

  return <MainWorkspace onBackToSplash={() => setEntered(false)} />
}
