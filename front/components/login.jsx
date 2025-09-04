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
        headers: { Accept: "application/json" },
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

      function parseJwt(token) {
        try {
          return JSON.parse(atob(token.split(".")[1]))
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
    <div className="min-h-screen w-full bg-gradient-to-br from-[#0f1123] via-[#1a1f3c] to-[#0f1123] text-white flex flex-col relative">
      {/* Header */}
      <header
        className={`fixed top-0 left-0 right-0 z-50 bg-[#0f1123]/70 backdrop-blur-md border-b border-white/10 px-6 lg:px-20 py-4 flex items-center justify-between transition-transform duration-300 ${
          showHeader ? "translate-y-0" : "-translate-y-full"
        }`}
      >
        <Link href="/">
          <Image
            src="/devaktus.png"
            alt="Devaktus Logo"
            width={200}
            height={40}
            priority
            className="object-contain cursor-pointer"
          />
        </Link>
      </header>

      <div className="h-[74px]" />

      <section className="flex-1 w-full px-6 lg:px-20 py-16 flex items-center justify-center">
        <div className="max-w-7xl w-full grid grid-cols-1 lg:grid-cols-2 gap-20 items-center">
          {/* Login Form */}
          <form
            onSubmit={handleSubmit}
            className="space-y-6 w-full max-w-md mx-auto lg:mx-0 bg-white/5 backdrop-blur-lg border border-white/10 p-10 rounded-2xl shadow-2xl"
          >
            <div className="flex justify-center mt-2">
              <div className="bg-gradient-to-r from-pink-500 to-red-500 p-4 rounded-full shadow-lg">
                <User className="h-10 w-10 text-white" strokeWidth={1.5} />
              </div>
            </div>

            <h2 className="text-3xl font-extrabold text-center mt-4 tracking-wide bg-gradient-to-r from-pink-400 to-red-400 bg-clip-text text-transparent">
              Login to Your Account
            </h2>

            <Button
              type="button"
              className="w-full rounded-xl bg-[#2a2f52] py-4 text-base font-semibold hover:bg-[#3b4a6b] flex items-center justify-center gap-3 transition"
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
              type="text"
              placeholder="Username *"
              value={formData.username}
              onChange={handleChange}
              required
              className="h-14 rounded-xl bg-[#2a2f52] placeholder-white/60 px-6 border border-white/10 text-white focus:ring-2 focus:ring-pink-500 transition"
            />

            <Input
              name="password"
              type="password"
              placeholder="Password *"
              value={formData.password}
              onChange={handleChange}
              required
              className="h-14 rounded-xl bg-[#2a2f52] placeholder-white/60 px-6 border border-white/10 text-white focus:ring-2 focus:ring-pink-500 transition"
            />

            {error && <p className="text-sm text-red-400 text-center font-medium">{error}</p>}

            <Button
              type="submit"
              disabled={loading}
              className="w-full rounded-xl bg-gradient-to-r from-pink-500 to-red-500 py-4 text-lg font-bold shadow-lg hover:scale-[1.02] hover:shadow-pink-500/30 transition-transform duration-300"
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
              width={550}
              height={480}
              priority
              className="object-contain drop-shadow-[0_0_90px_rgba(255,0,120,0.4)]"
            />
          </div>
        </div>
      </section>
    </div>
  )
}
