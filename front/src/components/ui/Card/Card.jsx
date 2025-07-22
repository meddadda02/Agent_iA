import "./Card.css"

const Card = ({ children, className = "", variant = "default" }) => {
  return <div className={`card card--${variant} ${className}`}>{children}</div>
}

const CardHeader = ({ children, className = "" }) => {
  return <div className={`card__header ${className}`}>{children}</div>
}

const CardContent = ({ children, className = "" }) => {
  return <div className={`card__content ${className}`}>{children}</div>
}

const CardFooter = ({ children, className = "" }) => {
  return <div className={`card__footer ${className}`}>{children}</div>
}

export { Card, CardHeader, CardContent, CardFooter }
