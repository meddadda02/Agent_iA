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
      msgType: "text",
      timestamp: new Date(),
    },
  ])
  const [inputValue, setInputValue] = useState("")
  const [file, setFile] = useState(null) // image or video
  const [isTyping, setIsTyping] = useState(false)
  const messagesEndRef = useRef(null)
  const fileInputRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSendMessage = async () => {
    if (!inputValue.trim() && !file) return

    const userMessage = {
      id: Date.now(),
      type: "user",
      msgType: file ? (file.type.startsWith("video") ? "video" : "image") : "text",
      content: file || inputValue,
      timestamp: new Date(),
    }

    setMessages((prev) => [...prev, userMessage])
    setInputValue("")
    setFile(null)
    setIsTyping(true)

    // Simulated bot response
    setTimeout(() => {
      const botMessage = {
        id: Date.now() + 1,
        type: "bot",
        msgType: "text",
        content: "Thanks! I've received your message and will process it.",
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

  const handleFileSelect = (e) => {
    const selected = e.target.files[0]
    if (selected) {
      setFile(selected)
    }
  }

  return (
    <Layout className="chat-layout">
      <div className="chat-interface">
        {/* Header */}
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

        {/* Messages */}
        <div className="chat-interface__messages">
          {messages.map((message) => (
            <div key={message.id} className={`chat-message chat-message--${message.type}`}>
              <div className="chat-message__content">
                {message.msgType === "text" && <p>{message.content}</p>}
                {message.msgType === "image" && (
                  <img
                    src={URL.createObjectURL(message.content)}
                    alt="sent"
                    className="chat-message__media"
                  />
                )}
                {message.msgType === "video" && (
                  <video
                    src={URL.createObjectURL(message.content)}
                    controls
                    className="chat-message__media"
                  />
                )}
              </div>
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

        {/* Input Section */}
        <div className="chat-interface__input">
          <textarea
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Type your message here..."
            className="chat-interface__textarea"
            rows="2"
          />

          <input
            ref={fileInputRef}
            type="file"
            accept="image/*,video/*"
            hidden
            onChange={handleFileSelect}
          />

          <Button
            variant="secondary"
            size="medium"
            onClick={() => fileInputRef.current.click()}
            className="chat-interface__send-btn"
          >
            📎
          </Button>

          <Button
            variant="primary"
            size="medium"
            onClick={handleSendMessage}
            disabled={!inputValue.trim() && !file}
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
