import React, { useEffect, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import './ChatbotLauncher.css'

const HIDDEN_PREFIXES = ['/advisor', '/login', '/register', '/reset-password', '/session-recovery', '/admin']

/**
 * Floating entry point to the Messenger RAG chat. It links to the existing
 * /advisor/chat route; it never mounts a second chat implementation.
 */
export default function ChatbotLauncher() {
  const { pathname } = useLocation()
  const [open, setOpen] = useState(false)

  useEffect(() => { setOpen(false) }, [pathname])

  if (HIDDEN_PREFIXES.some((prefix) => pathname === prefix || pathname.startsWith(prefix + '/'))) return null

  return (
    <div className="chat-launcher" data-chatbot-launcher>
      {open ? (
        <div className="chat-launcher-menu" role="dialog" aria-label="Trợ lý AI SmartProp">
          <p className="chat-launcher-title">Trợ lý AI SmartProp</p>
          <Link className="chat-launcher-option" to="/advisor/chat">Trò chuyện tư vấn (RAG) →</Link>
          <Link className="chat-launcher-option" to="/advisor/analysis">Tư vấn đa bằng chứng →</Link>
          <Link className="chat-launcher-option" to="/market-analytics">Phân tích thị trường →</Link>
        </div>
      ) : null}
      <button
        type="button"
        className="chat-launcher-button"
        aria-expanded={open}
        aria-label={open ? 'Đóng trợ lý AI' : 'Mở trợ lý AI'}
        onClick={() => setOpen((value) => !value)}
      >
        <span aria-hidden="true">{open ? '×' : '💬'}</span>
        <span className="chat-launcher-label">Trợ lý AI</span>
      </button>
    </div>
  )
}
