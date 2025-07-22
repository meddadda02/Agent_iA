import "./Layout.css"

const Layout = ({ children, className = "" }) => {
  return (
    <div className={`layout ${className}`}>
      <div className="layout__container">{children}</div>
    </div>
  )
}

export default Layout
