document.addEventListener('DOMContentLoaded', () => {
  const chat = document.getElementById('chat')
  const msgInput = document.getElementById('message')
  const sendBtn = document.getElementById('send')
  const statusDiv = document.getElementById('status')

  let hasMessages = false

  function clearEmptyState() {
    if (!hasMessages) {
      chat.innerHTML = ''
      hasMessages = true
    }
  }

  function append(role, text, isError = false) {
    clearEmptyState()

    const msgDiv = document.createElement('div')
    msgDiv.className = 'msg ' + (role === 'user' ? 'user' : 'bot')

    const avatar = document.createElement('div')
    avatar.className = 'msg-avatar'
    avatar.textContent = role === 'user' ? '👤' : '🤖'

    const content = document.createElement('div')
    content.className = 'msg-content' + (isError ? ' error' : '')
    content.textContent = text

    msgDiv.appendChild(avatar)
    msgDiv.appendChild(content)
    chat.appendChild(msgDiv)
    chat.scrollTop = chat.scrollHeight
  }

  async function loadStatus() {
    try {
      const r = await fetch('/status')
      const j = await r.json()
      const mode = j.mode === 'sdk' ? '🟢 Conectado' :
                   j.mode === 'rest' ? '🟡 REST API' : '🔴 Modo local'
      statusDiv.textContent = mode
    } catch (err) {
      statusDiv.textContent = '🔴 Error'
    }
  }

  loadStatus()

  // Auto-resize textarea
  msgInput.addEventListener('input', () => {
    msgInput.style.height = 'auto'
    msgInput.style.height = Math.min(msgInput.scrollHeight, 150) + 'px'
  })

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

    // Disable controls
    sendBtn.disabled = true
    msgInput.disabled = true

    append('user', text)
    msgInput.value = ''
    msgInput.style.height = 'auto'

    // Show typing indicator
    const typingDiv = document.createElement('div')
    typingDiv.className = 'msg bot typing-indicator'
    typingDiv.innerHTML = `
      <div class="msg-avatar">🤖</div>
      <div class="msg-content">Escribiendo...</div>
    `
    chat.appendChild(typingDiv)
    chat.scrollTop = chat.scrollHeight

    try {
      const res = await fetch('/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text })
      })

      // Remove typing indicator
      typingDiv.remove()

      const j = await res.json()
      if (res.ok) {
        append('bot', j.reply)
      } else {
        const errMsg = j.detail || j.error || 'Error desconocido'
        append('bot', '❌ ' + errMsg, true)

        // Show fallback if available
        if (j.fallback_reply) {
          setTimeout(() => {
            append('bot', '💡 Respuesta local: ' + j.fallback_reply)
          }, 500)
        }
      }
    } catch (err) {
      typingDiv.remove()
      append('bot', '❌ Error de conexión: ' + err.message, true)
    } finally {
      // Re-enable controls
      sendBtn.disabled = false
      msgInput.disabled = false
      msgInput.focus()
    }
  }

  // Focus on input
  msgInput.focus()
})
