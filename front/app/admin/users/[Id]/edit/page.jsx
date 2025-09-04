"use client"

import { useState, useEffect } from "react"
import React from "react"
import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { ArrowLeft } from "lucide-react"
import AdminLayout from "@/components/admin_layout"
import Link from "next/link"

export default function EditUserPage({ params }) {
  const router = useRouter()
  const actualParams = React.use(params)
  const { Id } = actualParams

  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [formData, setFormData] = useState({
    username: "",
    email: "",
    role: "user",
  })
  const [errors, setErrors] = useState({})

  useEffect(() => {
    fetchUser()
  }, [])

  const fetchUser = async () => {
    try {
      const token = localStorage.getItem("token")
      const res = await fetch(`http://localhost:8000/admin/users/${Id}`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok) throw new Error("User not found")
      const data = await res.json()
      setFormData({
        username: data.username || "",
        email: data.email || "",
        role: data.role || "user",
      })
    } catch (err) {
      console.error(err)
      setErrors({ fetch: "Failed to load user data" })
    } finally {
      setLoading(false)
    }
  }

  const handleInputChange = (e) => {
    const { name, value } = e.target
    setFormData((prev) => ({ ...prev, [name]: value }))
    if (errors[name]) setErrors((prev) => ({ ...prev, [name]: "" }))
  }

  const validateForm = () => {
    const newErrors = {}
    if (!formData.username.trim()) newErrors.username = "Username is required"
    if (!formData.email.trim()) newErrors.email = "Email is required"
    else if (!/\S+@\S+\.\S+/.test(formData.email)) newErrors.email = "Email is invalid"
    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!validateForm()) return

    setSubmitting(true)
    try {
      const token = localStorage.getItem("token")
      const submitData = new FormData()
      submitData.append("username", formData.username)
      submitData.append("email", formData.email)
      submitData.append("role", formData.role)

      const res = await fetch(`http://localhost:8000/admin/users/${Id}`, {
        method: "PUT",
        headers: { Authorization: `Bearer ${token}` },
        body: submitData,
      })

      if (!res.ok) {
        const result = await res.json()
        setErrors({ submit: result.detail || "Failed to update user" })
      } else {
        router.push("/admin/users")
      }
    } catch (err) {
      console.error(err)
      setErrors({ submit: "Network error. Please try again." })
    } finally {
      setSubmitting(false)
    }
  }

  if (loading)
    return (
      <AdminLayout>
        <div className="flex items-center justify-center h-64 text-gray-500 text-lg animate-pulse">
          Loading user data...
        </div>
      </AdminLayout>
    )

  return (
    <AdminLayout>
      <div className="space-y-6 animate-fadeIn">
        {/* Header */}
        <div className="flex items-center justify-between bg-white px-4 py-3 rounded-lg shadow-sm border">
          <div className="flex items-center space-x-4">
            <Link href="/admin/users">
              <Button
                variant="ghost"
                size="sm"
                className="hover:bg-indigo-50 hover:text-indigo-600 transition-colors"
              >
                <ArrowLeft className="h-4 w-4 mr-2" />
                Back to Users
              </Button>
            </Link>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Edit User</h1>
              <p className="text-sm text-gray-500">Modify user information and role</p>
            </div>
          </div>
        </div>

        {/* Edit User Form Card */}
        <div className="max-w-xl mx-auto">
          <Card className="shadow-xl rounded-2xl border border-gray-100 hover:shadow-2xl transition-shadow">
            <CardHeader>
              <CardTitle className="text-lg font-semibold text-gray-800">User Information</CardTitle>
            </CardHeader>
            <CardContent>
              {errors.fetch && (
                <div className="mb-4 text-sm text-red-600">{errors.fetch}</div>
              )}
              <form onSubmit={handleSubmit} className="space-y-5">
                {errors.submit && (
                  <div className="p-3 text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg">
                    {errors.submit}
                  </div>
                )}

                <div className="space-y-2">
                  <Label htmlFor="username">Username</Label>
                  <Input
                    id="username"
                    name="username"
                    value={formData.username}
                    onChange={handleInputChange}
                    placeholder="Enter username"
                    className={`rounded-lg shadow-sm focus:ring-2 transition ${
                      errors.username
                        ? "border-red-500 focus:ring-red-500"
                        : "focus:ring-indigo-500 focus:border-indigo-500"
                    }`}
                  />
                  {errors.username && (
                    <p className="text-sm text-red-600">{errors.username}</p>
                  )}
                </div>

                <div className="space-y-2">
                  <Label htmlFor="email">Email</Label>
                  <Input
                    id="email"
                    name="email"
                    type="email"
                    value={formData.email}
                    onChange={handleInputChange}
                    placeholder="Enter email"
                    className={`rounded-lg shadow-sm focus:ring-2 transition ${
                      errors.email
                        ? "border-red-500 focus:ring-red-500"
                        : "focus:ring-indigo-500 focus:border-indigo-500"
                    }`}
                  />
                  {errors.email && (
                    <p className="text-sm text-red-600">{errors.email}</p>
                  )}
                </div>

                <div className="space-y-2">
                  <Label htmlFor="role">Role</Label>
                  <Select
                    value={formData.role}
                    onValueChange={(value) =>
                      setFormData((prev) => ({ ...prev, role: value }))
                    }
                  >
                    <SelectTrigger className="rounded-lg border-gray-300 focus:ring-indigo-500 focus:border-indigo-500 transition">
                      <SelectValue placeholder="Select role" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="user">User</SelectItem>
                      <SelectItem value="admin">Admin</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <Button
                  type="submit"
                  disabled={submitting}
                  className="w-full bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white font-medium py-2.5 rounded-lg shadow-md transition"
                >
                  {submitting ? "Updating..." : "Update User"}
                </Button>
              </form>
            </CardContent>
          </Card>
        </div>
      </div>
    </AdminLayout>
  )
}
