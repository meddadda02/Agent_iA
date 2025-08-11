"use client"

import { useState, useEffect, useRef, useCallback } from "react"
import { Menu, Trash, Pencil, Sun, Moon, MessageSquare, Search } from "lucide-react"
import { useRouter } from "next/navigation"
import Image from "next/image"

const BASE_URL = "http://localhost:8000" // adapte si besoin

export default function Chat() {
  const router = useRouter()
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState("")
  const [history, setHistory] = useState([])
  const [search, setSearch] = useState("")
  const [models, setModels] = useState([])
  const [selectedModel, setSelectedModel] = useState("")
  const [editId, setEditId] = useState(null)
  const [menuOpen, setMenuOpen] = useState(false)
  const [darkMode, setDarkMode] = useState(() => {
    if (typeof window !== "undefined") {
      const saved = localStorage.getItem("darkMode")
      if (saved !== null) return saved === "true"
      return window.matchMedia("(prefers-color-scheme: dark)").matches
    }
    return true
  })
  const [isLoading, setIsLoading] = useState(false)
  const [token, setToken] = useState(null)
  const [currentUser, setCurrentUser] = useState(null)
  const [isAuthLoading, setIsAuthLoading] = useState(true)
  const [isProfileMenuOpen, setIsProfileMenuOpen] = useState(false)

  const messageEndRef = useRef(null)
  const profileMenuRef = useRef(null)

  // Authentication and session management
  useEffect(() => {
    const authenticateUser = async () => {
      setIsAuthLoading(true)

      const savedToken = localStorage.getItem("token")
      const savedLoginTimestamp = localStorage.getItem("lastLoginTimestamp")
      const twelveHours = 12 * 60 * 60 * 1000

      if (savedLoginTimestamp) {
        const timeElapsed = Date.now() - Number.parseInt(savedLoginTimestamp, 10)
        if (timeElapsed > twelveHours) {
          console.log("Client-side session expired (over 12 hours). Redirecting to login.")
          localStorage.removeItem("token")
          localStorage.removeItem("lastLoginTimestamp")
          router.push("/login")
          return
        }
      }

      if (!savedToken) {
        console.log("No token found after client-side check. Redirecting to login.")
        router.push("/login")
        return
      }

      try {
        const res = await fetch(`${BASE_URL}/api/users/users/me`, {
          headers: { Authorization: `Bearer ${savedToken}` },
        })

        if (res.status === 401) {
          console.log("Server rejected token (401). Clearing token and redirecting to login.")
          localStorage.removeItem("token")
          localStorage.removeItem("lastLoginTimestamp")
          router.push("/login")
          return
        }

        if (!res.ok) {
          throw new Error("Failed to fetch user profile")
        }

        const userData = await res.json()
        setCurrentUser(userData)
        setToken(savedToken)
        console.log("User authenticated and profile fetched:", userData.username)
      } catch (error) {
        console.error("Authentication error during profile fetch:", error)
        localStorage.removeItem("token")
        localStorage.removeItem("lastLoginTimestamp")
        router.push("/login")
        return
      } finally {
        setIsAuthLoading(false)
      }
    }

    authenticateUser()
  }, [router])

  // Apply theme + store preference
  useEffect(() => {
    document.documentElement.classList.toggle("dark", darkMode)
    localStorage.setItem("darkMode", darkMode.toString())
  }, [darkMode])

  // Scroll to bottom on new message
  useEffect(() => {
    messageEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  // Load available models (depends on authentication)
  useEffect(() => {
    async function fetchModels() {
      if (!token || !currentUser) return
      try {
        const res = await fetch(`${BASE_URL}/moderation/models`, {
          headers: { Authorization: `Bearer ${token}` },
        })
        if (!res.ok) throw new Error("Erreur chargement modèles")
        const data = await res.json()
        setModels(data.models || [])
        setSelectedModel(data.models?.[0] || "")
      } catch (error) {
        console.error("Erreur fetchModels:", error)
        setModels([])
        setSelectedModel("")
      }
    }
    fetchModels()
  }, [token, currentUser])

  // Fetch full history (memoized)
  const fetchHistory = useCallback(async () => {
    if (!token || !currentUser) return
    try {
      const res = await fetch(`${BASE_URL}/moderation/history`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok) throw new Error("Erreur chargement historique")
      const data = await res.json()
      setHistory(data || [])
    } catch (error) {
      console.error("Erreur fetchHistory:", error)
      setHistory([])
    }
  }, [token, currentUser])

  // Search history (memoized)
  const searchHistory = useCallback(async () => {
    if (!token || !currentUser) return
    if (!search.trim()) {
      await fetchHistory()
      return
    }
    try {
      const res = await fetch(`${BASE_URL}/moderation/history/search?search_query=${encodeURIComponent(search)}`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok) throw new Error("Erreur recherche historique")
      const data = await res.json()
      setHistory(data || [])
    } catch (error) {
      console.error("Erreur searchHistory:", error)
    }
  }, [search, token, currentUser, fetchHistory])

  // Initial load of full history
  useEffect(() => {
    fetchHistory()
  }, [fetchHistory])

  // Search history (backend)
  useEffect(() => {
    searchHistory()
  }, [searchHistory])

  // Close profile menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (profileMenuRef.current && !profileMenuRef.current.contains(event.target)) {
        setIsProfileMenuOpen(false)
      }
    }
    document.addEventListener("mousedown", handleClickOutside)
    return () => {
      document.removeEventListener("mousedown", handleClickOutside)
    }
  }, [])

  // Function to start a new chat
  const startNewChat = () => {
    setMessages([])
    setInput("")
    setEditId(null)
    setMenuOpen(false)
  }

  // Delete an analysis
  const deleteAnalysis = async (id) => {
    if (!confirm("Supprimer cette analyse ?")) return
    if (!token) return
    try {
      const res = await fetch(`${BASE_URL}/moderation/history/${id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      })
      if (res.status === 204) {
        setHistory((prev) => prev.filter((item) => item.id !== id))
        setMessages([])
        setInput("")
        setEditId(null)
      } else {
        throw new Error("Erreur suppression analyse")
      }
    } catch (error) {
      alert("Erreur suppression analyse")
      console.error(error)
    }
  }

  // Update question (PATCH)
  const updateAnalysisQuestion = async (id, newQuestion) => {
    if (!token) return
    try {
      const res = await fetch(`${BASE_URL}/moderation/history/${id}`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ question: newQuestion }),
      })
      if (!res.ok) throw new Error("Erreur mise à jour question")
      const updated = await res.json()
      setHistory((prev) => prev.map((item) => (item.id === id ? updated : item)))
      setEditId(null)
      setInput("")
    } catch (error) {
      alert("Erreur mise à jour question")
      console.error(error)
    }
  }

  // Send question / analysis
  const handleAsk = async () => {
    if (!input.trim() || isLoading) return
    setIsLoading(true)
    setMessages((prev) => [...prev, { text: input, isUser: true }])
    if (!token) return

    try {
      const res = await fetch(`${BASE_URL}/moderation/check`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ text: input, model: selectedModel }),
      })
      if (!res.ok) throw new Error("Erreur pendant l'analyse")
      const data = await res.json()

      // Build formatted message
      const groq = data.groq || {}
      const status = groq.status || data.status || "non conforme"
      const category = groq.category || data.category || "inconnu"
      const reasoning = groq.reasoning || data.reasoning || ""
      const messageText = `Le texte entré est ${status} aux règles YouTube.\nCatégorie : ${category}\nExplication : ${reasoning}`

      setMessages((prev) => [...prev, { text: messageText, isUser: false }])

      // After successful analysis, re-fetch history to get the new item with its actual ID
      await fetchHistory()
    } catch (error) {
      setMessages((prev) => [...prev, { text: "Erreur pendant l'analyse", isUser: false }])
      console.error(error)
    }
    setInput("")
    setEditId(null)
    setIsLoading(false)
  }

  // Display a loading screen during authentication
  if (isAuthLoading) {
    return (
      <div
        className={`flex items-center justify-center h-screen ${darkMode ? "bg-[#0f1123] text-white" : "bg-gray-50 text-gray-900"}`}
      >
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-pink-500 mx-auto mb-4"></div>
          <p className={`text-lg ${darkMode ? "text-gray-300" : "text-gray-600"}`}>
            Chargement de l'authentification...
          </p>
        </div>
      </div>
    )
  }

  // If the user is not authenticated after loading, it means they've been redirected.
  if (!currentUser) {
    return (
      <div
        className={`flex items-center justify-center h-screen ${darkMode ? "bg-[#0f1123] text-white" : "bg-gray-50 text-gray-900"}`}
      >
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-pink-500 mx-auto mb-4"></div>
          <p className={`text-lg ${darkMode ? "text-gray-300" : "text-gray-600"}`}>Redirection en cours...</p>
        </div>
      </div>
    )
  }

  return (
    <div
      className={`h-screen flex font-sans transition-colors duration-300 ${darkMode ? "bg-[#0f1123] text-white" : "bg-gray-50 text-gray-900"}`}
    >
      {/* Sidebar */}
      <aside
        className={`fixed top-0 left-0 h-full w-80 p-6 overflow-y-auto transition-transform duration-300 z-50 flex flex-col shadow-2xl
        ${darkMode ? "bg-[#0f1123] border-r border-gray-800" : "bg-white border-r border-gray-200"}
        ${menuOpen ? "translate-x-0" : "-translate-x-full"}`}
      >
        <div className="flex justify-between items-center mb-8">
          <h2 className={`text-2xl font-bold ${darkMode ? "text-white" : "text-gray-900"}`}>Historique</h2>
        </div>

        {/* New Chat Button */}
        <button
          onClick={startNewChat}
          className="w-full flex items-center justify-center gap-3 px-6 py-4 mb-6 rounded-full font-semibold bg-gradient-to-r from-pink-500 to-red-500 hover:brightness-110 text-white transition-all duration-200 shadow-lg hover:shadow-xl transform hover:scale-[1.02]"
          aria-label="Nouveau chat"
        >
          <MessageSquare size={20} /> Nouvelle Analyse
        </button>

        {/* Search Input */}
        <div className="relative mb-6">
          <Search
            className={`absolute left-4 top-1/2 transform -translate-y-1/2 ${darkMode ? "text-gray-400" : "text-gray-500"}`}
            size={18}
          />
          <input
            type="search"
            placeholder="Rechercher dans l'historique..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className={`w-full pl-12 pr-4 py-3 rounded-full border text-sm focus:outline-none focus:ring-2 focus:ring-pink-500 focus:border-transparent backdrop-blur-sm transition-colors
            ${
              darkMode
                ? "border-gray-700 bg-gray-800/50 text-white placeholder-gray-400"
                : "border-gray-300 bg-white/80 text-gray-900 placeholder-gray-500"
            }`}
            aria-label="Recherche dans l'historique"
          />
        </div>

        {/* History List */}
        <div className="flex-1 overflow-y-auto pr-2 space-y-3">
          {history.length === 0 && (
            <div className="text-center py-12">
              <MessageSquare className={`mx-auto mb-4 ${darkMode ? "text-gray-600" : "text-gray-400"}`} size={48} />
              <p className={`text-sm select-none ${darkMode ? "text-gray-400" : "text-gray-500"}`}>
                Aucun historique disponible
              </p>
            </div>
          )}
          {history.map((item) => (
            <div
              key={item.id}
              className={`p-4 rounded-2xl cursor-pointer transition-all duration-200 group shadow-lg hover:shadow-xl backdrop-blur-sm
              ${
                darkMode
                  ? "bg-gray-800/30 hover:bg-gray-800/50 border border-gray-700/50 hover:border-pink-500/30"
                  : "bg-white/60 hover:bg-white/80 border border-gray-200 hover:border-pink-300"
              }`}
              onClick={() => {
                setMessages([
                  { text: item.question, isUser: true },
                  {
                    text: `Le texte entré est ${
                      item.status === "conforme" ? "conforme" : "non conforme"
                    } aux règles YouTube.\nCatégorie : ${item.category}\nExplication : ${item.reasoning}`,
                    isUser: false,
                  },
                ])
                setEditId(null)
                setInput("")
                setMenuOpen(false)
              }}
              role="button"
              tabIndex={0}
            >
              <div className={`font-medium truncate mb-2 text-sm ${darkMode ? "text-white" : "text-gray-900"}`}>
                Q: {item.question}
              </div>
              <div className="text-xs truncate text-pink-500 mb-1">Réponse : {item.response || "Aucune"}</div>
              <div className={`text-xs italic ${darkMode ? "text-gray-500" : "text-gray-400"}`}>
                Statut : {item.status || "N/A"}
              </div>

              <div className="flex gap-2 mt-3 justify-end opacity-0 group-hover:opacity-100 transition-opacity duration-200">
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    setInput(item.question)
                    setEditId(item.id)
                  }}
                  aria-label="Modifier la question"
                  className="p-2 rounded-lg hover:bg-pink-500/20 text-pink-500 focus:outline-none focus:ring-2 focus:ring-pink-500 transition-colors"
                >
                  <Pencil size={14} />
                </button>

                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    deleteAnalysis(item.id)
                  }}
                  aria-label="Supprimer l'analyse"
                  className="p-2 rounded-lg hover:bg-red-500/20 text-red-500 focus:outline-none focus:ring-2 focus:ring-red-500 transition-colors"
                >
                  <Trash size={14} />
                </button>
              </div>
            </div>
          ))}
        </div>

        {/* User Profile Display */}
        {currentUser && (
          <div
            className={`flex items-center gap-3 mt-6 p-4 rounded-2xl backdrop-blur-sm
          ${darkMode ? "bg-gray-800/30 border border-gray-700/50" : "bg-white/60 border border-gray-200"}`}
          >
            {currentUser.photo ? (
              <img
                src={currentUser.photo || "/images/default-avatar.png"}
                alt="User profile"
                className="w-12 h-12 rounded-full object-cover border-2 border-pink-500"
              />
            ) : (
              <div className="w-12 h-12 rounded-full bg-gradient-to-r from-pink-500 to-red-500 flex items-center justify-center text-white font-bold text-lg">
                {currentUser.username?.charAt(0).toUpperCase()}
              </div>
            )}
            <div>
              <p className={`font-semibold text-sm ${darkMode ? "text-white" : "text-gray-900"}`}>
                {currentUser.username}
              </p>
              <p className={`text-xs ${darkMode ? "text-gray-400" : "text-gray-500"}`}>Utilisateur ContentGuard</p>
            </div>
          </div>
        )}
      </aside>

      {/* Main chat panel */}
      <main className={`flex-1 flex flex-col transition-all duration-300 ${menuOpen ? "ml-80" : "ml-0"}`}>
        {/* Header */}
        <header
          className={`sticky top-0 z-40 w-full shadow-sm px-6 lg:px-8 py-5 flex items-center justify-between transition-colors
        ${darkMode ? "bg-[#0f1123] border-b border-gray-800" : "bg-white border-b border-gray-200"}`}
        >
          <div className="flex items-center gap-6">
            <button
              onClick={() => setMenuOpen(!menuOpen)}
              className={`p-3 rounded-lg transition-colors
              ${darkMode ? "hover:bg-gray-800/50" : "hover:bg-gray-100"}`}
              aria-label="Toggle menu"
            >
              <Menu size={24} className="text-pink-500" />
            </button>
            <Image
              src="/devaktus.png"
              alt="Devaktus Logo"
              width={180}
              height={34}
              priority
              className="object-contain"
            />
          </div>

          <div className="flex items-center gap-4">
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              className={`rounded-full px-4 py-2 text-sm border cursor-pointer focus:outline-none focus:ring-2 focus:ring-pink-500 focus:border-transparent backdrop-blur-sm transition-colors
              ${darkMode ? "border-gray-700 bg-gray-800/50 text-white" : "border-gray-300 bg-white/80 text-gray-900"}`}
              aria-label="Choisir un modèle"
            >
              {models.length === 0 && <option value="">Modèles indisponibles</option>}
              {models.map((model, i) => (
                <option key={i} value={model}>
                  {model}
                </option>
              ))}
            </select>

            <button
              onClick={() => setDarkMode(!darkMode)}
              className={`p-3 rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-pink-500
              ${darkMode ? "hover:bg-gray-800/50" : "hover:bg-gray-100"}`}
              aria-label="Changer le thème"
            >
              {darkMode ? <Sun size={20} className="text-yellow-500" /> : <Moon size={20} className="text-pink-500" />}
            </button>

            {/* Profile Picture and Dropdown */}
            <div className="relative" ref={profileMenuRef}>
              <button
                onClick={() => setIsProfileMenuOpen(!isProfileMenuOpen)}
                className="p-1 rounded-full focus:outline-none focus:ring-2 focus:ring-pink-500"
                aria-label="Ouvrir le menu du profil"
              >
                {currentUser.photo ? (
                  <img
                    src={currentUser.photo || "/images/default-avatar.png"}
                    alt="User profile"
                    className="w-10 h-10 rounded-full object-cover border-2 border-pink-500"
                  />
                ) : (
                  <div className="w-10 h-10 rounded-full bg-gradient-to-r from-pink-500 to-red-500 flex items-center justify-center text-white font-bold text-sm">
                    {currentUser.username?.charAt(0).toUpperCase()}
                  </div>
                )}
              </button>

              {isProfileMenuOpen && (
                <div
                  className={`absolute right-0 mt-3 w-64 rounded-2xl shadow-2xl py-2 border z-10 backdrop-blur-sm
                ${darkMode ? "bg-gray-900/95 border-gray-700" : "bg-white/95 border-gray-200"}`}
                >
                  <div
                    className={`flex items-center gap-3 px-4 py-3 border-b
                  ${darkMode ? "border-gray-700" : "border-gray-200"}`}
                  >
                    {currentUser.photo ? (
                      <img
                        src={currentUser.photo || "/images/default-avatar.png"}
                        alt="User profile"
                        className="w-10 h-10 rounded-full object-cover border-2 border-pink-500"
                      />
                    ) : (
                      <div className="w-10 h-10 rounded-full bg-gradient-to-r from-pink-500 to-red-500 flex items-center justify-center text-white font-bold text-sm">
                        {currentUser.username?.charAt(0).toUpperCase()}
                      </div>
                    )}
                    <div>
                      <p className={`font-semibold text-sm ${darkMode ? "text-white" : "text-gray-900"}`}>
                        {currentUser.username}
                      </p>
                      <p className={`text-xs ${darkMode ? "text-gray-400" : "text-gray-500"}`}>
                        Utilisateur ContentGuard
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={() => {
                      router.push("/profile")
                      setIsProfileMenuOpen(false)
                    }}
                    className={`block w-full text-left px-4 py-3 transition-colors text-sm
                    ${darkMode ? "text-white hover:bg-gray-800/50" : "text-gray-900 hover:bg-gray-100"}`}
                  >
                    Personnaliser
                  </button>
                  <button
                    onClick={() => {
                      localStorage.removeItem("token")
                      localStorage.removeItem("lastLoginTimestamp")
                      router.push("/login")
                      setIsProfileMenuOpen(false)
                    }}
                    className={`block w-full text-left px-4 py-3 text-red-500 transition-colors text-sm
                    ${darkMode ? "hover:bg-red-500/10" : "hover:bg-red-50"}`}
                  >
                    Déconnexion
                  </button>
                </div>
              )}
            </div>
          </div>
        </header>

        {/* Messages */}
        <section
          className={`flex-1 flex flex-col overflow-y-auto px-6 lg:px-8 py-8 space-y-6 transition-colors
          ${darkMode ? "bg-[#0f1123]" : "bg-gray-50"}`}
          aria-live="polite"
          role="log"
        >
          {messages.length === 0 && (
            <div className="text-center py-24">
              <div className="mb-8">
                <div
                  className={`w-24 h-24 mx-auto bg-gradient-to-r from-pink-500 to-red-500 rounded-full flex items-center justify-center mb-6 ${darkMode ? "shadow-[0_0_70px_rgba(255,0,120,0.4)]" : "shadow-lg"}`}
                >
                  <MessageSquare size={40} className="text-white" />
                </div>
              </div>
              <h1
                className={`text-5xl md:text-6xl font-extrabold tracking-tight leading-tight mb-6 ${darkMode ? "text-white" : "text-gray-900"}`}
              >
                Meet <span className="text-pink-500">ContentGuard</span>
                <span className="text-pink-500">!</span>
              </h1>
              <p
                className={`text-lg md:text-xl max-w-2xl mx-auto leading-relaxed mb-8
              ${darkMode ? "text-gray-300" : "text-gray-600"}`}
              >
                Analysez instantanément votre contenu avec l'<span className="text-pink-500 font-medium">IA</span>.
                Demandez à ContentGuard tout ce que vous voulez avant de publier — faites que chaque mot compte.
              </p>
              <p className={`${darkMode ? "text-gray-400" : "text-gray-500"}`}>
                Posez votre question ci-dessous pour commencer 👇
              </p>
            </div>
          )}

          {messages.map((msg, i) => (
            <div
              key={i}
              className={`max-w-4xl px-6 py-4 rounded-3xl whitespace-pre-wrap break-words shadow-lg transition-all duration-200 ${
                msg.isUser
                  ? "bg-gradient-to-r from-pink-500 to-red-500 text-white self-end ml-auto"
                  : darkMode
                    ? "bg-gray-800/30 text-white self-start border border-gray-700/50 backdrop-blur-sm"
                    : "bg-white text-gray-900 self-start border border-gray-200 backdrop-blur-sm"
              }`}
            >
              {msg.isLoading ? (
                <div className="flex items-center gap-3">
                  <div
                    className={`animate-spin rounded-full h-5 w-5 border-b-2 ${msg.isUser ? "border-white" : "border-pink-500"}`}
                  ></div>
                  <span
                    className={`italic ${msg.isUser ? "text-white" : darkMode ? "text-gray-300" : "text-gray-600"}`}
                  >
                    Analyse en cours...
                  </span>
                </div>
              ) : (
                msg.text
              )}
            </div>
          ))}
          <div ref={messageEndRef} />
        </section>

        {/* Input area */}
        <footer
          className={`px-6 lg:px-8 py-6 border-t transition-colors
        ${darkMode ? "border-gray-800 bg-[#0f1123]" : "border-gray-200 bg-white"}`}
        >
          <form
            onSubmit={(e) => {
              e.preventDefault()
              if (editId) {
                updateAnalysisQuestion(editId, input)
              } else {
                handleAsk()
              }
            }}
            className="flex items-center gap-4 max-w-4xl mx-auto"
          >
            <input
              type="text"
              aria-label="Tapez votre question"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Analysez votre contenu avec ContentGuard..."
              className={`flex-1 rounded-full px-6 py-4 border text-lg focus:outline-none focus:ring-2 focus:ring-pink-500 focus:border-transparent backdrop-blur-sm transition-colors
              ${
                darkMode
                  ? "border-gray-700 bg-gray-800/30 text-white placeholder-gray-400"
                  : "border-gray-300 bg-white/80 text-gray-900 placeholder-gray-500"
              }`}
            />
            <button
              type="submit"
              disabled={isLoading}
              className="rounded-full px-8 py-4 font-semibold bg-gradient-to-r from-pink-500 to-red-500 hover:brightness-110 text-white transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-pink-500 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg hover:shadow-xl transform hover:scale-[1.02] flex items-center gap-2"
            >
              {editId ? "Modifier" : isLoading ? "Analyse..." : "Analyser"}
            </button>
          </form>
        </footer>
      </main>
    </div>
  )
}
