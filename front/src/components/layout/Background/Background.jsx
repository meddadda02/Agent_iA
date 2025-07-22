import "./Background.css"

const Background = ({ children }) => {
  return (
    <div className="background">
      <div className="background__effects">
        <div className="background__blur background__blur--1"></div>
        <div className="background__blur background__blur--2"></div>
        <div className="background__blur background__blur--3"></div>
      </div>

      <div className="background__grid"></div>

      <div className="background__particles">
        <div className="background__particle background__particle--1"></div>
        <div className="background__particle background__particle--2"></div>
        <div className="background__particle background__particle--3"></div>
      </div>

      <div className="background__content">{children}</div>
    </div>
  )
}

export default Background
