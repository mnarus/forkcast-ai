import { useEffect, useState } from 'react'
import './App.css'

function App() {
  const [message, setMessage] = useState('Loading...')
  const [error, setError] = useState('')

  useEffect(() => {
    let ignore = false

    async function loadGreeting() {
      try {
        const response = await fetch('/api/hello/')

        if (!response.ok) {
          throw new Error(`Request failed with status ${response.status}`)
        }

        const data: { message?: string } = await response.json()

        if (!ignore) {
          setMessage(data.message ?? 'No message received')
          setError('')
        }
      } catch (fetchError) {
        if (!ignore) {
          setMessage('')
          setError(
            fetchError instanceof Error
              ? fetchError.message
              : 'Unable to load message',
          )
        }
      }
    }

    void loadGreeting()

    return () => {
      ignore = true
    }
  }, [])

  return (
    <main className="app-shell">
      <section className="message-card">
        <p className="eyebrow">Forkcast AI</p>
        <h1>Django says:</h1>
        <p className="message">{error || message}</p>
      </section>
    </main>
  )
}

export default App
