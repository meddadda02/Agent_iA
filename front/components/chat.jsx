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
  const [menuOpen, setMenuOpen] = useState(true)
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
  const nextMsgId = useRef(1)
  const audioInputRef = useRef(null)
  const videoInputRef = useRef(null)
  const imageInputRef = useRef(null)

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
      }).catch(err => {
        console.error("Network error:", err);
        throw new Error("Erreur de connexion au serveur");
      })
      if (!res.ok) throw new Error(`Erreur chargement historique (${res.status})`)
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

  // Initial load of full history - disabled to prevent duplication
  // useEffect(() => {
  //   fetchHistory()
  // }, [fetchHistory])

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
    setMessages((prev) => [...prev, { id: nextMsgId.current++, text: input, isUser: true, kind: "user" }])
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

      // Normalise & store full payload for richer rendering
      const groq = data.groq || {}
      const status = groq.status || data.status || "non_conforme"
      const category = groq.category || data.category || "inconnu"
      const reasoning = groq.reasoning || data.reasoning || ""

      const analysisMsg = {
        id: nextMsgId.current++,
        isUser: false,
        kind: "analysis",
        status,
        category,
        reasoning,
        payload: data,
        expanded: false,
        showJson: false,
      }

      setMessages((prev) => [...prev, analysisMsg])

      // await fetchHistory() 
    } catch (error) {
      const msg = typeof error?.message === "string" ? error.message : "Erreur pendant l'analyse"
      setMessages((prev) => [
        ...prev,
        {
          id: nextMsgId.current++,
          isUser: false,
          kind: "error",
          text: msg,
        },
      ])
      console.error(error)
    }
    setInput("")
    setEditId(null)
    setIsLoading(false)
  }

  // --- Audio upload ---
  const handlePickAudio = useCallback(() => {
    audioInputRef.current?.click()
  }, [])

  const handleUploadAudio = useCallback(
    async (e) => {
      const file = e.target.files?.[0]
      e.target.value = "" // reset so same file can be reselected
      if (!file || !token || isLoading) return

      try {
        setIsLoading(true)
        const audioUrl = URL.createObjectURL(file)
        setMessages((prev) => [
          ...prev,
          {
            id: nextMsgId.current++,
            kind: "user",
            isUser: true,
            text: `Audio: ${file.name}`,
            mediaType: "audio",
            mediaUrl: audioUrl,
            fileName: file.name,
          },
        ])

        const form = new FormData()
        form.append("file", file)
        if (selectedModel) form.append("model", selectedModel)

        const res = await fetch(`${BASE_URL}/moderation/audio`, {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
          body: form,
        }).catch(err => {
          console.error("Network error:", err);
          throw new Error("Erreur de connexion au serveur - Vérifiez que le backend est démarré");
        })
        if (!res.ok) throw new Error(`Erreur pendant l'analyse audio (${res.status})`)
        const data = await res.json()

        // Keep audio response structure simple and independent
        const audioModeration = data.audio_moderation || {}
        const contentModeration = data.content_moderation || {}
        
        // Base status and reasoning on audio-specific information
        const lyricsAnalysis = audioModeration.lyrics_analysis || {}
        const copyrightAnalysis = audioModeration.copyright_analysis || {}
        
        const status = audioModeration.can_publish ? "conforme" : "bloqué"
        const category = "audio"
        
        // Build detailed structured reasoning
        const reasoningLines = []
        
        // Text analysis section - only GROQ
        if (contentModeration.groq) {
          reasoningLines.push("📖 Analyse du texte")
          reasoningLines.push(`Statut : ${contentModeration.groq.status === "conforme" ? "✅ Conforme" : "❌ Non conforme"}`)
          if (contentModeration.groq.reasoning) {
            reasoningLines.push(`Détails : ${contentModeration.groq.reasoning}`)
          }
          reasoningLines.push(`Insulte détectée : ${contentModeration.groq.is_insult ? "❌ Oui" : "✅ Non"}`)
          reasoningLines.push("")
        }
        
        // Audio analysis section
        reasoningLines.push("🎶 Analyse audio")
        reasoningLines.push(`Statut : ${audioModeration.can_publish ? "✅ Autorisé" : "🚫 Bloqué"} ${copyrightAnalysis.music_detected ? "(musique protégée détectée)" : ""}`)
        
        if (copyrightAnalysis.music_detected) {
          if (copyrightAnalysis.title) reasoningLines.push(`Titre : ${copyrightAnalysis.title}`)
          if (copyrightAnalysis.artist) reasoningLines.push(`Artiste : ${copyrightAnalysis.artist}`)
          if (copyrightAnalysis.album) reasoningLines.push(`Album : ${copyrightAnalysis.album}`)
          if (copyrightAnalysis.release_date) reasoningLines.push(`Date de sortie : ${copyrightAnalysis.release_date}`)
          if (copyrightAnalysis.confidence_score) reasoningLines.push(`Confiance : ${Math.round(copyrightAnalysis.confidence_score * 100)}%`)
          
          if (audioModeration.copyrighted_segment) {
            const segment = audioModeration.copyrighted_segment
            reasoningLines.push(`Segment protégé : ⏱️ ${segment.start_time} → ${segment.end_time}`)
          }
          
          if (copyrightAnalysis.strike_risk_level) {
            const riskEmoji = copyrightAnalysis.strike_risk_level === "critical" ? "⚠️" : 
                             copyrightAnalysis.strike_risk_level === "high" ? "⚠️" : "⚡"
            reasoningLines.push(`Niveau de risque : ${riskEmoji} ${copyrightAnalysis.strike_risk_level === "critical" ? "Critique (strike probable)" : copyrightAnalysis.strike_risk_level}`)
          }
        }
        
        reasoningLines.push("")
        
        // Final decision section
        reasoningLines.push("🛑 Décision finale")
        reasoningLines.push(`Peut publier ? ${audioModeration.can_publish ? "✅ Oui" : "❌ Non"}`)
        if (audioModeration.automatic_action) {
          const actionEmoji = audioModeration.automatic_action === "block" ? "🔒" : "✅"
          const actionText = audioModeration.automatic_action === "block" ? "Blocage immédiat" : "Autorisation"
          reasoningLines.push(`Action automatique : ${actionEmoji} ${actionText}`)
        }
        if (audioModeration.violated_rules?.length > 0) {
          const rulesWithEmojis = audioModeration.violated_rules.map(rule => {
            if (rule.includes('Parodie') || rule.includes('Remix')) return `🎭 ${rule}`
            if (rule.includes('copyright') || rule.includes('droits')) return `©️ ${rule}`
            if (rule.includes('harcèlement')) return `⚠️ ${rule}`
            return rule
          })
          reasoningLines.push(`Raisons : ${rulesWithEmojis.join(", ")}`)
        }
        
        const reasoning = reasoningLines.join("\n")

        setMessages((prev) => [
          ...prev,
          {
            id: nextMsgId.current++,
            isUser: false,
            kind: "analysis",
            status,
            category,
            reasoning,
            payload: data,
            expanded: false,
            showJson: false,
          },
        ])
      } catch (error) {
        setMessages((prev) => [
          ...prev,
          { id: nextMsgId.current++, isUser: false, kind: "error", text: error?.message || "Erreur audio" },
        ])
        console.error(error)
      } finally {
        setIsLoading(false)
      }
    },
    [token, isLoading, selectedModel],
  )

  // --- Video upload ---
  const handlePickVideo = useCallback(() => {
    videoInputRef.current?.click()
  }, [])

  const handleUploadVideo = useCallback(
    async (e) => {
      const file = e.target.files?.[0]
      e.target.value = ""
      if (!file || !token || isLoading) return

      try {
        setIsLoading(true)
        const videoUrl = URL.createObjectURL(file)
        setMessages((prev) => [
          ...prev,
          {
            id: nextMsgId.current++,
            kind: "user",
            isUser: true,
            text: `Vidéo: ${file.name}`,
            mediaType: "video",
            mediaUrl: videoUrl,
            fileName: file.name,
          },
        ])

        const form = new FormData()
        form.append("file", file)
        if (selectedModel) form.append("model", selectedModel)

        const res = await fetch(`${BASE_URL}/video/moderation/analyze`, {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
          body: form,
        })
        if (!res.ok) throw new Error("Erreur pendant l'analyse vidéo")
        const data = await res.json()

        const report = data.report || {}
        const cm = report.content_moderation || {}
        const groq = (cm && cm.groq) || {}
        const status = groq.status || cm.status || report.status || "inconnu"
        const category = groq.category || cm.category || "video"
        let reasoning = cm.reasoning || "Analyse vidéo terminée"

// 👇 Include transcript (audio) timings
if (report.transcript_segments && report.transcript_segments.length > 0) {
  reasoning += "\n\n🎤 Transcription audio détectée:\n"
  report.transcript_segments.forEach((seg, idx) => {
    reasoning += `• Segment ${idx + 1}: ${seg.start} → ${seg.end}\n`
    if (seg.text) reasoning += `   Texte: "${seg.text}"\n`
  })
}

if (report.visual_analysis && report.visual_analysis.length > 0) {
  reasoning += "\n\n🖼️ Analyse visuelle des frames:\n"
  report.visual_analysis.forEach((frame, idx) => {
    reasoning += `• Frame ${idx + 1}: ${frame.timestamp}\n`
    if (frame.caption) reasoning += `   Caption: ${frame.caption}\n`
  })
}

if (report.segments && report.segments.length > 0) {
  reasoning += "\n\n⏱️ Segments problématiques détectés:\n"
  report.segments.forEach((seg, idx) => {
    reasoning += `• Segment ${idx + 1}: ${seg.start_time} → ${seg.end_time}\n`
    if (seg.reason) reasoning += `   Raison: ${seg.reason}\n`
  })
}

// 👇 Violations
if (report.text_moderation?.violations?.length > 0) {
  reasoning += "\n\n🚨 Violations détectées:\n"
  report.text_moderation.violations.forEach((vio, idx) => {
    const start = vio.start || vio.timestamp || "?"
    const end = vio.end || ""
    reasoning += `• Violation ${idx + 1}: ${start}${end ? ` → ${end}` : ""}\n`
    if (vio.violated_rules) reasoning += `   Règles: ${vio.violated_rules.join(", ")}\n`
    if (vio.text) reasoning += `   Texte: "${vio.text}"\n`
  })
}

        setMessages((prev) => [
          ...prev,
          {
            id: nextMsgId.current++,
            isUser: false,
            kind: "analysis",
            status,
            category,
            reasoning,
            payload: data,
            expanded: false,
            showJson: false,
          },
        ])
      } catch (error) {
        setMessages((prev) => [
          ...prev,
          { id: nextMsgId.current++, isUser: false, kind: "error", text: error?.message || "Erreur vidéo" },
        ])
        console.error(error)
      } finally {
        setIsLoading(false)
      }
    },
    [token, isLoading, selectedModel],
  )

  // --- Image upload ---
  const handlePickImage = useCallback(() => {
    imageInputRef.current?.click()
  }, [])

  const handleUploadImage = useCallback(
    async (e) => {
      const file = e.target.files?.[0]
      e.target.value = ""
      if (!file || !token || isLoading) return

      try {
        setIsLoading(true)
        const imageUrl = URL.createObjectURL(file)
        setMessages((prev) => [
          ...prev,
          {
            id: nextMsgId.current++,
            kind: "user",
            isUser: true,
            text: `Image: ${file.name}`,
            mediaType: "image",
            mediaUrl: imageUrl,
            fileName: file.name,
          },
        ])

        const form = new FormData()
        form.append("file", file)
        if (selectedModel) form.append("model", selectedModel)

        const res = await fetch(`${BASE_URL}/image/moderation/analyze`, {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
          body: form,
        })
        if (!res.ok) throw new Error("Erreur pendant l'analyse image")
        const data = await res.json()

        // Utiliser directement la structure JSON retournée par le backend
        const compatibility = data.youtube_compatibility || {}
        const status = compatibility.compatible ? "conforme" : "non_conforme"
        const reasoning = compatibility.commentaire || "Analyse image terminée"

        setMessages((prev) => [
          ...prev,
          {
            id: nextMsgId.current++,
            isUser: false,
            kind: "analysis",
            status,
            category: "image",
            reasoning,
            payload: data,
            expanded: false,
            showJson: false,
          },
        ])
      } catch (error) {
        setMessages((prev) => [
          ...prev,
          { id: nextMsgId.current++, isUser: false, kind: "error", text: error?.message || "Erreur image" },
        ])
        console.error(error)
      } finally {
        setIsLoading(false)
      }
    },
    [token, isLoading, selectedModel],
  )

  // Calculate compliance score based on analysis results
  const calculateComplianceScore = useCallback((msg) => {
    if (!msg.payload) return { score: 0, details: "Aucune donnée" }

    let totalScore = 0
    let maxScore = 0
    let details = []

    // Content moderation scoring (GROQ)
    const contentMod = msg.payload.content_moderation
    if (contentMod && contentMod.groq) {
      maxScore += 40
      const isCompliant = contentMod.groq.status === "conforme"
      const contentScore = isCompliant ? 40 : (contentMod.groq.is_insult === false ? 20 : 0)
      totalScore += contentScore
      details.push(`Contenu: ${contentScore}/40 pts ${isCompliant ? "✅" : "❌"}`)
    }

    // Audio moderation scoring
    const audioMod = msg.payload.audio_moderation
    if (audioMod) {
      maxScore += 60
      let audioScore = 0
      
      // Base publication allowance (30 pts)
      if (audioMod.can_publish) audioScore += 30
      details.push(`Publication: ${audioMod.can_publish ? "30/30" : "0/30"} pts ${audioMod.can_publish ? "✅" : "❌"}`)
      
      // Copyright analysis (20 pts)
      const copyright = audioMod.copyright_analysis
      if (copyright) {
        const copyrightScore = copyright.music_detected ? 
          (copyright.strike_risk_level === "critical" ? 0 : 
           copyright.strike_risk_level === "high" ? 5 : 
           copyright.strike_risk_level === "medium" ? 15 : 20) : 20
        audioScore += copyrightScore
        details.push(`Droits d'auteur: ${copyrightScore}/20 pts ${copyright.music_detected ? (copyright.strike_risk_level === "critical" || copyright.strike_risk_level === "high" ? "❌" : "⚠️") : "✅"}`)
      }
      
      // Lyrics analysis (10 pts)
      const lyrics = audioMod.lyrics_analysis
      if (lyrics) {
        const lyricsScore = lyrics.toxic ? 0 : (lyrics.status === "allowed" ? 10 : 5)
        audioScore += lyricsScore
        details.push(`Paroles: ${lyricsScore}/10 pts ${lyrics.toxic ? "❌" : lyrics.status === "allowed" ? "✅" : "⚠️"}`)
      }
      
      totalScore += audioScore
    }

    // Image analysis scoring
    const imageCompat = msg.payload.youtube_compatibility
    if (imageCompat && !contentMod && !audioMod) {
      maxScore += 100
      const imageScore = imageCompat.compatible ? 100 : 30
      totalScore += imageScore
      details.push(`Image YouTube: ${imageScore}/100 pts ${imageCompat.compatible ? "✅" : "❌"}`)
    }

    // Video analysis scoring
    const report = msg.payload.report
    if (report && !contentMod && !audioMod && !imageCompat) {
      maxScore += 100
      let videoScore = 0
      
      if (report.can_publish) videoScore += 50
      if (!report.summary?.toxic) videoScore += 30
      if (report.youtube_report?.compatible !== false) videoScore += 20
      
      totalScore += videoScore
      details.push(`Vidéo: ${videoScore}/100 pts ${report.can_publish ? "✅" : "❌"}`)
    }

    // Fallback for simple text analysis
    if (maxScore === 0) {
      maxScore = 100
      const isCompliant = msg.status === "conforme"
      totalScore = isCompliant ? 100 : 30
      details.push(`Analyse générale: ${totalScore}/100 pts ${isCompliant ? "✅" : "❌"}`)
    }

    const percentage = maxScore > 0 ? Math.round((totalScore / maxScore) * 100) : 0
    return { score: percentage, details: details.join(" • ") }
  }, [])

  // UI helpers for analysis messages
  const formatAnalysisPlain = useCallback((msg) => {
    const lines = []
    const audioMod = msg.payload?.audio_moderation
    const contentMod = msg.payload?.content_moderation

    // Content moderation (text analysis) - show only structured format
    if (contentMod && contentMod.groq) {
      const groq = contentMod.groq
      const isCompliant = groq.status === "conforme"
      
      lines.push(`${isCompliant ? "✅" : "❌"} Contenu ${isCompliant ? "compatible" : "non compatible"}`)
      
      if (groq.reasoning) {
        lines.push("")
        lines.push("Raison:")
        lines.push(groq.reasoning)
      }
      
      if (groq.category && groq.category !== "aucun") {
        lines.push("")
        lines.push(`📋 Catégorie: ${groq.category}`)
      }
      
      if (groq.is_insult !== undefined) {
        lines.push(`🚫 Insulte détectée: ${groq.is_insult ? "Oui" : "Non"}`)
      }
      
      // Continue to show audio analysis if present
    }

    // Audio moderation - show detailed analysis
    if (audioMod) {
      lines.push("")
      lines.push("🎧 Analyse audio:")
      lines.push(`• Statut: ${audioMod.status === "blocked" ? "❌ Bloqué" : "✅ Autorisé"}`)
      lines.push(`• Publication: ${audioMod.can_publish ? "✅ Autorisée" : "❌ Bloquée"}`)
      
      // Show main message if present
      if (audioMod.message) {
        lines.push("")
        lines.push("📢 Message:")
        lines.push(audioMod.message)
      }

      // Violated rules
      if (audioMod.violated_rules && audioMod.violated_rules.length > 0) {
        lines.push("")
        lines.push("Règles violées:")
        audioMod.violated_rules.forEach(rule => {
          lines.push(`• ${rule}`)
        })
      }

      // Lyrics analysis
      if (audioMod.lyrics_analysis) {
        const lyrics = audioMod.lyrics_analysis
        lines.push("")
        lines.push("📝 Analyse des paroles:")
        lines.push(`• Statut: ${lyrics.status === "allowed" ? "✅ Autorisé" : "❌ Bloqué"}`)
        lines.push(`• Contenu toxique: ${lyrics.toxic ? "❌ Oui" : "✅ Non"}`)
        if (lyrics.confidence > 0) {
          lines.push(`• Confiance: ${Math.round(lyrics.confidence * 100)}%`)
        }
        if (lyrics.flagged_text) {
          lines.push(`• Texte problématique: "${lyrics.flagged_text}"`)
        }
        if (lyrics.recommendation && lyrics.recommendation !== "Aucune action requise") {
          lines.push(`• Recommandation: ${lyrics.recommendation}`)
        }
      }

      // Copyright analysis
      if (audioMod.copyright_analysis) {
        const copyright = audioMod.copyright_analysis
        lines.push("")
        lines.push("🎵 Analyse des droits d'auteur:")
        lines.push(`• Musique détectée: ${copyright.music_detected ? "✅ Oui" : "❌ Non"}`)
        
        if (copyright.music_detected) {
          if (copyright.title) {
            const isParody = copyright.title.toLowerCase().includes('paródia') || 
                           copyright.title.toLowerCase().includes('parody') ||
                           copyright.title.toLowerCase().includes('remix') ||
                           copyright.title.toLowerCase().includes('cover')
            lines.push(`• Titre: ${copyright.title} ${isParody ? '🎭 (Parodie/Remix)' : ''}`)
          }
          if (copyright.artist) lines.push(`• Artiste: ${copyright.artist}`)
          if (copyright.album) lines.push(`• Album: ${copyright.album}`)
          if (copyright.release_date) lines.push(`• Date de sortie: ${copyright.release_date}`)
          
          const isHighRisk = copyright.copyright_protected || 
                           copyright.strike_risk_level === 'critical' || 
                           copyright.strike_risk_level === 'high' ||
                           copyright.confidence_score >= 0.85
          lines.push(`• Protégé par droits d'auteur: ${isHighRisk ? '🚨 Oui' : '✅ Non'}`)
          
          if (copyright.confidence_score !== undefined) {
            lines.push(`• Score de confiance: ${Math.round(copyright.confidence_score * 100)}%`)
          }
          
          if (copyright.strike_risk_level) {
            const riskEmoji = copyright.strike_risk_level === "critical" ? "🚨" : 
                             copyright.strike_risk_level === "high" ? "⚠️" : 
                             copyright.strike_risk_level === "medium" ? "⚡" : "✅"
            lines.push(`• Risque de strike: ${riskEmoji} ${copyright.strike_risk_level}`)
          }
          
          if (copyright.recommendation) {
            lines.push("")
            lines.push("💡 Recommandation:")
            lines.push(copyright.recommendation)
          }
        }
      }

      // Copyrighted segment
      if (audioMod.copyrighted_segment) {
        const segment = audioMod.copyrighted_segment
        lines.push("")
        lines.push("⏱️ Segment problématique:")
        lines.push(`• Temps: ${segment.start_time || "0s"} - ${segment.end_time || "fin"}`)
        if (segment.offset_ms !== undefined) {
          lines.push(`• Décalage: ${segment.offset_ms}ms`)
        }

      }

      // Automatic action
      if (audioMod.automatic_action) {
        lines.push("")
        lines.push(` Action automatique: ${audioMod.automatic_action === "block" ? "❌ Bloqué" : "✅ Autorisé"}`)
      }
    }

    // Image analysis - show structured JSON data
    if (!contentMod && !audioMod && msg.category === "image" && msg.payload?.youtube_compatibility) {
      const compatibility = msg.payload.youtube_compatibility
      
      lines.push("🖼️ Analyse d'image:")
      lines.push(`• Compatible YouTube: ${compatibility.compatible ? "✅ Oui" : "❌ Non"}`)
      
      if (compatibility.commentaire) {
        lines.push("")
        lines.push("📋 Détails de l'analyse:")
        lines.push(compatibility.commentaire)
      }
    
    }
    // Fallback for other content types without specific moderation data
    else if (!contentMod && !audioMod) {
      const isCompatible = msg.payload?.can_publish !== false && (msg.status || "").toLowerCase() === "conforme"

      if (isCompatible) {
        lines.push("Votre contenu peut être publié sans problème.")
      } else {
        lines.push("❌ Contenu non compatible")

        if (msg.reasoning) {
          lines.push("")
          lines.push("Raison:")
          lines.push(msg.reasoning)
        }
      }
    }

    return lines.join("\n")
  }, [])
  
  const toggleReasoning = useCallback((id) => {
    setMessages((prev) => prev.map((m) => (m.id === id ? { ...m, expanded: !m.expanded } : m)))
  }, [])

  const toggleJson = useCallback((id) => {
    setMessages((prev) => prev.map((m) => (m.id === id ? { ...m, showJson: !m.showJson } : m)))
  }, [])

  const formatAnalysisRich = useCallback(
    (msg) => {
      const report = msg.payload?.report
      if (!report) return null

      return (
        <div className="space-y-6">
          {/* Analysis Summary */}
          <div
            className={`p-4 rounded-xl border ${darkMode ? "bg-gray-800/50 border-gray-700" : "bg-gray-50 border-gray-200"}`}
          >
            <div className="flex items-center gap-3 mb-3">
              <div className={`w-3 h-3 rounded-full ${report.can_publish ? "bg-green-500" : "bg-red-500"}`}></div>
              <h3 className={`font-semibold ${darkMode ? "text-white" : "text-gray-900"}`}>
                Statut: {report.can_publish ? "Autorisé" : "Bloqué"}
              </h3>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div>
                <span className={`block ${darkMode ? "text-gray-400" : "text-gray-600"}`}>Images analysées</span>
                <span className={`font-medium ${darkMode ? "text-white" : "text-gray-900"}`}>
                  {report.summary?.frames_analyzed || 0}
                </span>
              </div>
              <div>
                <span className={`block ${darkMode ? "text-gray-400" : "text-gray-600"}`}>Violations</span>
                <span className={`font-medium ${darkMode ? "text-white" : "text-gray-900"}`}>
                  {report.summary?.violations_count || 0}
                </span>
              </div>
              <div>
                <span className={`block ${darkMode ? "text-gray-400" : "text-gray-600"}`}>Toxique</span>
                <span className={`font-medium ${report.summary?.toxic ? "text-red-500" : "text-green-500"}`}>
                  {report.summary?.toxic ? "Oui" : "Non"}
                </span>
              </div>
              <div>
                <span className={`block ${darkMode ? "text-gray-400" : "text-gray-600"}`}>YouTube</span>
                <span
                  className={`font-medium ${
                    report.youtube_report?.compatible !== false && !report.copyright_analysis?.copyright_detected
                      ? "text-green-500"
                      : "text-red-500"
                  }`}
                >
                  {report.youtube_report?.compatible !== false && !report.copyright_analysis?.copyright_detected
                    ? "Compatible"
                    : "Non compatible"}
                </span>
              </div>
            </div>
          </div>

          {/* Copyright Analysis */}
          {report.copyright_analysis && (
            <div
              className={`p-4 rounded-xl border ${darkMode ? "bg-gray-800/50 border-gray-700" : "bg-gray-50 border-gray-200"}`}
            >
              <div className="flex items-center gap-3 mb-3">
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center ${
                    report.copyright_analysis.copyright_detected
                      ? "bg-red-100 text-red-600"
                      : "bg-green-100 text-green-600"
                  }`}
                >
                  {report.copyright_analysis.copyright_detected ? "⚠️" : "✅"}
                </div>
                <h3 className={`font-semibold ${darkMode ? "text-white" : "text-gray-900"}`}>
                  Analyse des droits d'auteur
                </h3>
              </div>

              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className={`${darkMode ? "text-gray-400" : "text-gray-600"}`}>Statut</span>
                  <span
                    className={`font-medium px-3 py-1 rounded-full text-sm ${
                      report.copyright_analysis.copyright_detected
                        ? "bg-red-100 text-red-700"
                        : "bg-green-100 text-green-700"
                    }`}
                  >
                    {report.copyright_analysis.copyright_detected ? "Détecté" : "Libre"}
                  </span>
                </div>

                <div className="flex items-center justify-between">
                  <span className={`${darkMode ? "text-gray-400" : "text-gray-600"}`}>Risque de strike</span>
                  <span
                    className={`font-medium px-3 py-1 rounded-full text-sm ${
                      report.copyright_analysis.strike_risk_level === "low"
                        ? "bg-green-100 text-green-700"
                        : report.copyright_analysis.strike_risk_level === "medium"
                          ? "bg-yellow-100 text-yellow-700"
                          : "bg-red-100 text-red-700"
                    }`}
                  >
                    {report.copyright_analysis.strike_risk_level || "Faible"}
                  </span>
                </div>

                {report.copyright_analysis.recommendation && (
                  <div className={`p-3 rounded-lg ${darkMode ? "bg-gray-700/50" : "bg-white"}`}>
                    <p className={`text-sm ${darkMode ? "text-gray-300" : "text-gray-700"}`}>
                      {report.copyright_analysis.recommendation}
                    </p>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* YouTube Report */}
          {report.youtube_report && (
            <div
              className={`p-4 rounded-xl border ${darkMode ? "bg-gray-800/50 border-gray-700" : "bg-gray-50 border-gray-200"}`}
            >
              <div className="flex items-center gap-3 mb-3">
                <div className="w-8 h-8 rounded-full bg-red-100 flex items-center justify-center">
                  <span className="text-red-600 font-bold text-sm">YT</span>
                </div>
                <h3 className={`font-semibold ${darkMode ? "text-white" : "text-gray-900"}`}>Rapport YouTube</h3>
              </div>

              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className={`${darkMode ? "text-gray-400" : "text-gray-600"}`}>Niveau de risque</span>
                  <span
                    className={`font-medium px-3 py-1 rounded-full text-sm ${
                      report.youtube_report.risk_level === "none"
                        ? "bg-green-100 text-green-700"
                        : report.youtube_report.risk_level === "low"
                          ? "bg-yellow-100 text-yellow-700"
                          : "bg-red-100 text-red-700"
                    }`}
                  >
                    {report.youtube_report.risk_level === "none" ? "Aucun" : report.youtube_report.risk_level}
                  </span>
                </div>

                {report.youtube_report.youtube_advice && report.youtube_report.youtube_advice.length > 0 && (
                  <div>
                    <h4 className={`font-medium mb-2 ${darkMode ? "text-white" : "text-gray-900"}`}>Conseils</h4>
                    <div className="space-y-1">
                      {report.youtube_report.youtube_advice.map((advice, idx) => (
                        <div key={idx} className={`text-sm ${darkMode ? "text-gray-300" : "text-gray-700"}`}>
                          {advice}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )
    },
    [darkMode],
  )

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
          className={`w-full flex items-center justify-center gap-3 px-6 py-4 mb-6 rounded-full font-semibold bg-gradient-to-r from-pink-500 to-red-500 hover:brightness-110 text-white transition-all duration-200 shadow-lg hover:shadow-xl transform hover:scale-[1.02]`}
          aria-label="Nouvelle Analyse"
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

        {/* User Profile Display - Always show avatar */}
        <div
          className={`flex items-center gap-3 mt-6 p-4 rounded-2xl backdrop-blur-sm
        ${darkMode ? "bg-gray-800/30 border border-gray-700/50" : "bg-white/60 border border-gray-200"}`}
        >
          <div className="w-12 h-12 rounded-full overflow-hidden bg-white/10 backdrop-blur-sm flex items-center justify-center border-2 border-pink-500">
            <img 
              src="/default-avatar1.png" 
              alt="Avatar"
              className="w-10 h-10 object-cover"
              onError={() => {
                console.log("Avatar load error - image not found")
              }}
            />
          </div>
          <div>
            <p className={`font-semibold text-sm ${darkMode ? "text-white" : "text-gray-900"}`}>
              {currentUser?.username || "Utilisateur"}
            </p>
            <p className={`text-xs ${darkMode ? "text-gray-400" : "text-gray-500"}`}>Utilisateur ContentGuard</p>
          </div>
        </div>
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
                <img
                  src="/default-avatar1.png"
                  alt="User profile"
                  className="w-10 h-10 rounded-full object-cover border-2 border-pink-500"
                />
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
                    <img
                      src={currentUser.photo || "/default-avatar1.png"}
                      alt="User profile"
                      className="w-10 h-10 rounded-full object-cover border-2 border-pink-500"
                    />
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
                    Profile
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

          {messages.map((msg, idx) => {
            // User message
            if (msg.kind === "user") {
              return (
                <div
                  key={`${msg.id ?? "m"}-${idx}`}
                  className="max-w-4xl px-6 py-4 rounded-3xl whitespace-pre-wrap break-words shadow-lg transition-all duration-200 bg-gradient-to-r from-pink-500 to-red-500 text-white self-end ml-auto"
                >
                  {msg.mediaType && msg.mediaUrl ? (
                    <div className="space-y-3">
                      <div className="text-sm opacity-90">{msg.fileName}</div>
                      {msg.mediaType === "image" && (
                        <img
                          src={msg.mediaUrl || "/placeholder.svg"}
                          alt={msg.fileName}
                          className="max-w-full max-h-64 rounded-lg object-contain"
                        />
                      )}
                      {msg.mediaType === "video" && (
                        <video src={msg.mediaUrl} controls className="max-w-full max-h-64 rounded-lg">
                          Votre navigateur ne supporte pas la lecture vidéo.
                        </video>
                      )}
                      {msg.mediaType === "audio" && (
                        <audio src={msg.mediaUrl} controls className="w-full">
                          Votre navigateur ne supporte pas la lecture audio.
                        </audio>
                      )}
                    </div>
                  ) : (
                    msg.text
                  )}
                </div>
              )
            }

            // Error message
            if (msg.kind === "error") {
              return (
                <div
                  key={`${msg.id ?? "m"}-${idx}`}
                  className={`max-w-4xl px-6 py-4 rounded-3xl shadow-lg self-start border ${
                    darkMode ? "bg-gray-800/30 text-red-300 border-red-800/50" : "bg-red-50 text-red-700 border-red-200"
                  }`}
                >
                  ⚠️ {msg.text}
                </div>
              )
            }

            // Analysis message (rich card)
            if (msg.kind === "analysis") {
              const textBase = darkMode ? "text-white" : "text-gray-900"
              const subText = darkMode ? "text-gray-300" : "text-gray-600"
              const plain = formatAnalysisPlain(msg)
              const richContent = formatAnalysisRich(msg)
              const scoreData = calculateComplianceScore(msg)

              // Score color based on percentage
              const getScoreColor = (score) => {
                if (score >= 80) return "text-green-500"
                if (score >= 60) return "text-yellow-500"
                if (score >= 40) return "text-orange-500"
                return "text-red-500"
              }

              const getScoreBg = (score) => {
                if (score >= 80) return "bg-green-500/20 border-green-500/30"
                if (score >= 60) return "bg-yellow-500/20 border-yellow-500/30"
                if (score >= 40) return "bg-orange-500/20 border-orange-500/30"
                return "bg-red-500/20 border-red-500/30"
              }

              return (
                <div
                  key={`${msg.id ?? "m"}-${idx}`}
                  className={`max-w-4xl px-6 py-5 rounded-3xl self-start shadow-lg border backdrop-blur-sm ${
                    darkMode ? "bg-gray-800/30 border-gray-700/50 text-white" : "bg-white border-gray-200 text-gray-900"
                  }`}
                >
                  {/* Compliance Score Header */}
                  <div className={`flex items-center justify-between mb-4 p-3 rounded-xl border ${getScoreBg(scoreData.score)}`}>
                    <div className="flex items-center gap-3">
                      <div className={`text-2xl font-bold ${getScoreColor(scoreData.score)}`}>
                        {scoreData.score}%
                      </div>
                      <div>
                        <div className={`font-semibold ${textBase}`}>
                          Score de conformité
                        </div>
                        <div className={`text-sm ${subText}`}>
                          {scoreData.score >= 80 ? "Excellent" : 
                           scoreData.score >= 60 ? "Bon" : 
                           scoreData.score >= 40 ? "Moyen" : "Faible"}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {scoreData.score >= 80 && <span className="text-2xl">🎉</span>}
                      {scoreData.score >= 60 && scoreData.score < 80 && <span className="text-2xl">👍</span>}
                      {scoreData.score >= 40 && scoreData.score < 60 && <span className="text-2xl">⚠️</span>}
                      {scoreData.score < 40 && <span className="text-2xl">❌</span>}
                    </div>
                  </div>

                  {/* Score Details */}
                  <div className={`text-xs mb-4 p-2 rounded-lg ${darkMode ? "bg-gray-700/30" : "bg-gray-100/50"} ${subText}`}>
                    📊 Détail du score: {scoreData.details}
                  </div>

                  {richContent ? (
                    richContent
                  ) : (
                    <pre className={`${textBase} whitespace-pre-wrap break-words`}>{plain}</pre>
                  )}

                  <div className="mt-3 flex items-center gap-3">
                    <button
                      onClick={() => toggleJson(msg.id)}
                      className={`text-sm px-3 py-1.5 rounded-full border transition-colors ${
                        darkMode
                          ? "border-gray-600 text-gray-200 hover:bg-gray-700"
                          : "border-gray-300 text-gray-700 hover:bg-gray-100"
                      }`}
                    >
                      {msg.showJson ? "Masquer le JSON" : "Voir le JSON brut"}
                    </button>
                    {msg.payload?.groq?.model && (
                      <span className={`text-xs ${subText}`}>Modèle: {msg.payload.groq.model || "-"}</span>
                    )}
                  </div>
                  {msg.showJson && (
                    <pre
                      className={`mt-3 p-3 rounded-xl overflow-auto text-xs ${
                        darkMode ? "bg-black/40 text-gray-200" : "bg-gray-50 text-gray-800"
                      }`}
                      style={{ maxHeight: 320 }}
                    >
                      {JSON.stringify(msg.payload, null, 2)}
                    </pre>
                  )}
                </div>
              )
            }

            // Fallback generic
            return (
              <div
                key={`${msg.id ?? "m"}-${idx}`}
                className={`max-w-4xl px-6 py-4 rounded-3xl whitespace-pre-wrap break-words shadow-lg self-start border ${
                  darkMode ? "bg-gray-800/30 text-white border-gray-700/50" : "bg-white text-gray-900 border-gray-200"
                }`}
              >
                {msg.text}
              </div>
            )
          })}
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
            <input ref={audioInputRef} type="file" accept="audio/*" className="hidden" onChange={handleUploadAudio} />
            <input ref={imageInputRef} type="file" accept="image/*" className="hidden" onChange={handleUploadImage} />
            <input ref={videoInputRef} type="file" accept="video/*" className="hidden" onChange={handleUploadVideo} />
            <button
              type="button"
              onClick={handlePickAudio}
              disabled={isLoading}
              className={`rounded-full px-4 py-3 font-semibold border transition-colors hidden sm:block ${
                darkMode
                  ? "border-gray-600 text-gray-200 hover:bg-gray-700"
                  : "border-gray-300 text-gray-700 hover:bg-gray-100"
              }`}
              title="Analyser un fichier audio"
            >
              Audio
            </button>
            <button
              type="button"
              onClick={handlePickImage}
              disabled={isLoading}
              className={`rounded-full px-4 py-3 font-semibold border transition-colors hidden sm:block ${
                darkMode
                  ? "border-gray-600 text-gray-200 hover:bg-gray-700"
                  : "border-gray-300 text-gray-700 hover:bg-gray-100"
              }`}
              title="Analyser une image"
            >
              Image
            </button>
            <button
              type="button"
              onClick={handlePickVideo}
              disabled={isLoading}
              className={`rounded-full px-4 py-3 font-semibold border transition-colors hidden sm:block ${
                darkMode
                  ? "border-gray-600 text-gray-200 hover:bg-gray-700"
                  : "border-gray-300 text-gray-700 hover:bg-gray-100"
              }`}
              title="Analyser une vidéo"
            >
              Vidéo
            </button>
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
