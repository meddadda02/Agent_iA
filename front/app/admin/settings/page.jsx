"use client"

import { useState, useEffect } from "react"
import AdminLayout from "@/components/admin_layout"
import { Button } from "@/components/ui/button"

export default function SettingsPage() {
  const [user, setUser] = useState(null)
  const [formData, setFormData] = useState({ username: "", email: "" })
  const [photo, setPhoto] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")

  const token = typeof window !== "undefined" ? localStorage.getItem("token") : null

  useEffect(() => {
    async function fetchUser() {
      try {
        const res = await fetch("http://localhost:8000/api/users/users/me", {
          headers: { Authorization: `Bearer ${token}` },
        })
        if (!res.ok) {
          const text = await res.text()
          throw new Error(`Failed to fetch user: ${res.status} ${text}`)
        }
        const data = await res.json()
        setUser(data)
        setFormData({ username: data.username || "", email: data.email || "" })
      } catch (err) {
        console.error(err)
        setError("Failed to load user data")
      }
    }
    if (token) fetchUser()
  }, [token])

  const handleChange = (e) => setFormData({ ...formData, [e.target.name]: e.target.value })
  const handlePhotoChange = (e) => setPhoto(e.target.files[0])

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError("")

    try {
      const form = new FormData()
      form.append("username", formData.username)
      form.append("email", formData.email)
      if (photo) form.append("photo", photo)

      const res = await fetch("http://localhost:8000/api/users/users/me", {
        method: "PUT",
        headers: { Authorization: `Bearer ${token}` },
        body: form,
      })

      if (!res.ok) {
        const text = await res.text()
        throw new Error(`Failed to update user: ${res.status} ${text}`)
      }

      const updatedUser = await res.json()
      setUser(updatedUser)
      setFormData({ username: updatedUser.username || "", email: updatedUser.email || "" })
      setPhoto(null)
      alert("Profile updated successfully!")
    } catch (err) {
      console.error(err)
      setError("Failed to update profile")
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async () => {
    if (!confirm("Are you sure you want to delete your account?")) return

    try {
      const res = await fetch("http://localhost:8000/api/users/users/me", {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok) {
        const text = await res.text()
        throw new Error(`Failed to delete user: ${res.status} ${text}`)
      }
      alert("Account deleted successfully")
      localStorage.removeItem("token")
      window.location.href = "/login"
    } catch (err) {
      console.error(err)
      setError("Failed to delete account")
    }
  }

  const getInitial = (name) => name?.[0]?.toUpperCase() || "U"

  return (
    <AdminLayout>
      <div className="max-w-md mx-auto mt-10 relative">
        {/* Profile bubble */}
        <div className="absolute -top-12 left-1/2 transform -translate-x-1/2">
          {photo || user?.photo ? (
            <div className="w-24 h-24 rounded-full border-4 border-white shadow-lg overflow-hidden">
              <img
                src={photo ? URL.createObjectURL(photo) : user.photo}
                alt="Profile"
                className="w-full h-full object-cover"
              />
            </div>
          ) : (
            <div className="w-24 h-24 rounded-full border-4 border-white shadow-lg flex items-center justify-center bg-blue-500 text-white text-4xl font-bold">
              {getInitial(user?.username)}
            </div>
          )}
        </div>

        {/* Form Card */}
        <div className="bg-white p-8 rounded-2xl shadow-lg pt-20">
          {error && <p className="text-red-500 mb-4 text-center">{error}</p>}

          {!user ? (
            <p className="text-center text-gray-500">Loading user data...</p>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-gray-700">Username</label>
                <input
                  type="text"
                  name="username"
                  value={formData.username}
                  onChange={handleChange}
                  className="mt-2 block w-full border-gray-300 rounded-lg shadow-sm p-3 focus:ring-2 focus:ring-blue-400 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">Email</label>
                <input
                  type="email"
                  name="email"
                  value={formData.email}
                  onChange={handleChange}
                  className="mt-2 block w-full border-gray-300 rounded-lg shadow-sm p-3 focus:ring-2 focus:ring-blue-400 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">Change Profile Photo</label>
                <input type="file" onChange={handlePhotoChange} className="mt-2" />
                {photo && (
                  <p className="mt-2 text-sm text-gray-600">Selected file: {photo.name}</p>
                )}
              </div>

              <div className="flex justify-between items-center mt-6">
                <Button type="submit" className="px-6 py-3" disabled={loading}>
                  {loading ? "Updating..." : "Update Profile"}
                </Button>
                <Button type="button" variant="destructive" className="px-6 py-3" onClick={handleDelete}>
                  Delete Account
                </Button>
              </div>
            </form>
          )}
        </div>
      </div>
    </AdminLayout>
  )
}
