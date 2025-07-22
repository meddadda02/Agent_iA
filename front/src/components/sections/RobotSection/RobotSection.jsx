import "./RobotSection.css"

const RobotSection = () => {
  return (
    <section className="robot-section">
      <div className="robot-section__glow"></div>

      <img
        src="/images/robot-illustration.png"
        alt="ContentGuard AI Assistant Robot"
        className="robot-section__image"
      />

      {/* Particules colorées */}
      <div className="robot-section__particle robot-section__particle--green"></div>
      <div className="robot-section__particle robot-section__particle--blue"></div>
      <div className="robot-section__particle robot-section__particle--pink"></div>
    </section>
  )
}

export default RobotSection
