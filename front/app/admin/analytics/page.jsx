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

  useEffect(() => { fetchAnalyticsData() }, [])

  const fetchAnalyticsData = async () => {
    setLoading(true)
    try {
      const token = localStorage.getItem("token")
      const headers = { Authorization: `Bearer ${token}` }

      const volumeJson = await (await fetch("http://localhost:8000/admin/moderation/volume-by-date", { headers })).json()
      setVolumeData(Array.isArray(volumeJson) ? volumeJson : [])

      const topUsersJson = await (await fetch("http://localhost:8000/admin/moderation/top-users", { headers })).json()
      setTopUsers(Array.isArray(topUsersJson) ? topUsersJson : [])

      const typesJson = await (await fetch("http://localhost:8000/admin/moderation/count-by-type", { headers })).json()
      setAnalysisTypes(Array.isArray(typesJson) ? typesJson : [])

      const toxicityJson = await (await fetch("http://localhost:8000/admin/moderation/average-toxicity-by-user", { headers })).json()
      setToxicityData(Array.isArray(toxicityJson) ? toxicityJson : [])
    } catch (error) { console.error("Error fetching analytics data:", error) }
    finally { setLoading(false) }
  }

  const formatDate = (dateString) => new Date(dateString).toLocaleDateString("en-US", { month: "short", day: "numeric" })
  const getToxicityBadge = (toxicity) => {
    if (toxicity >= 0.7) return <Badge variant="destructive">High</Badge>
    if (toxicity >= 0.4) return <Badge variant="secondary">Medium</Badge>
    return <Badge variant="default">Low</Badge>
  }

  if (loading) return (
    <AdminLayout>
      <div className="flex items-center justify-center h-64 text-gray-700 font-medium text-lg">Loading analytics...</div>
    </AdminLayout>
  )

  return (
    <AdminLayout>
      <div className="space-y-8">

        {/* Header */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Analytics Dashboard</h1>
            <p className="text-gray-500 mt-1">Monitor moderation activity and user behavior</p>
          </div>
          <Button className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white font-semibold shadow-md rounded-lg" onClick={fetchAnalyticsData}>
            <RefreshCw className="h-4 w-4" /> Refresh Data
          </Button>
        </div>

        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {[{
            icon: <BarChart3 className="h-8 w-8 text-blue-600" />,
            label: "Total Analyses",
            value: Array.isArray(analysisTypes) ? analysisTypes.reduce((sum, type) => sum + (typeof type.count === "number" ? type.count : 0), 0) : 0
          },{
            icon: <Users className="h-8 w-8 text-green-600" />,
            label: "Active Users",
            value: Array.isArray(topUsers) ? topUsers.length : 0
          },{
            icon: <TrendingUp className="h-8 w-8 text-purple-600" />,
            label: "Daily Average",
            value: Array.isArray(volumeData) && volumeData.length > 0
              ? Math.round(volumeData.reduce((sum, day) => sum + (typeof day.count === "number" ? day.count : 0), 0) / volumeData.length)
              : 0
          },{
            icon: <AlertTriangle className="h-8 w-8 text-red-600" />,
            label: "High Risk Users",
            value: Array.isArray(toxicityData)
              ? toxicityData.filter((u) => typeof u.average_toxicity === "number" && u.average_toxicity >= 0.7).length
              : 0
          }].map((card, idx) => (
            <Card key={idx} className="shadow-xl rounded-2xl border border-gray-100 hover:shadow-2xl transition">
              <CardContent className="p-6 flex items-center gap-4">
                {card.icon}
                <div>
                  <p className="text-sm text-gray-500">{card.label}</p>
                  <p className="text-2xl font-bold text-gray-900">{card.value}</p>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Volume & Types */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

          <Card className="shadow-lg rounded-2xl border border-gray-100 hover:shadow-xl transition">
            <CardHeader>
              <CardTitle className="text-lg font-semibold text-gray-800">Analysis Volume by Date</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {Array.isArray(volumeData) && volumeData.length > 0 ? volumeData.map((day, i) => (
                <div key={i} className="flex items-center justify-between">
                  <span className="text-sm text-gray-500">{formatDate(day.date)}</span>
                  <div className="flex items-center gap-2">
                    <div className="w-32 bg-gray-200 rounded-full h-2">
                      <div className="bg-blue-600 h-2 rounded-full" style={{
                        width: `${
                          Math.max(...volumeData.map(d => typeof d.count === "number" ? d.count : 0)) > 0
                            ? ((typeof day.count === "number" ? day.count : 0) / Math.max(...volumeData.map(d => typeof d.count === "number" ? d.count : 0))) * 100
                            : 0
                        }%`
                      }}></div>
                    </div>
                    <span className="text-sm font-medium w-8">{day.count}</span>
                  </div>
                </div>
              )) : <div className="text-sm text-gray-400">No data available</div>}
            </CardContent>
          </Card>

          <Card className="shadow-lg rounded-2xl border border-gray-100 hover:shadow-xl transition">
            <CardHeader>
              <CardTitle className="text-lg font-semibold text-gray-800">Analysis by Content Type</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {Array.isArray(analysisTypes) && analysisTypes.map((type, idx) => (
                <div key={idx} className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-3 h-3 rounded-full bg-blue-600"></div>
                    <span className="font-medium capitalize">{type.type}</span>
                  </div>
                  <span className="text-lg font-bold">{type.count}</span>
                </div>
              ))}
            </CardContent>
          </Card>

        </div>

        {/* Users & Toxicity */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

          <Card className="shadow-lg rounded-2xl border border-gray-100 hover:shadow-xl transition">
            <CardHeader>
              <CardTitle className="text-lg font-semibold text-gray-800">Most Active Users</CardTitle>
            </CardHeader>
            <CardContent>
              <Table className="rounded-lg overflow-hidden shadow-sm">
                <TableHeader className="bg-gray-50">
                  <TableRow>
                    <TableHead className="text-gray-600">Username</TableHead>
                    <TableHead className="text-gray-600 text-right">Analyses</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {Array.isArray(topUsers) && topUsers.map((user) => (
                    <TableRow key={user.user_id} className="hover:bg-gray-50 transition">
                      <TableCell className="font-medium">{user.username}</TableCell>
                      <TableCell className="text-right">{user.analysis_count}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>

          <Card className="shadow-lg rounded-2xl border border-gray-100 hover:shadow-xl transition">
            <CardHeader>
              <CardTitle className="text-lg font-semibold text-gray-800">User Toxicity Levels</CardTitle>
            </CardHeader>
            <CardContent>
              <Table className="rounded-lg overflow-hidden shadow-sm">
                <TableHeader className="bg-gray-50">
                  <TableRow>
                    <TableHead className="text-gray-600">Username</TableHead>
                    <TableHead className="text-gray-600">Avg. Toxicity</TableHead>
                    <TableHead className="text-gray-600">Risk Level</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {Array.isArray(toxicityData) && toxicityData.map((user) => (
                    <TableRow key={user.user_id} className="hover:bg-gray-50 transition">
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
