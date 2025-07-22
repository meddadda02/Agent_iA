"use client"
import Image from "next/image"
import { Button } from "./ui/button"
import { Sparkles } from "./icons"

export default function ContentGuardLanding() {
  return (
    <div className="min-h-screen w-full bg-[#0f1123] text-white flex flex-col">
      
      {/* 🔝 Header */}
      <header className="sticky top-0 z-50 w-full bg-[#0f1123] shadow-sm px-6 lg:px-20 py-5 flex items-center">
        <Image
          src="/devaktus.png"
          alt="Devaktus Logo"
          width={230}
          height={44}
          priority
          className="object-contain"
        />
      </header>

      {/* 🎯 Hero Section */}
      <section className="flex-1 w-full px-6 lg:px-20 py-24 flex items-center justify-center">
        <div className="max-w-7xl w-full grid grid-cols-1 lg:grid-cols-2 gap-24 items-center">
          
          {/* 📝 Text */}
          <div className="space-y-10 text-center lg:text-left">
            <h1 className="text-5xl md:text-6xl font-extrabold tracking-tight leading-tight">
              Meet <span className="text-pink-500">ContentGuard</span><span className="text-pink-500"> !</span>
            </h1>

            <p className="text-lg md:text-xl text-gray-300 max-w-xl mx-auto lg:mx-0 leading-relaxed">
              Instantly analyze your content with <span className="text-pink-400 font-medium">AI</span>.
              Ask ContentGuardian anything before you publish — make every word count.
            </p>

            <div className="flex flex-col sm:flex-row items-center justify-center lg:justify-start gap-4">
              <Button className="bg-gradient-to-r from-pink-500 to-red-500 hover:brightness-110 text-white text-base px-6 py-3 rounded-full font-semibold shadow-lg transition-all duration-200 flex items-center gap-2">
                <Sparkles className="w-5 h-5" />
                Create an Account
              </Button>

              <button className="text-sm text-gray-400 hover:text-white underline underline-offset-4 transition duration-150">
                Already have one
              </button>
            </div>
          </div>

          {/* 🤖 Robot Illustration */}
          <div className="flex justify-center">
            <Image
              src="/robot-illustration.png"
              alt="ContentGuard AI Assistant Robot"
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
