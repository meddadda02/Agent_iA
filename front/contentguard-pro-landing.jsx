"use client"

import { Button } from "@/components/ui/button"
import { Sparkles, Shield, Zap } from "lucide-react"

// Composant Robot Humanoïde
const HumanoidRobot = () => {
  return (
    <div className="relative w-48 h-64 mx-auto">
      <svg viewBox="0 0 200 280" className="w-full h-full drop-shadow-2xl" xmlns="http://www.w3.org/2000/svg">
        {/* Glow Effects */}
        <defs>
          <filter id="glow">
            <feGaussianBlur stdDeviation="3" result="coloredBlur" />
            <feMerge>
              <feMergeNode in="coloredBlur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
          <linearGradient id="bodyGradient" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#60a5fa" />
            <stop offset="50%" stopColor="#3b82f6" />
            <stop offset="100%" stopColor="#1e40af" />
          </linearGradient>
          <linearGradient id="headGradient" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#34d399" />
            <stop offset="100%" stopColor="#059669" />
          </linearGradient>
        </defs>

        {/* Corps principal */}
        <rect
          x="70"
          y="100"
          width="60"
          height="80"
          rx="15"
          fill="url(#bodyGradient)"
          stroke="#1e40af"
          strokeWidth="2"
        />

        {/* Tête */}
        <rect x="75" y="40" width="50" height="50" rx="25" fill="url(#headGradient)" stroke="#059669" strokeWidth="2" />

        {/* Yeux lumineux */}
        <circle cx="88" cy="60" r="6" fill="#00ffff" filter="url(#glow)" className="animate-pulse" />
        <circle cx="112" cy="60" r="6" fill="#00ffff" filter="url(#glow)" className="animate-pulse" />

        {/* Pupilles */}
        <circle cx="88" cy="60" r="3" fill="#0066cc" />
        <circle cx="112" cy="60" r="3" fill="#0066cc" />

        {/* Bouche */}
        <rect x="92" y="72" width="16" height="4" rx="2" fill="#00ffff" opacity="0.8" />

        {/* Bras gauche */}
        <rect x="45" y="110" width="25" height="12" rx="6" fill="url(#bodyGradient)" stroke="#1e40af" strokeWidth="1" />

        {/* Bras droit */}
        <rect
          x="130"
          y="110"
          width="25"
          height="12"
          rx="6"
          fill="url(#bodyGradient)"
          stroke="#1e40af"
          strokeWidth="1"
        />

        {/* Mains */}
        <circle cx="52" cy="116" r="8" fill="#60a5fa" stroke="#1e40af" strokeWidth="1" />
        <circle cx="148" cy="116" r="8" fill="#60a5fa" stroke="#1e40af" strokeWidth="1" />

        {/* Jambes */}
        <rect x="80" y="180" width="15" height="40" rx="7" fill="url(#bodyGradient)" stroke="#1e40af" strokeWidth="1" />
        <rect
          x="105"
          y="180"
          width="15"
          height="40"
          rx="7"
          fill="url(#bodyGradient)"
          stroke="#1e40af"
          strokeWidth="1"
        />

        {/* Pieds */}
        <ellipse cx="87" cy="230" rx="12" ry="8" fill="#1e40af" />
        <ellipse cx="113" cy="230" rx="12" ry="8" fill="#1e40af" />

        {/* Détails technologiques sur le torse */}
        <rect x="85" y="120" width="30" height="3" rx="1" fill="#00ffff" opacity="0.6" />
        <rect x="85" y="130" width="20" height="3" rx="1" fill="#00ffff" opacity="0.6" />
        <rect x="85" y="140" width="25" height="3" rx="1" fill="#00ffff" opacity="0.6" />

        {/* Antenne */}
        <line x1="100" y1="40" x2="100" y2="25" stroke="#00ffff" strokeWidth="2" />
        <circle cx="100" cy="22" r="3" fill="#ff6b6b" className="animate-ping" />

        {/* Épaules */}
        <circle cx="70" cy="105" r="8" fill="#3b82f6" stroke="#1e40af" strokeWidth="1" />
        <circle cx="130" cy="105" r="8" fill="#3b82f6" stroke="#1e40af" strokeWidth="1" />
      </svg>

      {/* Particules flottantes autour du robot */}
      <div className="absolute top-4 left-8 w-2 h-2 bg-cyan-400 rounded-full animate-bounce opacity-60"></div>
      <div className="absolute top-12 right-6 w-1 h-1 bg-blue-400 rounded-full animate-ping opacity-80"></div>
      <div className="absolute bottom-16 left-4 w-1.5 h-1.5 bg-green-400 rounded-full animate-pulse opacity-70"></div>
      <div className="absolute bottom-8 right-8 w-1 h-1 bg-purple-400 rounded-full animate-bounce opacity-60"></div>
    </div>
  )
}

