import { Card, CardContent } from "../../ui/Card"
import { Sparkles, Shield, Zap } from "../../icons/Icons"
import "./Hero.css"

const Hero = () => {
  return (
    <section className="hero">
      <Card variant="glass" className="hero__card">
        <CardContent>
          <div className="hero__icons">
            <Sparkles className="hero__icon hero__icon--sparkles" size={28} />
            <Shield className="hero__icon hero__icon--shield" size={28} />
            <Zap className="hero__icon hero__icon--zap" size={28} />
          </div>

          <h1 className="hero__title">
            Meet <span className="hero__title--highlight">ContentGuard</span> !
          </h1>

          <p className="hero__description">
            <span className="hero__text--blue">Instantly analyze</span> your content with{" "}
            <span className="hero__text--purple">AI</span>.
            <br />
            Ask ContentGuardian anything
            <br />
            <span className="hero__text--pink">before you publish!</span>
          </p>
        </CardContent>
      </Card>
    </section>
  )
}

export default Hero
