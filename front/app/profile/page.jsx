"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { User, Mail, Calendar, Shield, ArrowLeft, Edit3, Save, X, BarChart3, CheckCircle, XCircle } from "lucide-react"

const BASE_URL = "http://localhost:8000"

export default function Profile() {
  const router = useRouter()
  const [user, setUser] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isEditing, setIsEditing] = useState(false)
  const [editForm, setEditForm] = useState({
    username: "",
    email: "",
    password: "",
    confirmPassword: ""
  })
  const [isSaving, setIsSaving] = useState(false)
  const [message, setMessage] = useState("")
  const [stats, setStats] = useState({
    total_analyses: 0,
    approved_content: 0,
    blocked_content: 0,
    analyses_by_type: { text: 0, audio: 0, image: 0, video: 0 }
  })

  useEffect(() => {
    fetchUserData()
    fetchUserStats()
    
    // Vérifier si on doit ouvrir en mode édition
    const urlParams = new URLSearchParams(window.location.search)
    if (urlParams.get('edit') === 'true') {
      setIsEditing(true)
    }
  }, [])

  const fetchUserData = async () => {
    try {
      const token = localStorage.getItem("token")
      if (!token) {
        router.push("/login")
        return
      }

      const response = await fetch(`${BASE_URL}/api/users/users/me`, {
        headers: {
          "Authorization": `Bearer ${token}`,
          "Content-Type": "application/json"
        }
      })

      if (response.ok) {
        const userData = await response.json()
        setUser(userData)
        setEditForm({
          username: userData.username || "",
          email: userData.email || "",
          password: "",
          confirmPassword: ""
        })
      } else if (response.status === 401) {
        localStorage.removeItem("token")
        router.push("/login")
      }
    } catch (error) {
      console.error("Erreur lors du chargement du profil:", error)
    } finally {
      setIsLoading(false)
    }
  }

  const handleSaveProfile = async () => {
    setIsSaving(true)
    setMessage("")

    // Validation des mots de passe
    if (editForm.password && editForm.password !== editForm.confirmPassword) {
      setMessage("Les mots de passe ne correspondent pas")
      setIsSaving(false)
      return
    }
    
    try {
      const token = localStorage.getItem("token")
      const updateData = {
        username: editForm.username,
        email: editForm.email
      }
      
      // Ajouter le mot de passe seulement s'il est fourni
      if (editForm.password) {
        updateData.password = editForm.password
      }
      
      const response = await fetch(`${BASE_URL}/api/users/users/me`, {
        method: "PUT",
        headers: {
          "Authorization": `Bearer ${token}`,
          "Content-Type": "application/json"
        },
        body: JSON.stringify(updateData)
      })

      if (response.ok) {
        const updatedUser = await response.json()
        setUser(updatedUser)
        setIsEditing(false)
        setEditForm({...editForm, password: "", confirmPassword: ""})
        setMessage("Profil mis à jour avec succès !")
        setTimeout(() => setMessage(""), 3000)
      } else {
        const error = await response.json()
        setMessage(`Erreur: ${error.detail || "Impossible de mettre à jour le profil"}`)
      }
    } catch (error) {
      console.error("Erreur lors de la sauvegarde:", error)
      setMessage("Erreur de connexion")
    } finally {
      setIsSaving(false)
    }
  }

  const fetchUserStats = async () => {
    try {
      const token = localStorage.getItem("token")
      if (!token) return

      // Récupérer l'historique des analyses depuis l'API existante
      const response = await fetch(`${BASE_URL}/moderation/history`, {
        headers: {
          "Authorization": `Bearer ${token}`,
          "Content-Type": "application/json"
        }
      })

      if (response.ok) {
        const historyData = await response.json()
        
        // Calculer les statistiques depuis l'historique
        const total = historyData.length
        let approved = 0
        let blocked = 0
        const typeCount = { text: 0, audio: 0, image: 0, video: 0 }
        
        historyData.forEach(item => {
          // Debug: voir la structure des données
          console.log("Item historique:", item)
          
          // Utiliser le champ type de la DB ou détecter depuis le contenu
          let itemType = item.type || "texte" // valeur par défaut de la DB
          
          // Normaliser les noms de types pour l'affichage
          if (itemType === "texte") itemType = "text"
          
          typeCount[itemType] = (typeCount[itemType] || 0) + 1
          
          // Compter approuvés/bloqués selon le champ toxic
          if (item.toxic === false) {
            approved++
          } else if (item.toxic === true) {
            blocked++
          }
        })
        
        setStats({
          total_analyses: total,
          approved_content: approved,
          blocked_content: blocked,
          analyses_by_type: typeCount
        })
      }
    } catch (error) {
      console.error("Erreur lors du chargement des statistiques:", error)
    }
  }

  const handleCancelEdit = () => {
    setIsEditing(false)
    setEditForm({
      username: user?.username || "",
      email: user?.email || "",
      full_name: user?.full_name || ""
    })
    setMessage("")
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#0f1123] flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-pink-500"></div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-[#0f1123] text-white">
      {/* Header */}
      <div className="bg-[#1a1f3a] shadow-sm border-b border-gray-700">
        <div className="max-w-4xl mx-auto px-6 py-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <button
                onClick={() => router.push("/chat")}
                className="p-2 rounded-lg hover:bg-gray-700 transition-colors"
              >
                <ArrowLeft className="h-5 w-5 text-gray-300" />
              </button>
              <h1 className="text-2xl font-bold text-white">
                Mon Profil
              </h1>
            </div>

          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-4xl mx-auto px-6 py-8">
        {message && (
          <div className={`mb-6 p-4 rounded-lg ${
            message.includes("succès") 
              ? "bg-green-900/20 text-green-400 border border-green-500/30" 
              : "bg-red-900/20 text-red-400 border border-red-500/30"
          }`}>
            {message}
          </div>
        )}

        <div className="bg-[#1a1f3a] rounded-xl shadow-lg overflow-hidden border border-gray-700">
          {/* Profile Header */}
          <div className="bg-gradient-to-r from-pink-500 to-red-500 px-6 py-8">
            <div className="flex items-center space-x-4">
              <div className="w-20 h-20 rounded-full overflow-hidden bg-white/10 backdrop-blur-sm flex items-center justify-center">
                <img 
                  src="/default-avatar1.png" 
                  alt="Devaktus Logo"
                  className="w-16 h-16 object-contain"
                />
              </div>
              <div className="text-white">
                <h2 className="text-2xl font-bold">{user?.full_name || user?.username || "Utilisateur"}</h2>
                <p className="text-pink-100">@{user?.username}</p>
              </div>
            </div>
          </div>

          {/* Profile Details */}
          <div className="p-6">
            {isEditing ? (
              <div className="space-y-6">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Nom d'utilisateur
                  </label>
                  <input
                    type="text"
                    value={editForm.username}
                    onChange={(e) => setEditForm({...editForm, username: e.target.value})}
                    className="w-full px-4 py-3 bg-[#3b4a6b] border border-gray-600 rounded-full focus:ring-2 focus:ring-pink-500 text-white placeholder-white/50"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Mot de passe
                  </label>
                  <input
                    type="password"
                    value={editForm.password}
                    onChange={(e) => setEditForm({...editForm, password: e.target.value})}
                    className="w-full px-4 py-3 bg-[#3b4a6b] border border-gray-600 rounded-full focus:ring-2 focus:ring-pink-500 text-white placeholder-white/50"
                    placeholder="Nouveau mot de passe"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Confirmer le mot de passe
                  </label>
                  <input
                    type="password"
                    value={editForm.confirmPassword}
                    onChange={(e) => setEditForm({...editForm, confirmPassword: e.target.value})}
                    className="w-full px-4 py-3 bg-[#3b4a6b] border border-gray-600 rounded-full focus:ring-2 focus:ring-pink-500 text-white placeholder-white/50"
                    placeholder="Confirmer le mot de passe"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Email
                  </label>
                  <input
                    type="email"
                    value={editForm.email}
                    onChange={(e) => setEditForm({...editForm, email: e.target.value})}
                    className="w-full px-4 py-3 bg-[#3b4a6b] border border-gray-600 rounded-full focus:ring-2 focus:ring-pink-500 text-white placeholder-white/50"
                  />
                </div>

                <div className="flex space-x-3">
                  <button
                    onClick={handleSaveProfile}
                    disabled={isSaving}
                    className="flex items-center space-x-2 px-6 py-3 bg-gradient-to-r from-green-500 to-green-600 text-white rounded-full hover:brightness-110 disabled:opacity-50 transition-all"
                  >
                    <Save className="h-4 w-4" />
                    <span>{isSaving ? "Sauvegarde..." : "Sauvegarder"}</span>
                  </button>
                  <button
                    onClick={handleCancelEdit}
                    className="flex items-center space-x-2 px-6 py-3 bg-gray-600 text-white rounded-full hover:bg-gray-700 transition-colors"
                  >
                    <X className="h-4 w-4" />
                    <span>Annuler</span>
                  </button>
                </div>
              </div>
            ) : (
              <div className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="flex items-center space-x-3 p-4 bg-[#3b4a6b] rounded-lg">
                    <User className="h-5 w-5 text-blue-400" />
                    <div>
                      <p className="text-sm text-gray-400">Nom d'utilisateur</p>
                      <p className="font-medium text-white">{user?.username}</p>
                    </div>
                  </div>

                  <div className="flex items-center space-x-3 p-4 bg-[#3b4a6b] rounded-lg">
                    <Mail className="h-5 w-5 text-green-400" />
                    <div>
                      <p className="text-sm text-gray-400">Email</p>
                      <p className="font-medium text-white">{user?.email}</p>
                    </div>
                  </div>

                  <div className="flex items-center space-x-3 p-4 bg-[#3b4a6b] rounded-lg">
                    <Calendar className="h-5 w-5 text-purple-400" />
                    <div>
                      <p className="text-sm text-gray-400">Membre depuis</p>
                      <p className="font-medium text-white">
                        {user?.created_at ? new Date(user.created_at).toLocaleDateString('fr-FR') : "N/A"}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center space-x-3 p-4 bg-[#3b4a6b] rounded-lg">
                    <Shield className="h-5 w-5 text-orange-400" />
                    <div>
                      <p className="text-sm text-gray-400">Statut</p>
                      <p className="font-medium text-white">
                        {user?.role === "admin" ? "Administrateur" : "Utilisateur"}
                      </p>
                    </div>
                  </div>
                </div>

                {user?.full_name && (
                  <div className="p-4 bg-[#3b4a6b] rounded-lg">
                    <p className="text-sm text-gray-400">Nom complet</p>
                    <p className="font-medium text-white">{user.full_name}</p>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Statistics Section */}
        <div className="mt-8 bg-[#1a1f3a] rounded-xl shadow-lg p-6 border border-gray-700">
          <div className="flex items-center space-x-2 mb-6">
            <BarChart3 className="h-5 w-5 text-pink-400" />
            <h3 className="text-lg font-semibold text-white">
              Statistiques d'utilisation
            </h3>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <div className="text-center p-4 bg-blue-500/10 rounded-lg border border-blue-500/30">
              <p className="text-2xl font-bold text-blue-400">
                {stats.total_analyses}
              </p>
              <p className="text-sm text-gray-400">Analyses totales</p>
            </div>
            <div className="text-center p-4 bg-green-500/10 rounded-lg border border-green-500/30">
              <div className="flex items-center justify-center space-x-1 mb-1">
                <CheckCircle className="h-4 w-4 text-green-400" />
                <p className="text-2xl font-bold text-green-400">
                  {stats.approved_content}
                </p>
              </div>
              <p className="text-sm text-gray-400">Contenus approuvés</p>
            </div>
            <div className="text-center p-4 bg-red-500/10 rounded-lg border border-red-500/30">
              <div className="flex items-center justify-center space-x-1 mb-1">
                <XCircle className="h-4 w-4 text-red-400" />
                <p className="text-2xl font-bold text-red-400">
                  {stats.blocked_content}
                </p>
              </div>
              <p className="text-sm text-gray-400">Contenus bloqués</p>
            </div>
          </div>
          
          {/* Analyses by type */}
        </div>
      </div>
    </div>
  )
}
