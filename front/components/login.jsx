"use client"

import React, { useEffect, useState, useRef } from "react"
import Image from "next/image"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { Button } from "./ui/button"
import { Input } from "./ui/input"
import { User } from "lucide-react"

export default function Login() {
  const [showHeader, setShowHeader] = useState(true)
  const lastScrollY = useRef(0)
  const router = useRouter()

  const [formData, setFormData] = useState({
    username: "",
    password: "",
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
    setLoading(true)
    setError("")

    try {
      const res = await fetch("http://localhost:8000/api/users/login", {
        method: "POST",
        headers: {
          Accept: "application/json",
        },
        body: new URLSearchParams({
          username: formData.username,
          password: formData.password,
        }),
      })

      if (!res.ok) {
        const errorData = await res.json()
        throw new Error(errorData.detail || "Login failed")
      }

      const data = await res.json()
      console.log("Token reçu:", data.access_token)

      localStorage.setItem("token", data.access_token)

      // Décode la payload du JWT (sans validation, juste pour lire le rôle)
      function parseJwt(token) {
        try {
          return JSON.parse(atob(token.split('.')[1]))
        } catch (e) {
          return null
        }
      }

      const payload = parseJwt(data.access_token)
      console.log("Payload token:", payload)

      if (payload && payload.role === "admin") {
        router.push("/admin")
      } else {
        router.push("/chat")
      }

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

          {/* Login Form */}
          <form onSubmit={handleSubmit} className="space-y-8 w-full max-w-md mx-auto lg:mx-0 text-white">
            <div className="flex justify-center mt-6">
              <User className="h-16 w-16" strokeWidth={1} />
            </div>

            <h2 className="text-3xl font-extrabold text-center mt-4 mb-8 tracking-wide">
              Login to Your Account
            </h2>

            <Button
              type="button"
              className="w-full rounded-full bg-[#3b4a6b] py-5 text-base font-semibold hover:bg-[#4a5b7c] flex items-center justify-center gap-2"
              onClick={() => alert("Google sign-in flow here")}
            >
              <Image src="/images/google-logo.png" alt="Google" width={24} height={24} />
              Sign in with Google
            </Button>

            <div className="flex items-center gap-4">
              <div className="flex-grow h-px bg-white/20" />
              <span className="text-sm text-white/60">OR</span>
              <div className="flex-grow h-px bg-white/20" />
            </div>

            <Input
              name="username"
              type="username"
              placeholder="Username *"
              value={formData.username}
              onChange={handleChange}
              required
              className="h-14 rounded-full bg-[#3b4a6b] placeholder-white/50 px-6 border-none focus:ring-4 focus:ring-pink-500 text-white transition"
            />

            <Input
              name="password"
              type="password"
              placeholder="Password *"
              value={formData.password}
              onChange={handleChange}
              required
              className="h-14 rounded-full bg-[#3b4a6b] placeholder-white/50 px-6 border-none focus:ring-4 focus:ring-pink-500 text-white transition"
            />

            {error && <p className="text-sm text-red-500 text-center font-semibold">{error}</p>}

            <Button
              type="submit"
              disabled={loading}
              className="w-full rounded-full bg-gradient-to-r from-pink-500 to-red-500 py-5 text-base font-extrabold shadow-lg hover:brightness-110 transition"
            >
              {loading ? "Connexion..." : "Login"}
            </Button>

            <p className="text-sm text-white/60 text-center">
              Forgot password?{" "}
              <Link href="/forgot-password" className="text-pink-400 hover:underline">
                Reset here
              </Link>
            </p>
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
