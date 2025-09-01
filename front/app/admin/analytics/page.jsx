"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { BarChart3, TrendingUp, Users, AlertTriangle, RefreshCw } from "lucide-react"
import AdminLayout from "@/components/admin_layout"

export default function AnalyticsPage() {
  const [volumeData, setVolumeData] = useState([])
  const [topUsers, setTopUsers] = useState([])
  const [analysisTypes, setAnalysisTypes] = useState([])
  const [toxicityData, setToxicityData] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchAnalyticsData()
  }, [])

  const fetchAnalyticsData = async () => {
    setLoading(true)
    try {
      const token = localStorage.getItem("token")
      const headers = { Authorization: `Bearer ${token}` }

      // Volume by date
      const volumeResponse = await fetch("http://localhost:8000/admin/moderation/volume-by-date", { headers })
      const volumeJson = await volumeResponse.json()
      // Backend returns: [{date: "...", count: ...}]
      setVolumeData(Array.isArray(volumeJson) ? volumeJson : [])

      // Top users
      const topUsersResponse = await fetch("http://localhost:8000/admin/moderation/top-users", { headers })
      const topUsersJson = await topUsersResponse.json()
      // Backend returns: [{user_id, username, analysis_count}]
      setTopUsers(Array.isArray(topUsersJson) ? topUsersJson : [])

      // Analysis types
      const typesResponse = await fetch("http://localhost:8000/admin/moderation/count-by-type", { headers })
      const typesJson = await typesResponse.json()
      // Backend returns: [{type, count}]
      setAnalysisTypes(Array.isArray(typesJson) ? typesJson : [])

      // Toxicity data
      const toxicityResponse = await fetch("http://localhost:8000/admin/moderation/average-toxicity-by-user", { headers })
      const toxicityJson = await toxicityResponse.json()
      // Backend returns: [{user_id, username, average_toxicity}]
      setToxicityData(Array.isArray(toxicityJson) ? toxicityJson : [])

    } catch (error) {
      console.error("Error fetching analytics data:", error)
    } finally {
      setLoading(false)
    }
  }

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
    })
  }

  const getToxicityBadge = (toxicity) => {
    if (toxicity >= 0.7) return <Badge variant="destructive">High</Badge>
    if (toxicity >= 0.4) return <Badge variant="secondary">Medium</Badge>
    return <Badge variant="default">Low</Badge>
  }

  if (loading) {
    return (
      <AdminLayout>
        <div className="flex items-center justify-center h-64">
          <div className="text-lg">Loading analytics...</div>
        </div>
      </AdminLayout>
    )
  }

  return (
    <AdminLayout>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Analytics Dashboard</h1>
            <p className="text-gray-600">Monitor moderation activity and user behavior</p>
          </div>
          <Button onClick={fetchAnalyticsData}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh Data
          </Button>
        </div>

        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <Card>
            <CardContent className="p-6 flex items-center">
              <BarChart3 className="h-8 w-8 text-blue-600" />
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Total Analyses</p>
                <p className="text-2xl font-bold text-gray-900">
                  {Array.isArray(analysisTypes)
                    ? analysisTypes.reduce((sum, type) => sum + (typeof type.count === "number" ? type.count : 0), 0)
                    : 0}
                </p>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-6 flex items-center">
              <Users className="h-8 w-8 text-green-600" />
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Active Users</p>
                <p className="text-2xl font-bold text-gray-900">{Array.isArray(topUsers) ? topUsers.length : 0}</p>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-6 flex items-center">
              <TrendingUp className="h-8 w-8 text-purple-600" />
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Daily Average</p>
                <p className="text-2xl font-bold text-gray-900">
                  {Array.isArray(volumeData) && volumeData.length > 0
                    ? Math.round(volumeData.reduce((sum, day) => sum + (typeof day.count === "number" ? day.count : 0), 0) / volumeData.length)
                    : 0}
                </p>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-6 flex items-center">
              <AlertTriangle className="h-8 w-8 text-red-600" />
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">High Risk Users</p>
                <p className="text-2xl font-bold text-gray-900">
                  {Array.isArray(toxicityData)
                    ? toxicityData.filter((user) => typeof user.average_toxicity === "number" && user.average_toxicity >= 0.7).length
                    : 0}
                </p>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Volume by Date */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card>
            <CardHeader>
              <CardTitle>Analysis Volume by Date</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {Array.isArray(volumeData) && volumeData.length > 0 ? (
                  volumeData.map((day, index) => (
                    <div key={index} className="flex items-center justify-between">
                      <span className="text-sm text-gray-600">{formatDate(day.date)}</span>
                      <div className="flex items-center space-x-2">
                        <div className="w-32 bg-gray-200 rounded-full h-2">
                          <div
                            className="bg-blue-600 h-2 rounded-full"
                            style={{
                              width: `${
                                Math.max(...volumeData.map(d => typeof d.count === "number" ? d.count : 0)) > 0
                                  ? ((typeof day.count === "number" ? day.count : 0) /
                                    Math.max(...volumeData.map(d => typeof d.count === "number" ? d.count : 0))) * 100
                                  : 0
                              }%`
                            }}
                          ></div>
                        </div>
                        <span className="text-sm font-medium w-8">{day.count}</span>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="text-sm text-gray-500">No data available</div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Analysis Types */}
          <Card>
            <CardHeader>
              <CardTitle>Analysis by Content Type</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {Array.isArray(analysisTypes) && analysisTypes.map((type, index) => (
                  <div key={index} className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      <div className="w-3 h-3 rounded-full bg-blue-600"></div>
                      <span className="font-medium capitalize">{type.type}</span>
                    </div>
                    <span className="text-lg font-bold">{type.count}</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Top Users & Toxicity */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card>
            <CardHeader>
              <CardTitle>Most Active Users</CardTitle>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Username</TableHead>
                    <TableHead className="text-right">Analyses</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {Array.isArray(topUsers) && topUsers.map((user) => (
                    <TableRow key={user.user_id}>
                      <TableCell className="font-medium">{user.username}</TableCell>
                      <TableCell className="text-right">{user.analysis_count}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>User Toxicity Levels</CardTitle>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Username</TableHead>
                    <TableHead>Avg. Toxicity</TableHead>
                    <TableHead>Risk Level</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {Array.isArray(toxicityData) && toxicityData.map((user) => (
                    <TableRow key={user.user_id}>
                      <TableCell className="font-medium">{user.username}</TableCell>
                      <TableCell>{(user.average_toxicity * 100).toFixed(1)}%</TableCell>
                      <TableCell>{getToxicityBadge(user.average_toxicity)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </div>
      </div>
    </AdminLayout>
  )
}