export default function Component() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-blue-950 to-slate-900 relative overflow-hidden">
      {/* Background Effects */}
      <div className="absolute inset-0">
        <div className="absolute top-20 left-10 w-72 h-72 bg-blue-500/10 rounded-full blur-3xl"></div>
        <div className="absolute bottom-20 right-10 w-96 h-96 bg-purple-500/10 rounded-full blur-3xl"></div>
        <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-80 h-80 bg-pink-500/5 rounded-full blur-3xl"></div>
      </div>

      {/* Animated Grid Background */}
      <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.02)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.02)_1px,transparent_1px)] bg-[size:50px_50px]"></div>

      <div className="relative z-10 min-h-screen flex flex-col items-center justify-between p-6 text-white max-w-sm mx-auto">
        {/* Header with Enhanced Logo */}
        <div className="pt-12 pb-8">
          <div className="flex items-center gap-1 text-xl font-bold group cursor-pointer">
            <span className="bg-gradient-to-r from-red-500 to-pink-500 text-white px-3 py-2 rounded-lg shadow-lg transform group-hover:scale-105 transition-all duration-300">
              Dev
            </span>
            <span className="bg-gradient-to-r from-white to-gray-100 text-slate-900 px-3 py-2 rounded-lg shadow-lg transform group-hover:scale-105 transition-all duration-300">
              aktus
            </span>
          </div>
        </div>

        {/* Main Content with Glass Effect */}
        <div className="flex-1 flex flex-col items-center justify-center text-center space-y-8">
          {/* Enhanced Title Section */}
          <div className="space-y-4 backdrop-blur-sm bg-white/5 p-8 rounded-3xl border border-white/10 shadow-2xl">
            <div className="flex items-center justify-center gap-2 mb-4">
              <Sparkles className="w-6 h-6 text-yellow-400 animate-pulse" />
              <Shield className="w-6 h-6 text-blue-400" />
              <Zap className="w-6 h-6 text-purple-400 animate-pulse" />
            </div>

            <h1 className="text-3xl font-bold bg-gradient-to-r from-white via-blue-100 to-white bg-clip-text text-transparent leading-tight">
              Meet{" "}
              <span className="bg-gradient-to-r from-red-400 via-pink-500 to-red-600 bg-clip-text text-transparent">
                ContentGuard
              </span>{" "}
              !
            </h1>

            <p className="text-gray-300 text-base leading-relaxed max-w-xs font-light">
              <span className="text-blue-300 font-medium">Instantly analyze</span> your content with{" "}
              <span className="text-purple-300 font-medium">AI</span>.
              <br />
              Ask ContentGuardian anything
              <br />
              <span className="text-pink-300 font-medium">before you publish!</span>
            </p>
          </div>

          {/* Enhanced Robot Section */}
          <div className="relative">
            {/* Glow Effect Behind Robot */}
            <div className="absolute inset-0 bg-gradient-to-r from-blue-500/20 via-purple-500/20 to-pink-500/20 rounded-full blur-2xl scale-150"></div>

            {/* Robot Container */}
            <div className="relative bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-sm rounded-3xl p-8 border border-white/20 shadow-2xl transform hover:scale-105 transition-all duration-500">
              <HumanoidRobot />

              {/* Floating Elements */}
              <div className="absolute -top-2 -right-2 w-4 h-4 bg-green-400 rounded-full animate-ping"></div>
              <div className="absolute -bottom-2 -left-2 w-3 h-3 bg-blue-400 rounded-full animate-pulse"></div>
            </div>
          </div>
        </div>

        {/* Enhanced CTA Section */}
        <div className="w-full space-y-6 pb-12">
          <Button
            className="w-full bg-gradient-to-r from-pink-500 via-red-500 to-pink-600 hover:from-pink-600 hover:via-red-600 hover:to-pink-700 text-white font-semibold py-4 rounded-2xl text-lg shadow-2xl border border-pink-400/20 transform hover:scale-105 hover:shadow-pink-500/25 transition-all duration-300 relative overflow-hidden group"
            size="lg"
          >
            <span className="relative z-10 flex items-center justify-center gap-2">
              <Sparkles className="w-5 h-5" />
              Create An Account
              <Sparkles className="w-5 h-5" />
            </span>
            <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent transform -skew-x-12 -translate-x-full group-hover:translate-x-full transition-transform duration-1000"></div>
          </Button>

          <button className="text-center text-gray-400 text-sm hover:text-white transition-colors duration-300 underline decoration-dotted underline-offset-4 hover:decoration-solid">
            Already have an account? Sign in
          </button>
        </div>

        {/* Floating Particles */}
        <div
          className="absolute top-1/4 left-8 w-2 h-2 bg-blue-400 rounded-full animate-bounce"
          style={{ animationDelay: "0s" }}
        ></div>
        <div
          className="absolute top-1/3 right-12 w-1 h-1 bg-purple-400 rounded-full animate-bounce"
          style={{ animationDelay: "1s" }}
        ></div>
        <div
          className="absolute bottom-1/3 left-16 w-1.5 h-1.5 bg-pink-400 rounded-full animate-bounce"
          style={{ animationDelay: "2s" }}
        ></div>
      </div>
    </div>
  )
}
