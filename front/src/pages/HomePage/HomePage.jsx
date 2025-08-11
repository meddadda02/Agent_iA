import Background from "../../components/layout/Background"
import Logo from "../../components/common/Logo"
import Hero from "../../components/sections/Hero"
import RobotSection from "../../components/sections/RobotSection"
import CallToAction from "../../components/sections/CallToAction"
import "./HomePage.css"

const HomePage = () => {
  return (
    <Background>
      <div className="homepage">
        <header className="homepage__header">
          <Logo size="medium" />
        </header>

        <main className="homepage__main">
          <Hero />
          <RobotSection />
        </main>

        <footer className="homepage__footer">
          <CallToAction />
        </footer>
      </div>
    </Background>
  )
}

export default HomePage
