import "./Logo.css"

const Logo = ({ className = "", size = "medium" }) => {
  return (
    <div className={`logo logo--${size} ${className}`}>
      <span className="logo__dev">Dev</span>
      <span className="logo__aktus">aktus</span>
    </div>
  )
}

export default Logo
