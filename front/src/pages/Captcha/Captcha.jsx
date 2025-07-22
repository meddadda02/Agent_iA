"use client"

import { useState } from "react"
import Layout from "../../components/layout/Layout/Layout"
import Button from "../../components/ui/Button/Button"
import "./Captcha.css"

const Captcha = ({ onNext, onBack }) => {
  const [selectedImages, setSelectedImages] = useState([])
  const [isVerifying, setIsVerifying] = useState(false)

  const images = [
    { id: 1, src: "/images/traffic-light-1.jpg", isTrafficLight: true },
    { id: 2, src: "/images/car-1.jpg", isTrafficLight: false },
    { id: 3, src: "/images/traffic-light-2.jpg", isTrafficLight: true },
    { id: 4, src: "/images/building-1.jpg", isTrafficLight: false },
    { id: 5, src: "/images/traffic-light-3.jpg", isTrafficLight: true },
    { id: 6, src: "/images/tree-1.jpg", isTrafficLight: false },
    { id: 7, src: "/images/road-1.jpg", isTrafficLight: false },
    { id: 8, src: "/images/traffic-light-4.jpg", isTrafficLight: true },
    { id: 9, src: "/images/sky-1.jpg", isTrafficLight: false },
  ]

  const handleImageClick = (imageId) => {
    setSelectedImages((prev) => (prev.includes(imageId) ? prev.filter((id) => id !== imageId) : [...prev, imageId]))
  }

  const handleVerify = async () => {
    setIsVerifying(true)

    // Simulate verification process
    await new Promise((resolve) => setTimeout(resolve, 2000))

    const correctImages = images.filter((img) => img.isTrafficLight).map((img) => img.id)
    const isCorrect =
      selectedImages.length === correctImages.length && selectedImages.every((id) => correctImages.includes(id))

    setIsVerifying(false)

    if (isCorrect && onNext) {
      onNext()
    } else {
      alert("Please try again. Select all images with traffic lights.")
      setSelectedImages([])
    }
  }

  return (
    <Layout>
      <div className="captcha">
        <h1 className="captcha__title">Select all images with traffic lights</h1>

        <p className="captcha__description">
          Click on each image containing a traffic light. Click verify once there are none left.
        </p>

        <div className="captcha__grid">
          {images.map((image) => (
            <div
              key={image.id}
              className={`captcha__image ${selectedImages.includes(image.id) ? "captcha__image--selected" : ""}`}
              onClick={() => handleImageClick(image.id)}
            >
              <div className="captcha__image-placeholder">{image.id}</div>
              {selectedImages.includes(image.id) && <div className="captcha__checkmark">✓</div>}
            </div>
          ))}
        </div>

        <div className="captcha__actions">
          <Button variant="secondary" size="medium" onClick={onBack} className="captcha__back-btn">
            ← Back
          </Button>

          <Button
            variant="primary"
            size="medium"
            onClick={handleVerify}
            disabled={selectedImages.length === 0 || isVerifying}
            className="captcha__verify-btn"
          >
            {isVerifying ? "Verifying..." : "Verify"}
          </Button>
        </div>
      </div>
    </Layout>
  )
}

export default Captcha
