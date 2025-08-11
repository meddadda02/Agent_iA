"use client"

import { useState } from "react"
import SecurityCheck from "./pages/SecurityCheck/SecurityCheck"
import Captcha from "./pages/Captcha/Captcha"
import ChatInterface from "./pages/ChatInterface/ChatInterface"
import "./App.css"

function App() {
  const [currentStep, setCurrentStep] = useState("security") // security, captcha, chat

  const handleSecurityNext = () => {
    setCurrentStep("captcha")
  }

  const handleCaptchaNext = () => {
    setCurrentStep("chat")
  }

  const handleCaptchaBack = () => {
    setCurrentStep("security")
  }

  const handleChatBack = () => {
    setCurrentStep("captcha")
  }

  const renderCurrentStep = () => {
    switch (currentStep) {
      case "security":
        return <SecurityCheck onNext={handleSecurityNext} />
      case "captcha":
        return <Captcha onNext={handleCaptchaNext} onBack={handleCaptchaBack} />
      case "chat":
        return <ChatInterface onBack={handleChatBack} />
      default:
        return <SecurityCheck onNext={handleSecurityNext} />
    }
  }

  return <div className="App">{renderCurrentStep()}</div>
}

export default App
