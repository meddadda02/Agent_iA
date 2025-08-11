"use client"

import React, { useEffect, useState, useRef } from "react"
import Image from "next/image"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { Button } from "./ui/button"
import { Input } from "./ui/input"
import { User } from "lucide-react"

export default function Signup() {
  const [showHeader, setShowHeader] = useState(true)
  const lastScrollY = useRef(0)
  const router = useRouter()

  const [formData, setFormData] = useState({
    username: "",
    email: "",
    password: "",
    confirmPassword: "",
  })
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    function handleScroll() {
      const currentScrollY = window.scrollY
      if (currentScrollY < 50) {
        setShowHeader(true)
      } else if (currentScrollY > lastScrollY.current) {
        setShowHeader(false)
      } else {
        setShowHeader(true)
      }
      lastScrollY.current = currentScrollY
    }

    window.addEventListener("scroll", handleScroll)
    return () => window.removeEventListener("scroll", handleScroll)
  }, [])

  function handleChange(e) {
    const { name, value } = e.target
    setFormData(prev => ({ ...prev, [name]: value }))
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setError("")

    if (formData.password !== formData.confirmPassword) {
      setError("Passwords do not match")
      return
    }

    try {
      setLoading(true)

      const payload = new FormData()
      payload.append("username", formData.username)
      payload.append("email", formData.email)
      payload.append("password", formData.password)
      payload.append("confirm_password", formData.confirmPassword)

      // Image par défaut
      const resDefault = await fetch("/default-avatar.png")
      const blob = await resDefault.blob()
      const defaultFile = new File([blob], "default-avatar.png", { type: blob.type })
      payload.append("photo", defaultFile)

      const res = await fetch("http://localhost:8000/api/users/signup", {
        method: "POST",
        body: payload,
      })

      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || "Signup failed")
      }

      await res.json()
      router.push("/login")
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen w-full bg-[#0f1123] text-white flex flex-col relative">
      {/* Header */}
      <header
        className={`fixed top-0 left-0 right-0 z-50 bg-[#0f1123] shadow-sm px-6 lg:px-20 py-5 flex items-center transition-transform duration-300 ${
          showHeader ? "translate-y-0" : "-translate-y-full"
        }`}
      >
        <Link href="/">
          <Image
            src="/devaktus.png"
            alt="Devaktus Logo"
            width={230}
            height={44}
            priority
            className="object-contain cursor-pointer"
          />
        </Link>
      </header>

      <div className="h-[74px]" />

      <section className="flex-1 w-full px-6 lg:px-20 py-24 flex items-center justify-center">
        <div className="max-w-7xl w-full grid grid-cols-1 lg:grid-cols-2 gap-24 items-center">
          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-8 w-full max-w-md mx-auto lg:mx-0 text-white">
            <div className="flex justify-center mt-6">
              <User className="h-16 w-16" strokeWidth={1} />
            </div>
            <h2 className="text-3xl font-extrabold text-center mt-4 mb-8 tracking-wide">Create Your Account</h2>

            <Input
              name="username"
              type="text"
              placeholder="Username *"
              value={formData.username}
              onChange={handleChange}
              required
              className="h-14 rounded-full bg-[#3b4a6b] placeholder-white/50 px-6 border-none text-white"
            />

            <Input
              name="email"
              type="email"
              placeholder="Email *"
              value={formData.email}
              onChange={handleChange}
              required
              className="h-14 rounded-full bg-[#3b4a6b] placeholder-white/50 px-6 border-none text-white"
            />

            <Input
              name="password"
              type="password"
              placeholder="Password *"
              value={formData.password}
              onChange={handleChange}
              required
              className="h-14 rounded-full bg-[#3b4a6b] placeholder-white/50 px-6 border-none text-white"
            />

            <Input
              name="confirmPassword"
              type="password"
              placeholder="Confirm Password *"
              value={formData.confirmPassword}
              onChange={handleChange}
              required
              className="h-14 rounded-full bg-[#3b4a6b] placeholder-white/50 px-6 border-none text-white"
            />

            {error && (
              <p className="text-red-500 text-sm text-center font-semibold">{error}</p>
            )}

            <Button
              type="submit"
              disabled={loading}
              className="w-full rounded-full bg-gradient-to-r from-pink-500 to-red-500 py-5 text-base font-extrabold shadow-lg hover:brightness-110 transition"
            >
              {loading ? "Creating..." : "Create Account"}
            </Button>
          </form>

          {/* Illustration */}
          <div className="hidden lg:flex justify-center">
            <Image
              src="/robot-illustration.png"
              alt="AI Assistant Robot"
              width={600}
              height={520}
              priority
              className="object-contain drop-shadow-[0_0_70px_rgba(255,0,120,0.4)]"
            />
          </div>
        </div>
      </section>
    </div>
  )
}
