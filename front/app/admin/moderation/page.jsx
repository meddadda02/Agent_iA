"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { List, RefreshCw, PlusCircle, Edit, Trash2 } from "lucide-react"
import AdminLayout from "@/components/admin_layout"

export default function ModerationPage() {
  const [token, setToken] = useState(null)
  const [loading, setLoading] = useState(true)
  const [textModels, setTextModels] = useState([])
  const [imageModels, setImageModels] = useState([])
  const [rules, setRules] = useState([])
  const [expandedRuleIds, setExpandedRuleIds] = useState([])
  const [showAddForm, setShowAddForm] = useState(false)
  const [newRuleTitle, setNewRuleTitle] = useState("")
  const [newRuleContent, setNewRuleContent] = useState("")
  const [editingRule, setEditingRule] = useState(null)

  // Load token on client
  useEffect(() => {
    const t = localStorage.getItem("token")
    setToken(t)
  }, [])

  // Fetch data when token is available
  useEffect(() => {
    if (token) fetchData()
  }, [token])

  const fetchData = async () => {
    setLoading(true)
    try {
      const textRes = await fetch("http://localhost:8000/admin/moderation/models", {
        headers: { Authorization: `Bearer ${token}` },
      })
      const textData = await textRes.json()
      // Remove status from text models
      setTextModels((textData.models || []).map((m) => ({ name: m })))

      const imageRes = await fetch("http://localhost:8000/admin/moderation/models-list", {
        headers: { Authorization: `Bearer ${token}` },
      })
      const imageData = await imageRes.json()
      setImageModels((imageData.models || []).map((m) => ({ name: m })))

      const rulesRes = await fetch("http://localhost:8000/admin/moderation/rules", {
        headers: { Authorization: `Bearer ${token}` },
      })
      const rulesData = await rulesRes.json()
      setRules(Array.isArray(rulesData) ? rulesData : rulesData.rules || [])
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  const toggleRule = (id) => {
    setExpandedRuleIds((prev) =>
      prev.includes(id) ? prev.filter((rid) => rid !== id) : [...prev, id]
    )
  }

  const handleAddOrUpdateRule = async () => {
    if (!token) return
    try {
      const url = editingRule
        ? `http://localhost:8000/admin/moderation/rules/${editingRule.id}`
        : "http://localhost:8000/admin/moderation/rules"
      const method = editingRule ? "PUT" : "POST"

      const formData = new FormData()
      formData.append("title", newRuleTitle)
      formData.append("content", newRuleContent)

      const res = await fetch(url, {
        method,
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      })

      if (!res.ok) throw new Error("Failed to save rule")
      setNewRuleTitle("")
      setNewRuleContent("")
      setEditingRule(null)
      setShowAddForm(false)
      fetchData()
    } catch (e) {
      console.error(e)
    }
  }

  const handleEditRule = (rule) => {
    setEditingRule(rule)
    setNewRuleTitle(rule.title)
    setNewRuleContent(rule.content || "")
    setShowAddForm(true)
  }

  const handleDeleteRule = async (id) => {
    if (!token || !confirm("Are you sure?")) return
    try {
      const res = await fetch(`http://localhost:8000/admin/moderation/rules/${id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok) throw new Error("Delete failed")
      fetchData()
    } catch (e) {
      console.error(e)
    }
  }

  if (!token) return <AdminLayout><div>Loading token...</div></AdminLayout>
  if (loading) return <AdminLayout><div>Loading data...</div></AdminLayout>

  return (
    <AdminLayout>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold">Moderation Management</h1>
          <Button onClick={() => fetchData()}><RefreshCw className="h-4 w-4 mr-2" /> Refresh</Button>
        </div>

        <Tabs defaultValue="models" className="space-y-6">
          <TabsList>
            <TabsTrigger value="models">Models</TabsTrigger>
            <TabsTrigger value="rules">Rules</TabsTrigger>
          </TabsList>

          <TabsContent value="models">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <Card>
                <CardHeader>
                  <CardTitle>Text Models</CardTitle>
                </CardHeader>
                <CardContent>
                  {textModels.map((m, i) => (
                    <div
                      key={i}
                      className="flex items-center gap-2 p-2 border rounded bg-blue-50 hover:bg-blue-100 transition"
                    >
                      <span className="font-medium text-blue-800">{m.name}</span>
                    </div>
                  ))}
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Image Models</CardTitle>
                </CardHeader>
                <CardContent>
                  {imageModels.map((m, i) => (
                    <div
                      key={i}
                      className="flex items-center gap-2 p-2 border rounded bg-green-50 hover:bg-green-100 transition"
                    >
                      <span className="font-medium text-green-800">{m.name}</span>
                    </div>
                  ))}
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="rules">
            {!showAddForm && (
              <div className="flex justify-end mb-4">
                <Button
                  onClick={() => setShowAddForm(true)}
                  className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white font-semibold"
                >
                  <PlusCircle className="h-4 w-4" /> Add Rule
                </Button>
              </div>
            )}

            {showAddForm && (
              <Card className="mb-4 shadow-lg border border-blue-100">
                <CardHeader>
                  <CardTitle className="text-blue-700">{editingRule ? "Edit Rule" : "Add New Rule"}</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <input
                    type="text"
                    placeholder="Rule Title"
                    value={newRuleTitle}
                    onChange={(e) => setNewRuleTitle(e.target.value)}
                    className="w-full p-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-400"
                  />
                  <textarea
                    placeholder="Rule Content"
                    value={newRuleContent}
                    onChange={(e) => setNewRuleContent(e.target.value)}
                    className="w-full p-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-400 min-h-[80px]"
                  />
                  <div className="flex gap-2">
                    <Button
                      onClick={handleAddOrUpdateRule}
                      className="bg-green-600 hover:bg-green-700 text-white font-semibold"
                    >
                      {editingRule ? "Update" : "Add"}
                    </Button>
                    <Button
                      variant="outline"
                      onClick={() => { setShowAddForm(false); setEditingRule(null); }}
                      className="border-gray-300"
                    >
                      Cancel
                    </Button>
                  </div>
                </CardContent>
              </Card>
            )}

            <div className="space-y-3">
              {rules.map((rule) => {
                const isExpanded = expandedRuleIds.includes(rule.id)
                return (
                  <div
                    key={rule.id}
                    className="border rounded shadow-sm transition hover:shadow-md bg-white"
                  >
                    <div
                      className="flex justify-between items-center p-3 cursor-pointer hover:bg-gray-50"
                      onClick={() => toggleRule(rule.id)}
                    >
                      <div>
                        <div className="font-semibold text-blue-700">{rule.title}</div>
                        <div className="text-xs text-gray-400">
                          {rule.published_at && (
                            <>Published: {new Date(rule.published_at).toLocaleDateString()}</>
                          )}
                        </div>
                      </div>
                      <div className="flex gap-2">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={(e) => { e.stopPropagation(); handleEditRule(rule); }}
                          className="border-blue-300 text-blue-700 hover:bg-blue-50"
                        >
                          <Edit className="h-4 w-4 mr-1" /> Edit
                        </Button>
                        <Button
                          size="sm"
                          variant="destructive"
                          onClick={(e) => { e.stopPropagation(); handleDeleteRule(rule.id); }}
                          className="bg-red-600 hover:bg-red-700 text-white"
                        >
                          <Trash2 className="h-4 w-4 mr-1" /> Delete
                        </Button>
                      </div>
                    </div>
                    {isExpanded && (
                      <div className="p-4 bg-gray-50 border-t text-gray-700 whitespace-pre-line">
                        {rule.content}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </AdminLayout>
  )
}
