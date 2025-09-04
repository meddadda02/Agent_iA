"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
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

  useEffect(() => { setToken(localStorage.getItem("token")) }, [])
  useEffect(() => { if (token) fetchData() }, [token])

  const fetchData = async () => {
    setLoading(true)
    try {
      const textData = await (await fetch("http://localhost:8000/admin/moderation/models", { headers: { Authorization: `Bearer ${token}` } })).json()
      setTextModels((textData.models || []).map((m) => ({ name: m })))

      const imageData = await (await fetch("http://localhost:8000/admin/moderation/models-list", { headers: { Authorization: `Bearer ${token}` } })).json()
      setImageModels((imageData.models || []).map((m) => ({ name: m })))

      const rulesData = await (await fetch("http://localhost:8000/admin/moderation/rules", { headers: { Authorization: `Bearer ${token}` } })).json()
      setRules(Array.isArray(rulesData) ? rulesData : rulesData.rules || [])
    } catch (e) { console.error(e) }
    finally { setLoading(false) }
  }

  const toggleRule = (id) => setExpandedRuleIds(prev => prev.includes(id) ? prev.filter(rid => rid !== id) : [...prev, id])

  const handleAddOrUpdateRule = async () => {
    if (!token) return
    try {
      const url = editingRule ? `http://localhost:8000/admin/moderation/rules/${editingRule.id}` : "http://localhost:8000/admin/moderation/rules"
      const method = editingRule ? "PUT" : "POST"
      const formData = new FormData()
      formData.append("title", newRuleTitle)
      formData.append("content", newRuleContent)

      const res = await fetch(url, { method, headers: { Authorization: `Bearer ${token}` }, body: formData })
      if (!res.ok) throw new Error("Failed to save rule")
      setNewRuleTitle(""); setNewRuleContent(""); setEditingRule(null); setShowAddForm(false)
      fetchData()
    } catch (e) { console.error(e) }
  }

  const handleEditRule = (rule) => { setEditingRule(rule); setNewRuleTitle(rule.title); setNewRuleContent(rule.content || ""); setShowAddForm(true) }

  const handleDeleteRule = async (id) => {
    if (!token || !confirm("Are you sure?")) return
    try { 
      const res = await fetch(`http://localhost:8000/admin/moderation/rules/${id}`, { method: "DELETE", headers: { Authorization: `Bearer ${token}` } })
      if (!res.ok) throw new Error("Delete failed")
      fetchData()
    } catch (e) { console.error(e) }
  }

  if (!token) return <AdminLayout><div>Loading token...</div></AdminLayout>
  if (loading) return <AdminLayout><div>Loading data...</div></AdminLayout>

  return (
    <AdminLayout>
      <div className="space-y-8">
        {/* Header */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <h1 className="text-3xl font-bold text-gray-900">Moderation Management</h1>
          <Button className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white font-semibold shadow-md" onClick={fetchData}>
            <RefreshCw className="h-4 w-4" /> Refresh
          </Button>
        </div>

        <Tabs defaultValue="models" className="space-y-6">
          <TabsList className="bg-gray-50 rounded-lg p-1 shadow-inner">
            <TabsTrigger value="models" className="text-gray-700 font-medium">Models</TabsTrigger>
            <TabsTrigger value="rules" className="text-gray-700 font-medium">Rules</TabsTrigger>
          </TabsList>

          {/* Models Tab */}
          <TabsContent value="models">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <Card className="shadow-xl border border-gray-100 rounded-2xl">
                <CardHeader>
                  <CardTitle className="text-lg font-semibold text-blue-700">Text Models</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                  {textModels.map((m, i) => (
                    <div key={i} className="flex items-center gap-2 p-2 rounded-lg bg-blue-50 hover:bg-blue-100 transition shadow-sm">
                      <span className="font-medium text-blue-800">{m.name}</span>
                    </div>
                  ))}
                </CardContent>
              </Card>

              <Card className="shadow-xl border border-gray-100 rounded-2xl">
                <CardHeader>
                  <CardTitle className="text-lg font-semibold text-green-700">Image Models</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                  {imageModels.map((m, i) => (
                    <div key={i} className="flex items-center gap-2 p-2 rounded-lg bg-green-50 hover:bg-green-100 transition shadow-sm">
                      <span className="font-medium text-green-800">{m.name}</span>
                    </div>
                  ))}
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* Rules Tab */}
          <TabsContent value="rules">
            {!showAddForm && (
              <div className="flex justify-end mb-4">
                <Button className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white font-semibold shadow-md" onClick={() => setShowAddForm(true)}>
                  <PlusCircle className="h-4 w-4" /> Add Rule
                </Button>
              </div>
            )}

            {showAddForm && (
              <Card className="mb-4 shadow-xl border border-blue-100 rounded-2xl">
                <CardHeader>
                  <CardTitle className="text-blue-700 font-semibold">{editingRule ? "Edit Rule" : "Add New Rule"}</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <input
                    type="text"
                    placeholder="Rule Title"
                    value={newRuleTitle}
                    onChange={(e) => setNewRuleTitle(e.target.value)}
                    className="w-full p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-400 shadow-sm transition"
                  />
                  <textarea
                    placeholder="Rule Content"
                    value={newRuleContent}
                    onChange={(e) => setNewRuleContent(e.target.value)}
                    className="w-full p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-400 shadow-sm min-h-[80px] transition"
                  />
                  <div className="flex flex-col sm:flex-row gap-3">
                    <Button onClick={handleAddOrUpdateRule} className="bg-green-600 hover:bg-green-700 text-white font-semibold shadow-md rounded-lg">
                      {editingRule ? "Update" : "Add"}
                    </Button>
                    <Button variant="outline" onClick={() => { setShowAddForm(false); setEditingRule(null); }} className="border-gray-300 rounded-lg shadow-sm">
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
                  <div key={rule.id} className="border rounded-2xl shadow-sm hover:shadow-md bg-white transition">
                    <div className="flex justify-between items-center p-4 cursor-pointer hover:bg-gray-50" onClick={() => toggleRule(rule.id)}>
                      <div>
                        <div className="font-semibold text-blue-700 text-lg">{rule.title}</div>
                        <div className="text-xs text-gray-400">
                          {rule.published_at && <>Published: {new Date(rule.published_at).toLocaleDateString()}</>}
                        </div>
                      </div>
                      <div className="flex gap-2">
                        <Button size="sm" variant="outline" className="border-blue-300 text-blue-700 hover:bg-blue-50" onClick={(e) => { e.stopPropagation(); handleEditRule(rule); }}>
                          <Edit className="h-4 w-4 mr-1" /> Edit
                        </Button>
                        <Button size="sm" variant="destructive" className="bg-red-600 hover:bg-red-700 text-white" onClick={(e) => { e.stopPropagation(); handleDeleteRule(rule.id); }}>
                          <Trash2 className="h-4 w-4 mr-1" /> Delete
                        </Button>
                      </div>
                    </div>
                    {isExpanded && (
                      <div className="p-4 bg-gray-50 border-t text-gray-700 whitespace-pre-line rounded-b-2xl">
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
