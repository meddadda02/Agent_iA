"use client"
import Button from "../../ui/Button"
import { Sparkles } from "../../icons/Icons"
import "./CallToAction.css"

const CallToAction = () => {
  const handleCreateAccount = () => {
    console.log("Create account clicked")
    // Logique pour créer un compte
  }

  const handleSignIn = () => {
    console.log("Sign in clicked")
    // Logique pour se connecter
  }

  return (
    <section className="cta">
      <div className="cta__container">
        <Button variant="primary" size="large" className="cta__button" onClick={handleCreateAccount}>
          <Sparkles className="cta__icon" size={20} />
          Create An Account
          <Sparkles className="cta__icon" size={20} />
        </Button>

        <button className="cta__link" onClick={handleSignIn}>
          Already have an account? Sign in
        </button>
      </div>
    </section>
  )
}

export default CallToAction
