"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Users, Shield, BarChart3, TrendingUp } from "lucide-react"
import AdminLayout from "@/components/admin_layout"
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  BarChart,
  Bar,
  Cell,
  Legend,
} from "recharts"

export default function AdminDashboard() {
  const [stats, setStats] = useState({
    totalUsers: 0,
    totalAnalyses: 0,
    toxicContent: 0,
    activeUsers: 0,
  })
  const [chartData, setChartData] = useState([])
  const [typeDistribution, setTypeDistribution] = useState([])

  useEffect(() => {
    fetchDashboardStats()
    fetchChartData()
    fetchTypeDistribution()
  }, [])

  const fetchDashboardStats = async () => {
    try {
      const token = localStorage.getItem("token")
      const [usersRes, analysesRes, toxicityRes, activeUsersRes] = await Promise.all([
        fetch("http://localhost:8000/admin/stats/users/count", { headers: { Authorization: `Bearer ${token}` } }),
        fetch("http://localhost:8000/admin/moderation/analyses/count/today", { headers: { Authorization: `Bearer ${token}` } }),
        fetch("http://localhost:8000/admin/moderation/analyses/toxic-percentage", { headers: { Authorization: `Bearer ${token}` } }),
        fetch("http://localhost:8000/admin/users/active/count", { headers: { Authorization: `Bearer ${token}` } })
      ])

      if (!usersRes.ok || !analysesRes.ok || !toxicityRes.ok || !activeUsersRes.ok) throw new Error("Erreur récupération stats")

      const users = await usersRes.json()
      const analysesData = await analysesRes.json()
      const toxicityData = await toxicityRes.json()
      const activeUsersData = await activeUsersRes.json()

      setStats({
        totalUsers: users.total_users,
        totalAnalyses: analysesData.total_analyses_today,
        toxicContent: parseFloat(toxicityData) || 0,
        activeUsers: activeUsersData.active_users
      })
    } catch (error) {
      console.error("Erreur chargement stats:", error)
    }
  }

  const fetchChartData = async () => {
    try {
      const token = localStorage.getItem("token")
      const res = await fetch("http://localhost:8000/admin/moderation/analyses/stats/weekly", {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (!res.ok) throw new Error("Erreur récupération données graphiques")
      const data = await res.json()
      setChartData(data)
    } catch (error) {
      console.error("Erreur chargement graphique:", error)
    }
  }

  const fetchTypeDistribution = async () => {
    try {
      const token = localStorage.getItem("token")
      const res = await fetch("http://localhost:8000/admin/moderation/analyses/global-type-distribution", {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (!res.ok) throw new Error("Erreur récupération type distribution")
      const data = await res.json()
      setTypeDistribution(data.global_type_distribution || [])
    } catch (error) {
      console.error("Erreur chargement distribution types:", error)
    }
  }

  const COLORS = ["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6"]

  const statCards = [
    { title: "Total Users", value: stats.totalUsers, icon: Users, color: "text-blue-600", bgColor: "bg-blue-100" },
    { title: "Total Analyses", value: stats.totalAnalyses, icon: BarChart3, color: "text-green-600", bgColor: "bg-green-100" },
    { title: "Toxic Content", value: `${stats.toxicContent.toFixed(2)}%`, icon: Shield, color: "text-red-600", bgColor: "bg-red-100" },
    { title: "Active Users", value: stats.activeUsers, icon: TrendingUp, color: "text-purple-600", bgColor: "bg-purple-100" },
  ]

  return (
    <AdminLayout>
      <div className="space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Admin Dashboard</h1>
          <p className="text-gray-600">Vue d’ensemble des performances et activités récentes</p>
        </div>

        {/* Statistiques */}
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {statCards.map((stat) => {
            const Icon = stat.icon
            return (
              <Card key={stat.title}>
                <CardContent className="p-6">
                  <div className="flex items-center">
                    <div className={`p-2 rounded-lg ${stat.bgColor}`}>
                      <Icon className={`h-6 w-6 ${stat.color}`} />
                    </div>
                    <div className="ml-4">
                      <p className="text-sm font-medium text-gray-600">{stat.title}</p>
                      <p className="text-2xl font-bold text-gray-900">{stat.value}</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )
          })}
        </div>

        {/* Graphique + Distribution globale */}
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          {/* Graphique évolutif */}
          <Card>
            <CardHeader>
              <CardTitle>Évolution des analyses (7 derniers jours)</CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={250}>
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="day" />
                  <YAxis />
                  <Tooltip />
                  <Line type="monotone" dataKey="analyses" stroke="#3b82f6" strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          {/* Distribution globale par type */}
          <Card>
            <CardHeader>
              <CardTitle>Répartition globale par type</CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={250}>
                <BarChart data={typeDistribution} layout="vertical" margin={{ top: 20, right: 30, left: 40, bottom: 20 }}>
                  <XAxis type="number" />
                  <YAxis type="category" dataKey="type" />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="count">
                    {typeDistribution.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </div>
      </div>
    </AdminLayout>
  )
}
