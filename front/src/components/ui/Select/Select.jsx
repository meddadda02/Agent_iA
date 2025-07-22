"use client"
import "./Select.css"

const Select = ({ options = [], value, onChange, placeholder = "Select an option", className = "", ...props }) => {
  return (
    <div className={`select-wrapper ${className}`}>
      <select className="select" value={value} onChange={onChange} {...props}>
        {placeholder && (
          <option value="" disabled>
            {placeholder}
          </option>
        )}
        {options.map((option, index) => (
          <option key={index} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </div>
  )
}

export default Select
