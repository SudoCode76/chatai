document.addEventListener('DOMContentLoaded', () => {
  const chat = document.getElementById('chat')
  const msgInput = document.getElementById('message')
  const sendBtn = document.getElementById('send')
  const statusDiv = document.getElementById('status')

  function append(role, text) {
    const d = document.createElement('div')
    d.className = 'msg ' + (role === 'user' ? 'user' : 'bot')
    d.textContent = text
    chat.appendChild(d)
    chat.scrollTop = chat.scrollHeight
  }

  async function loadStatus() {
    try {
      const r = await fetch('/status')
      const j = await r.json()
      statusDiv.textContent = `Estado: mode=${j.mode} | sdk_installed=${j.sdk_installed} | has_key=${j.has_key} | model=${j.gemini_model}`
    } catch (err) {
      statusDiv.textContent = 'Estado: error al obtener estado (' + err.message + ')'
    }
  }

  loadStatus()

  sendBtn.addEventListener('click', send)
  msgInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      send()
    }
  })

  async function send() {
    const text = msgInput.value.trim()
    if (!text) return
    append('user', text)
    msgInput.value = ''

    try {
      const res = await fetch('/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text })
      })
      const j = await res.json()
      if (res.ok) {
        append('bot', j.reply)
      } else {
        // mostrar detalle si está presente
        const errMsg = j.detail || j.error || 'Unknown error'
        append('bot', 'Error: ' + errMsg)
      }
    } catch (err) {
      append('bot', 'Network error: ' + err.message)
    }
  }
})
