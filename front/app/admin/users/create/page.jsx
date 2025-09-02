"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { ArrowLeft, Upload } from "lucide-react"
import AdminLayout from "@/components/admin_layout"
import Link from "next/link"

export default function CreateUserPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(false)
  const [formData, setFormData] = useState({
    username: "",
    email: "",
    password: "",
    confirm_password: "",
    role: "user",
  })
  const [photo, setPhoto] = useState(null)
  const [errors, setErrors] = useState({})

  const handleInputChange = (e) => {
    const { name, value } = e.target
    setFormData((prev) => ({ ...prev, [name]: value }))
    if (errors[name]) {
      setErrors((prev) => ({ ...prev, [name]: "" }))
    }
  }

  const handlePhotoChange = (e) => {
    const file = e.target.files[0]
    if (file) setPhoto(file)
  }

  const validateForm = () => {
    const newErrors = {}
    if (!formData.username.trim()) newErrors.username = "Username is required"
    if (!formData.email.trim()) newErrors.email = "Email is required"
    else if (!/\S+@\S+\.\S+/.test(formData.email)) newErrors.email = "Email is invalid"
    if (!formData.password) newErrors.password = "Password is required"
    else if (formData.password.length < 6) newErrors.password = "Password must be at least 6 characters"
    if (formData.password !== formData.confirm_password) newErrors.confirm_password = "Passwords do not match"
    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!validateForm()) return
    setLoading(true)
    try {
      const submitData = new FormData()
      submitData.append("username", formData.username)
      submitData.append("email", formData.email)
      submitData.append("password", formData.password)
      submitData.append("confirm_password", formData.confirm_password)
      submitData.append("role", formData.role)
      if (photo) submitData.append("photo", photo)

      const response = await fetch("http://localhost:8000/admin/users", {
        method: "POST",
        headers: { Authorization: `Bearer ${localStorage.getItem("token")}` },
        body: submitData,
      })

      const result = await response.json()
      if (response.ok) {
        router.push("/admin/users")
      } else {
        setErrors({ submit: result.detail || "Failed to create user" })
      }
    } catch (error) {
      console.error("Error creating user:", error)
      setErrors({ submit: "Network error. Please try again." })
    } finally {
      setLoading(false)
    }
  }

  return (
    <AdminLayout>
      <div className="space-y-10">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-extrabold text-black tracking-tight">Create User</h1>
          <p className="text-gray-500">Add a new user to the system</p>
        </div>

        {/* Back Button */}
        <div className="flex justify-start mb-4">
          <Link href="/admin/users">
            <Button variant="ghost" size="sm" className="flex items-center">
              <ArrowLeft className="h-4 w-4 mr-2" /> Back
            </Button>
          </Link>
        </div>

        {/* Form Card */}
        <Card className="max-w-2xl mx-auto shadow-2xl border-0 bg-white/90 backdrop-blur-md">
          <CardHeader>
            <CardTitle className="text-xl font-bold text-black">User Information</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-8">
              {errors.submit && (
                <div className="p-3 text-sm text-red-600 bg-red-50 border border-red-200 rounded-md">
                  {errors.submit}
                </div>
              )}

              {/* Username & Email */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                <div className="space-y-2">
                  <Label htmlFor="username" className="font-semibold text-gray-700">Username</Label>
                  <Input
                    id="username"
                    name="username"
                    value={formData.username}
                    onChange={handleInputChange}
                    placeholder="Enter username"
                    className={`focus:ring-2 focus:ring-gray-400 bg-gray-50 ${errors.username ? "border-red-500" : ""}`}
                  />
                  {errors.username && <p className="text-xs text-red-600">{errors.username}</p>}
                </div>
                <div className="space-y-2">
                  <Label htmlFor="email" className="font-semibold text-gray-700">Email</Label>
                  <Input
                    id="email"
                    name="email"
                    type="email"
                    value={formData.email}
                    onChange={handleInputChange}
                    placeholder="Enter email"
                    className={`focus:ring-2 focus:ring-gray-400 bg-gray-50 ${errors.email ? "border-red-500" : ""}`}
                  />
                  {errors.email && <p className="text-xs text-red-600">{errors.email}</p>}
                </div>
              </div>

              {/* Password & Confirm Password */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                <div className="space-y-2">
                  <Label htmlFor="password" className="font-semibold text-gray-700">Password</Label>
                  <Input
                    id="password"
                    name="password"
                    type="password"
                    value={formData.password}
                    onChange={handleInputChange}
                    placeholder="Enter password"
                    className={`focus:ring-2 focus:ring-gray-400 bg-gray-50 ${errors.password ? "border-red-500" : ""}`}
                  />
                  {errors.password && <p className="text-xs text-red-600">{errors.password}</p>}
                </div>
                <div className="space-y-2">
                  <Label htmlFor="confirm_password" className="font-semibold text-gray-700">Confirm Password</Label>
                  <Input
                    id="confirm_password"
                    name="confirm_password"
                    type="password"
                    value={formData.confirm_password}
                    onChange={handleInputChange}
                    placeholder="Confirm password"
                    className={`focus:ring-2 focus:ring-gray-400 bg-gray-50 ${errors.confirm_password ? "border-red-500" : ""}`}
                  />
                  {errors.confirm_password && <p className="text-xs text-red-600">{errors.confirm_password}</p>}
                </div>
              </div>

              {/* Role */}
              <div className="space-y-2">
                <Label htmlFor="role" className="font-semibold text-gray-700">Role</Label>
                <Select
                  value={formData.role}
                  onValueChange={(value) => setFormData((prev) => ({ ...prev, role: value }))}
                >
                  <SelectTrigger className="focus:ring-2 focus:ring-gray-400 bg-gray-50">
                    <SelectValue placeholder="Select role" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="user">User</SelectItem>
                    <SelectItem value="admin">Admin</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* Photo Upload */}
              <div className="space-y-2">
                <Label htmlFor="photo" className="font-semibold text-gray-700">Profile Photo (Optional)</Label>
                <div className="flex items-center space-x-4">
                  <Input
                    id="photo"
                    type="file"
                    accept="image/*"
                    onChange={handlePhotoChange}
                    className="hidden"
                  />
                  <Button
                    type="button"
                    variant="outline"
                    className="flex items-center gap-2 border-gray-300"
                    onClick={() => document.getElementById("photo").click()}
                  >
                    <Upload className="h-4 w-4" /> Choose Photo
                  </Button>
                  {photo && <span className="text-sm text-gray-700">{photo.name}</span>}
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex justify-end space-x-4 pt-4">
                <Link href="/admin/users">
                  <Button type="button" variant="outline" className="border-gray-300">
                    Cancel
                  </Button>
                </Link>
                <Button
                  type="submit"
                  disabled={loading}
                  className="bg-gray-800 hover:bg-gray-900 text-white font-semibold shadow-md"
                >
                  {loading ? "Creating..." : "Create User"}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      </div>
    </AdminLayout>
  )
}
