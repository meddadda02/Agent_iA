"use client"

import Image from "next/image"
import { useRouter } from "next/navigation"
import { Button } from "./ui/button"
import { Sparkles } from "./icons"

export default function Home() {
  const router = useRouter()

  return (
    <div className="min-h-screen w-full bg-gradient-to-br from-[#0f1123] via-[#14162e] to-[#1b1e3f] text-white flex flex-col">
      {/* Header */}
      <header className="sticky top-0 z-50 w-full backdrop-blur-md bg-[#0f1123]/80 border-b border-white/10 shadow-lg px-6 lg:px-20 py-5 flex items-center">
        <Image
          src="/devaktus.png"
          alt="Devaktus Logo"
          width={230}
          height={44}
          priority
          className="object-contain hover:scale-105 transition-transform duration-300"
        />
      </header>

      {/* Hero */}
      <section className="flex-1 w-full px-6 lg:px-20 py-24 flex items-center justify-center">
        <div className="max-w-7xl w-full grid grid-cols-1 lg:grid-cols-2 gap-24 items-center">
          {/* Text */}
          <div className="space-y-10 text-center lg:text-left">
            <h1 className="text-5xl md:text-6xl font-extrabold tracking-tight leading-tight drop-shadow-lg">
              Meet{" "}
              <span className="bg-gradient-to-r from-pink-500 to-red-500 bg-clip-text text-transparent animate-gradient">
                ContentGuard 
              </span>
              <span className="text-pink-400"> !</span>
            </h1>
            <p className="text-lg md:text-xl text-gray-300/90 max-w-xl mx-auto lg:mx-0 leading-relaxed">
              Instantly analyze your content with{" "}
              <span className="text-pink-400 font-semibold">AI</span>. <br />
              Ask ContentGuardian anything before you publish — make every word count.
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center lg:justify-start gap-4">
              <Button
                onClick={() => router.push("/signup")}
                className="bg-gradient-to-r from-pink-500 via-red-500 to-orange-500 hover:scale-105 hover:shadow-[0_0_25px_rgba(255,0,120,0.6)] text-white text-base px-8 py-3 rounded-full font-semibold shadow-lg transition-all duration-300 flex items-center gap-2"
              >
                <Sparkles className="w-5 h-5 animate-pulse" />
                Create an Account
              </Button>

              <button
                onClick={() => router.push("/login")}
                className="text-sm text-gray-400 hover:text-pink-400 underline underline-offset-4 transition duration-200"
              >
                Already have one?
              </button>
            </div>
          </div>

          {/* Robot Illustration */}
          <div className="flex justify-center">
            <Image
              src="/robot-illustration.png"
              alt="ContentGuard AI Assistant Robot"
              width={600}
              height={520}
              priority
              className="object-contain drop-shadow-[0_0_80px_rgba(255,0,120,0.45)] hover:scale-105 transition-transform duration-500"
            />
          </div>
        </div>
      </section>
    </div>
  )
}
