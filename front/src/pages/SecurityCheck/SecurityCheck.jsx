"use client"

import { useState } from "react"
import Layout from "../../components/layout/Layout/Layout"
import Button from "../../components/ui/Button/Button"
import Select from "../../components/ui/Select/Select"
import "./SecurityCheck.css"

const SecurityCheck = ({ onNext }) => {
  const [selectedLanguage, setSelectedLanguage] = useState("english")

  const languageOptions = [
    { value: "english", label: "English" },
    { value: "french", label: "Français" },
    { value: "spanish", label: "Español" },
    { value: "german", label: "Deutsch" },
  ]

  const handleBegin = () => {
    if (onNext) {
      onNext()
    }
  }

  const handleLanguageChange = (e) => {
    setSelectedLanguage(e.target.value)
  }

  return (
    <Layout>
      <div className="security-check">
        <h1 className="security-check__title">Let's confirm you are human</h1>

        <p className="security-check__description">
          Complete the security check before continuing. This step verifies that you are not a bot, which helps to
          protect your account and prevent spam.
        </p>

        <div className="security-check__actions">
          <Button variant="primary" size="medium" onClick={handleBegin} className="security-check__begin-btn">
            Begin →
          </Button>
        </div>

        <div className="security-check__language">
          <Select options={languageOptions} value={selectedLanguage} onChange={handleLanguageChange} />
        </div>
      </div>
    </Layout>
  )
}

export default SecurityCheck
