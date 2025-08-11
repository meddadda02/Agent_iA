"use client"

import { useState, useRef, useEffect } from "react"
import Layout from "../../components/layout/Layout/Layout"
import Button from "../../components/ui/Button/Button"
import "./ChatInterface.css"

const ChatInterface = ({ onBack }) => {
  const [messages, setMessages] = useState([
    {
      id: 1,
      type: "bot",
      content: "Hello! I'm your AI assistant. How can I help you today?",
      timestamp: new Date(),
    },
  ])
  const [inputValue, setInputValue] = useState("")
  const [isTyping, setIsTyping] = useState(false)
  const messagesEndRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSendMessage = async () => {
    if (!inputValue.trim()) return

    const userMessage = {
      id: Date.now(),
      type: "user",
      content: inputValue,
      timestamp: new Date(),
    }

    setMessages((prev) => [...prev, userMessage])
    setInputValue("")
    setIsTyping(true)

    // Simulate bot response
    setTimeout(() => {
      const botMessage = {
        id: Date.now() + 1,
        type: "bot",
        content: "Thank you for your message! I'm processing your request and will get back to you shortly.",
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, botMessage])
      setIsTyping(false)
    }, 2000)
  }

  const handleKeyPress = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  return (
    <Layout className="chat-layout">
      <div className="chat-interface">
        <div className="chat-interface__header">
          <Button variant="secondary" size="small" onClick={onBack} className="chat-interface__back-btn">
            ← Back
          </Button>
          <h1 className="chat-interface__title">AI Assistant</h1>
          <div className="chat-interface__status">
            <span className="chat-interface__status-dot"></span>
            Online
          </div>
        </div>

        <div className="chat-interface__messages">
          {messages.map((message) => (
            <div key={message.id} className={`chat-message chat-message--${message.type}`}>
              <div className="chat-message__content">{message.content}</div>
              <div className="chat-message__timestamp">
                {message.timestamp.toLocaleTimeString([], {
                  hour: "2-digit",
                  minute: "2-digit",
                })}
              </div>
            </div>
          ))}

          {isTyping && (
            <div className="chat-message chat-message--bot">
              <div className="chat-message__content">
                <div className="typing-indicator">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        <div className="chat-interface__input">
          <textarea
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Type your message here..."
            className="chat-interface__textarea"
            rows="2"
          />
          <Button
            variant="primary"
            size="medium"
            onClick={handleSendMessage}
            disabled={!inputValue.trim()}
            className="chat-interface__send-btn"
          >
            Send
          </Button>
        </div>
      </div>
    </Layout>
  )
}

export default ChatInterface
