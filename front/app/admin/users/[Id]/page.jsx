"use client"

import { useState, useEffect } from "react"
import { useParams, useRouter } from "next/navigation"
import Link from "next/link"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { ArrowLeft, Edit, Trash2, History, Info } from "lucide-react"
import AdminLayout from "@/components/admin_layout"

export default function UserDetailPage() {
  const params = useParams()
  const router = useRouter()
  const userId = params?.Id

  const [user, setUser] = useState(null)
  const [moderationHistory, setModerationHistory] = useState([])
  const [selectedDetail, setSelectedDetail] = useState(null)
  const [loading, setLoading] = useState(true)
  const [loadingDetail, setLoadingDetail] = useState(false)

  useEffect(() => {
    if (userId) {
      const fetchData = async () => {
        setLoading(true)
        await Promise.all([fetchUser(userId), fetchModerationHistory(userId)])
        setLoading(false)
      }
      fetchData()
    } else {
      setLoading(false)
    }
  }, [userId])

  const fetchUser = async (id) => {
    try {
      const response = await fetch(`http://localhost:8000/admin/users/${id}`, {
        headers: { Authorization: `Bearer ${localStorage.getItem("token")}` },
      })
      if (!response.ok) throw new Error("Failed to fetch user")
      const data = await response.json()
      setUser(data)
    } catch {
      setUser({
        id: Number.parseInt(id),
        username: "john_doe",
        email: "john@example.com",
        role: "user",
        created_at: "2024-01-15T10:30:00Z",
        photo: "/placeholder.svg",
      })
    }
  }

  const fetchModerationHistory = async (id) => {
    try {
      const response = await fetch(`http://localhost:8000/admin/moderation/history/${id}`, {
        headers: { Authorization: `Bearer ${localStorage.getItem("token")}` },
      })
      if (!response.ok) throw new Error("Failed to fetch moderation history")
      const data = await response.json()
      setModerationHistory(data)
    } catch {
      setModerationHistory([])
    }
  }

  const fetchModerationDetail = async (analysisId) => {
    setLoadingDetail(true)
    try {
      const response = await fetch(
        `http://localhost:8000/admin/moderation/history/${userId}/${analysisId}`,
        {
          headers: { Authorization: `Bearer ${localStorage.getItem("token")}` },
        }
      )
      if (!response.ok) throw new Error("Failed to fetch moderation detail")
      const data = await response.json()
      let parsedResponse
      try {
        parsedResponse = JSON.parse(data.response)
      } catch {
        parsedResponse = { raw: data.response }
      }
      setSelectedDetail({ ...data, parsedResponse })
    } catch {
      setSelectedDetail(null)
    } finally {
      setLoadingDetail(false)
    }
  }

  const handleDeleteUser = async () => {
    if (!confirm("Are you sure you want to delete this user?")) return
    try {
      const token = localStorage.getItem("token")
      const response = await fetch(`http://localhost:8000/admin/users/${userId}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!response.ok) throw new Error("Failed to delete user")
      router.push("/admin/users")
    } catch {
      alert("Failed to delete user.")
    }
  }

  const formatDate = (dateString) =>
    new Date(dateString).toLocaleDateString("en-US", {
      year: "numeric",
      month: "long",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    })

  if (loading) {
    return (
      <AdminLayout>
        <div className="flex items-center justify-center h-64">
          <div className="text-lg animate-pulse text-gray-600">Loading user details...</div>
        </div>
      </AdminLayout>
    )
  }

  if (!user) {
    return (
      <AdminLayout>
        <div className="text-center py-16">
          <h2 className="text-2xl font-bold text-gray-900">User not found</h2>
          <p className="text-gray-600 mt-2">The user you're looking for doesn't exist.</p>
          <Link href="/admin/users">
            <Button className="mt-6 rounded-xl shadow-md">Back to Users</Button>
          </Link>
        </div>
      </AdminLayout>
    )
  }

  return (
    <AdminLayout>
      <div className="space-y-8">
        {/* Header */}
        <div className="flex items-center justify-between bg-white/70 backdrop-blur-md p-4 rounded-2xl shadow-sm">
          <div className="flex items-center space-x-4">
            <Link href="/admin/users">
              <Button variant="ghost" size="sm" className="rounded-xl">
                <ArrowLeft className="h-4 w-4 mr-2" />
                Back
              </Button>
            </Link>
            <div>
              <h1 className="text-3xl font-extrabold text-gray-900">User Details</h1>
              <p className="text-gray-500 text-sm">View and manage user information</p>
            </div>
          </div>
          <div className="flex space-x-3">
            <Link href={`/admin/users/${user.id}/edit`}>
              <Button variant="outline" className="rounded-xl">
                <Edit className="h-4 w-4 mr-2" />
                Edit
              </Button>
            </Link>
            <Button variant="destructive" onClick={handleDeleteUser} className="rounded-xl">
              <Trash2 className="h-4 w-4 mr-2" />
              Delete
            </Button>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* User Info */}
          <Card className="lg:col-span-1 shadow-xl border-0 rounded-2xl bg-white/80 backdrop-blur">
            <CardHeader>
              <CardTitle className="text-lg font-semibold">User Information</CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="text-center">
                <div className="h-28 w-28 mx-auto rounded-full bg-gray-100 shadow-inner flex items-center justify-center mb-4 overflow-hidden">
                  {user.photo ? (
                    <img src={user.photo} alt={user.username} className="h-28 w-28 object-cover" />
                  ) : (
                    <span className="text-2xl font-bold text-gray-600">
                      {user.username.charAt(0).toUpperCase()}
                    </span>
                  )}
                </div>
                <h3 className="text-lg font-bold">{user.username}</h3>
                <p className="text-gray-500">{user.email}</p>
              </div>
              <div className="space-y-3 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-600">Role:</span>
                  <Badge
                    variant={user.role === "admin" ? "default" : "secondary"}
                    className="rounded-lg px-3"
                  >
                    {user.role}
                  </Badge>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">User ID:</span>
                  <span className="font-medium">{user.id}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Created:</span>
                  <span className="font-medium">{formatDate(user.created_at)}</span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Moderation */}
          <Card className="lg:col-span-2 shadow-xl border-0 rounded-2xl bg-white/80 backdrop-blur">
            <CardHeader>
              <CardTitle className="flex items-center text-lg font-semibold">
                <History className="h-5 w-5 mr-2 text-gray-600" />
                Moderation
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                {/* History List */}
                <div>
                  <h3 className="font-semibold mb-3 text-gray-800">History</h3>
                  {moderationHistory.length === 0 ? (
                    <div className="text-center py-8 text-gray-400 italic">
                      No moderation history found.
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {moderationHistory.map((item) => (
                        <div
                          key={item.id}
                          className="flex items-center justify-between border rounded-xl px-4 py-3 hover:bg-gray-50 transition shadow-sm"
                        >
                          <div className="flex items-center space-x-3">
                            <span className="text-sm font-medium text-gray-700">ID: {item.id}</span>
                            <Badge variant="secondary" className="rounded-md text-xs px-2">
                              {item.type.toUpperCase()}
                            </Badge>
                          </div>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="rounded-lg"
                            onClick={() => fetchModerationDetail(item.id)}
                          >
                            <Info className="h-4 w-4 text-gray-600" />
                          </Button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Detail Panel */}
                <div>
                  <h3 className="font-semibold mb-3 text-gray-800">Detail</h3>
                  {loadingDetail ? (
                    <p className="text-gray-500">Loading details...</p>
                  ) : selectedDetail ? (
                    <div className="space-y-2 border rounded-xl p-4 bg-gray-50 shadow-inner">
                      <p><strong>ID:</strong> {selectedDetail.id}</p>
                      <p><strong>Question:</strong> {selectedDetail.question}</p>
                      <p><strong>Toxic:</strong> {selectedDetail.toxic ? "Yes" : "No"}</p>
                      <p><strong>Date:</strong> {formatDate(selectedDetail.date)}</p>
                      <div className="mt-3 p-2 bg-white rounded-lg border shadow-sm">
                        <pre className="text-xs whitespace-pre-wrap text-gray-700">
                          {JSON.stringify(selectedDetail.parsedResponse, null, 2)}
                        </pre>
                      </div>
                    </div>
                  ) : (
                    <p className="text-gray-400 italic">Click on ℹ️ to view details</p>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </AdminLayout>
  )
}
