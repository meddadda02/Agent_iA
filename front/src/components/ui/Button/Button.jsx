"use client"
import "./Button.css"

const Button = ({
  children,
  variant = "primary",
  size = "medium",
  onClick,
  disabled = false,
  className = "",
  ...props
}) => {
  const buttonClass = `btn btn--${variant} btn--${size} ${className} ${disabled ? "btn--disabled" : ""}`

  return (
    <button className={buttonClass} onClick={onClick} disabled={disabled} {...props}>
      {children}
    </button>
  )
}

export default Button
